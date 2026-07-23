import Foundation
import ImageIO
import Vision

struct FrameSpec: Decodable {
    let image: String
    let timestampSeconds: Double
}

struct BoxSpec: Codable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

    var rect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }

    init(_ rect: CGRect) {
        x = rect.origin.x
        y = rect.origin.y
        width = rect.width
        height = rect.height
    }
}

struct GateInput: Decodable {
    let sourceId: String
    let trackId: String
    let viewportYawDegrees: Double
    let viewportPitchDegrees: Double
    let horizontalFovDegrees: Double
    let initialBox: BoxSpec
    let frames: [FrameSpec]
}

struct Observation: Encodable {
    let frameIndex: Int
    let timestampSeconds: Double
    let state: String
    let confidence: Double?
    let boundingBox: BoxSpec?
    let yawRadians: Double?
    let pitchRadians: Double?
    let sphericalCenterStepRadians: Double?
    let error: String?
}

struct Summary: Encodable {
    let outcome: String
    let requestedFrameCount: Int
    let trackedFrameCount: Int
    let lostFrameCount: Int
    let errorFrameCount: Int
    let persistenceRatio: Double
    let maximumSphericalCenterStepRadians: Double?
    let seamCrossingCount: Int
}

struct Provenance: Encodable {
    let adapterId: String
    let adapterVersion: String
    let backendId: String
    let projectionStrategy: String
    let trackingLevel: String
}

struct GateOutput: Encodable {
    let schemaVersion: Int
    let sourceId: String
    let trackId: String
    let provenance: Provenance
    let observations: [Observation]
    let summary: Summary
    let limitations: [String]
}

enum GateError: Error, CustomStringConvertible {
    case usage
    case invalid(String)

    var description: String {
        switch self {
        case .usage:
            return "usage: vision_tracking_gate INPUT.json OUTPUT.json"
        case .invalid(let message):
            return message
        }
    }
}

func radians(_ degrees: Double) -> Double { degrees * .pi / 180.0 }

func wrapYaw(_ value: Double) -> Double {
    var wrapped = value
    while wrapped >= .pi { wrapped -= 2.0 * .pi }
    while wrapped < -.pi { wrapped += 2.0 * .pi }
    return wrapped
}

func privacySafeError(_ error: Error) -> String {
    let value = error as NSError
    return "\(value.domain):\(value.code)"
}

func direction(yaw: Double, pitch: Double) -> SIMD3<Double> {
    let cp = cos(pitch)
    return SIMD3(cp * sin(yaw), sin(pitch), cp * cos(yaw))
}

func sphericalDistance(_ first: (Double, Double), _ second: (Double, Double)) -> Double {
    let a = direction(yaw: first.0, pitch: first.1)
    let b = direction(yaw: second.0, pitch: second.1)
    let cross = SIMD3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    )
    return atan2(sqrt(cross.x * cross.x + cross.y * cross.y + cross.z * cross.z),
                 a.x * b.x + a.y * b.y + a.z * b.z)
}

func sphericalCenter(_ box: CGRect, input: GateInput) -> (Double, Double) {
    let hFov = radians(input.horizontalFovDegrees)
    let vFov = 2.0 * atan(tan(hFov / 2.0) / (16.0 / 9.0))
    let yawOffset = atan((2.0 * box.midX - 1.0) * tan(hFov / 2.0))
    let pitchOffset = atan((2.0 * box.midY - 1.0) * tan(vFov / 2.0))
    return (
        wrapYaw(radians(input.viewportYawDegrees) + yawOffset),
        max(-.pi / 2.0, min(.pi / 2.0, radians(input.viewportPitchDegrees) + pitchOffset))
    )
}

func loadImage(_ path: String) throws -> CGImage {
    let url = URL(fileURLWithPath: path) as CFURL
    guard let source = CGImageSourceCreateWithURL(url, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw GateError.invalid("image_decode_failed")
    }
    return image
}

func validate(_ input: GateInput) throws {
    let safe = "^[A-Za-z0-9._:-]+$"
    guard input.sourceId.range(of: safe, options: .regularExpression) != nil,
          input.trackId.range(of: safe, options: .regularExpression) != nil else {
        throw GateError.invalid("sourceId and trackId must be privacy-safe")
    }
    guard !input.frames.isEmpty else { throw GateError.invalid("at least one frame is required") }
    guard (0.0..<180.0).contains(input.horizontalFovDegrees) else {
        throw GateError.invalid("horizontal FOV must be in (0, 180)")
    }
    let box = input.initialBox
    guard box.width > 0, box.height > 0, box.x >= 0, box.y >= 0,
          box.x + box.width <= 1, box.y + box.height <= 1 else {
        throw GateError.invalid("initialBox must be a normalized in-frame rectangle")
    }
    var prior = -Double.infinity
    for frame in input.frames {
        guard frame.timestampSeconds >= 0, frame.timestampSeconds > prior else {
            throw GateError.invalid("frame timestamps must be finite, nonnegative, and increasing")
        }
        prior = frame.timestampSeconds
    }
}

func run(_ input: GateInput) throws -> GateOutput {
    try validate(input)
    let sequence = VNSequenceRequestHandler()
    var priorObservation = VNDetectedObjectObservation(boundingBox: input.initialBox.rect)

    var observations: [Observation] = []
    var previousCenter: (Double, Double)?
    var maxStep: Double?
    var seamCrossings = 0
    var tracked = 0
    var lost = 0
    var errors = 0

    for (index, frame) in input.frames.enumerated() {
        do {
            let image = try loadImage(frame.image)
            var completionObservation: VNDetectedObjectObservation?
            var completionError: Error?
            let request = VNTrackObjectRequest(
                detectedObjectObservation: priorObservation
            ) { request, error in
                completionError = error
                completionObservation = request.results?.first as? VNDetectedObjectObservation
            }
            request.revision = VNTrackObjectRequestRevision1
            request.trackingLevel = .accurate
            request.isLastFrame = index == input.frames.count - 1
            try sequence.perform([request], on: image)
            if let completionError { throw completionError }
            guard let found = completionObservation else {
                observations.append(Observation(
                    frameIndex: index, timestampSeconds: frame.timestampSeconds,
                    state: "lost", confidence: nil, boundingBox: nil,
                    yawRadians: nil, pitchRadians: nil,
                    sphericalCenterStepRadians: nil, error: nil
                ))
                lost += 1
                continue
            }
            let center = sphericalCenter(found.boundingBox, input: input)
            let step = previousCenter.map { sphericalDistance($0, center) }
            if let previous = previousCenter,
               abs(center.0 - previous.0) > .pi {
                seamCrossings += 1
            }
            if let step {
                maxStep = max(maxStep ?? step, step)
            }
            observations.append(Observation(
                frameIndex: index, timestampSeconds: frame.timestampSeconds,
                state: "tracked", confidence: Double(found.confidence),
                boundingBox: BoxSpec(found.boundingBox),
                yawRadians: center.0, pitchRadians: center.1,
                sphericalCenterStepRadians: step, error: nil
            ))
            tracked += 1
            previousCenter = center
            priorObservation = found
        } catch {
            observations.append(Observation(
                frameIndex: index, timestampSeconds: frame.timestampSeconds,
                state: "error", confidence: nil, boundingBox: nil,
                yawRadians: nil, pitchRadians: nil,
                sphericalCenterStepRadians: nil, error: privacySafeError(error)
            ))
            errors += 1
        }
    }

    let requested = input.frames.count
    return GateOutput(
        schemaVersion: 1,
        sourceId: input.sourceId,
        trackId: input.trackId,
        provenance: Provenance(
            adapterId: "apple-vision-tracking-gate",
            adapterVersion: "0.1.0",
            backendId: "VNTrackObjectRequest",
            projectionStrategy: "single rectilinear viewport",
            trackingLevel: "accurate"
        ),
        observations: observations,
        summary: Summary(
            outcome: tracked > 0 ? "tracking_observations_returned" : "no_tracking_observations",
            requestedFrameCount: requested,
            trackedFrameCount: tracked,
            lostFrameCount: lost,
            errorFrameCount: errors,
            persistenceRatio: Double(tracked) / Double(requested),
            maximumSphericalCenterStepRadians: maxStep,
            seamCrossingCount: seamCrossings
        ),
        limitations: [
            "The initial box is supplied externally; this gate does not detect or identify a subject.",
            "Vision tracking confidence is perception evidence, not editorial interest.",
            "A single rectilinear viewport cannot preserve a target that leaves that viewport.",
            "Spherical centers use the same approximate pinhole mapping as the frame gate.",
        ]
    )
}

do {
    guard CommandLine.arguments.count == 3 else { throw GateError.usage }
    let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
    let input = try JSONDecoder().decode(GateInput.self, from: Data(contentsOf: inputURL))
    let output = try run(input)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    try encoder.encode(output).write(to: outputURL, options: .atomic)
} catch {
    FileHandle.standardError.write(Data("vision_tracking_gate: \(error)\n".utf8))
    exit(2)
}

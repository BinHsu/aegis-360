import Foundation
import Vision

struct ViewportSpec: Decodable {
    let id: String
    let image: String
    let yawDegrees: Double
    let pitchDegrees: Double
    let horizontalFovDegrees: Double
    let timestampSeconds: Double
}

struct GateInput: Decodable {
    let sourceId: String
    let frameIndex: Int
    let viewports: [ViewportSpec]
}

struct Candidate: Encodable {
    let id: String
    let kind: String
    let confidence: Double
    let yawRadians: Double
    let pitchRadians: Double
    let horizontalFovRadians: Double
    let viewportId: String
    let boundingBox: [String: Double]
}

struct RequestResult: Encodable {
    let request: String
    let supported: Bool
    let error: String?
    let candidateCount: Int
}

struct FrameResult: Encodable {
    let sourceId: String
    let frameIndex: Int
    let timestampSeconds: Double
    let viewportCount: Int
    let candidates: [Candidate]
    let requests: [RequestResult]
}

struct Provenance: Encodable {
    let adapterId: String
    let adapterVersion: String
    let backendId: String
    let projectionStrategy: String
    let weightsSha256: String?
    let coordinateApproximation: String
}

struct GateOutput: Encodable {
    let schemaVersion: Int
    let provenance: Provenance
    let frames: [FrameResult]
    let limitations: [String]
}

enum GateError: Error, CustomStringConvertible {
    case usage
    case invalid(String)

    var description: String {
        switch self {
        case .usage:
            return "usage: vision_frame_gate INPUT.json OUTPUT.json"
        case .invalid(let message):
            return message
        }
    }
}

func radians(_ degrees: Double) -> Double { degrees * .pi / 180.0 }

func wrapYaw(_ value: Double) -> Double {
    var wrapped = value
    while wrapped > .pi { wrapped -= 2.0 * .pi }
    while wrapped < -.pi { wrapped += 2.0 * .pi }
    return wrapped
}

func privacySafeError(_ error: Error) -> String {
    let value = error as NSError
    return "\(value.domain):\(value.code)"
}

func sphericalCandidate(
    boundingBox box: CGRect,
    confidence: VNConfidence,
    kind: String,
    viewport: ViewportSpec,
    index: Int
) -> Candidate {
    let hFov = radians(viewport.horizontalFovDegrees)
    let aspect = 16.0 / 9.0
    let vFov = 2.0 * atan(tan(hFov / 2.0) / aspect)
    let centerX = box.midX
    let centerY = box.midY
    let yawOffset = atan((2.0 * centerX - 1.0) * tan(hFov / 2.0))
    let pitchOffset = atan((2.0 * centerY - 1.0) * tan(vFov / 2.0))
    let extent = max(0.01, 2.0 * atan(box.width * tan(hFov / 2.0)))
    return Candidate(
        id: "\(viewport.id):\(kind):\(index)",
        kind: kind,
        confidence: Double(confidence),
        yawRadians: wrapYaw(radians(viewport.yawDegrees) + yawOffset),
        pitchRadians: max(-.pi / 2.0, min(.pi / 2.0, radians(viewport.pitchDegrees) + pitchOffset)),
        horizontalFovRadians: min(.pi - 0.001, extent),
        viewportId: viewport.id,
        boundingBox: [
            "x": Double(box.origin.x),
            "y": Double(box.origin.y),
            "width": Double(box.width),
            "height": Double(box.height),
        ]
    )
}

func saliencyCandidates(
    _ observation: VNSaliencyImageObservation?,
    kind: String,
    viewport: ViewportSpec
) -> [Candidate] {
    guard let objects = observation?.salientObjects else { return [] }
    return objects.enumerated().map {
        sphericalCandidate(
            boundingBox: $0.element.boundingBox,
            confidence: $0.element.confidence,
            kind: kind,
            viewport: viewport,
            index: $0.offset
        )
    }
}

func analyze(_ input: GateInput) throws -> GateOutput {
    let safeSourceId = input.sourceId.range(
        of: "^[A-Za-z0-9._:-]+$", options: .regularExpression
    ) != nil
    guard safeSourceId else {
        throw GateError.invalid("sourceId contains unsupported characters")
    }
    guard !input.viewports.isEmpty else {
        throw GateError.invalid("at least one viewport is required")
    }

    var frames: [FrameResult] = []
    for viewport in input.viewports {
        guard (0.0..<180.0).contains(viewport.horizontalFovDegrees),
              viewport.timestampSeconds >= 0 else {
            throw GateError.invalid("invalid FOV or timestamp")
        }
        let imageURL = URL(fileURLWithPath: viewport.image)
        let attention = VNGenerateAttentionBasedSaliencyImageRequest()
        let objectness = VNGenerateObjectnessBasedSaliencyImageRequest()
        let humans = VNDetectHumanRectanglesRequest()
        var requestResults: [RequestResult] = []
        var candidates: [Candidate] = []

        do {
            try VNImageRequestHandler(url: imageURL, options: [:]).perform([attention])
            let found = saliencyCandidates(
                attention.results?.first as? VNSaliencyImageObservation,
                kind: "attention_saliency",
                viewport: viewport
            )
            candidates.append(contentsOf: found)
            requestResults.append(RequestResult(
                request: "VNGenerateAttentionBasedSaliencyImageRequest",
                supported: true, error: nil, candidateCount: found.count
            ))
        } catch {
            requestResults.append(RequestResult(
                request: "VNGenerateAttentionBasedSaliencyImageRequest",
                supported: false, error: privacySafeError(error), candidateCount: 0
            ))
        }

        do {
            try VNImageRequestHandler(url: imageURL, options: [:]).perform([objectness])
            let found = saliencyCandidates(
                objectness.results?.first as? VNSaliencyImageObservation,
                kind: "objectness_saliency",
                viewport: viewport
            )
            candidates.append(contentsOf: found)
            requestResults.append(RequestResult(
                request: "VNGenerateObjectnessBasedSaliencyImageRequest",
                supported: true, error: nil, candidateCount: found.count
            ))
        } catch {
            requestResults.append(RequestResult(
                request: "VNGenerateObjectnessBasedSaliencyImageRequest",
                supported: false, error: privacySafeError(error), candidateCount: 0
            ))
        }

        do {
            try VNImageRequestHandler(url: imageURL, options: [:]).perform([humans])
            let observations = humans.results ?? []
            let found = observations.enumerated().map {
                sphericalCandidate(
                    boundingBox: $0.element.boundingBox,
                    confidence: $0.element.confidence,
                    kind: "human_rectangle",
                    viewport: viewport,
                    index: $0.offset
                )
            }
            candidates.append(contentsOf: found)
            requestResults.append(RequestResult(
                request: "VNDetectHumanRectanglesRequest",
                supported: true, error: nil, candidateCount: found.count
            ))
        } catch {
            requestResults.append(RequestResult(
                request: "VNDetectHumanRectanglesRequest",
                supported: false, error: privacySafeError(error), candidateCount: 0
            ))
        }

        frames.append(FrameResult(
            sourceId: input.sourceId,
            frameIndex: input.frameIndex,
            timestampSeconds: viewport.timestampSeconds,
            viewportCount: 1,
            candidates: candidates,
            requests: requestResults
        ))
    }
    return GateOutput(
        schemaVersion: 1,
        provenance: Provenance(
            adapterId: "apple-vision-frame-gate",
            adapterVersion: "0.1.0",
            backendId: "Apple Vision (OS-provided requests)",
            projectionStrategy: "overlapping rectilinear viewports",
            weightsSha256: nil,
            coordinateApproximation: "rectilinear bounding-box center mapped with pinhole tangent geometry"
        ),
        frames: frames,
        limitations: [
            "Single-frame bootstrap evidence only; no tracking or cross-viewport deduplication.",
            "Candidate quality and benchmark recall are not established.",
            "Bounding-box extent is an approximation, not a spherical mask.",
            "Framework availability does not establish CPU/GPU/ANE placement.",
        ]
    )
}

do {
    guard CommandLine.arguments.count == 3 else { throw GateError.usage }
    let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
    let input = try JSONDecoder().decode(GateInput.self, from: Data(contentsOf: inputURL))
    let output = try analyze(input)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    try encoder.encode(output).write(to: outputURL, options: .atomic)
} catch {
    FileHandle.standardError.write(Data("vision_frame_gate: \(error)\n".utf8))
    exit(2)
}

import Foundation
import CoreMedia
import CoreVideo
import ImageIO
import Vision

struct FrameSpec: Decodable {
    let image: String
    let timestampSeconds: Double
}

struct ProbeInput: Decodable {
    let sourceId: String
    let frameWidth: Int
    let frameHeight: Int
    let frames: [FrameSpec]
}

struct MotionObservation: Encodable {
    let frameIndex: Int
    let timestampSeconds: Double
    let state: String
    let homographyRowMajor: [Double]?
    let translationXPixels: Double?
    let translationYPixels: Double?
    let translationXNormalized: Double?
    let translationYNormalized: Double?
    let translationMagnitudePixels: Double?
    let rotationProxyRadians: Double?
    let determinantProxy: Double?
    let error: String?
}

struct Summary: Encodable {
    let outcome: String
    let requestedFrameCount: Int
    let measuredPairCount: Int
    let errorPairCount: Int
    let rootMeanSquareTranslationPixels: Double?
    let p95TranslationPixels: Double?
    let maximumTranslationPixels: Double?
    let rootMeanSquareRotationProxyRadians: Double?
    let p95AbsoluteRotationProxyRadians: Double?
    let maximumAbsoluteRotationProxyRadians: Double?
}

struct Provenance: Encodable {
    let adapterId = "aegis.vision-motion-probe"
    let adapterVersion = "1"
    let backendId = "VNTrackHomographicImageRegistrationRequest"
    let transformConvention = "Vision warpTransform exported row-major; signed direction requires fixture calibration"
}

struct ProbeOutput: Encodable {
    let schemaVersion = 1
    let sourceId: String
    let provenance = Provenance()
    let observations: [MotionObservation]
    let summary: Summary
    let limitations: [String]
}

enum ProbeError: Error, CustomStringConvertible {
    case usage
    case invalid(String)

    var description: String {
        switch self {
        case .usage: return "usage: vision_motion_probe INPUT.json OUTPUT.json"
        case .invalid(let message): return message
        }
    }
}

func loadImage(_ path: String) throws -> CGImage {
    guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw ProbeError.invalid("image_decode_failed")
    }
    return image
}

func sampleBuffer(_ image: CGImage, timestamp: Double) throws -> CMSampleBuffer {
    var pixelBuffer: CVPixelBuffer?
    let attributes: [CFString: Any] = [
        kCVPixelBufferCGImageCompatibilityKey: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey: true
    ]
    let pixelStatus = CVPixelBufferCreate(
        kCFAllocatorDefault, image.width, image.height, kCVPixelFormatType_32BGRA,
        attributes as CFDictionary, &pixelBuffer)
    guard pixelStatus == kCVReturnSuccess, let pixelBuffer else {
        throw ProbeError.invalid("pixel_buffer_create_failed")
    }
    CVPixelBufferLockBaseAddress(pixelBuffer, [])
    defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, []) }
    guard let base = CVPixelBufferGetBaseAddress(pixelBuffer),
          let context = CGContext(
            data: base, width: image.width, height: image.height,
            bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(pixelBuffer),
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue |
                CGBitmapInfo.byteOrder32Little.rawValue) else {
        throw ProbeError.invalid("bitmap_context_create_failed")
    }
    context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    var format: CMVideoFormatDescription?
    guard CMVideoFormatDescriptionCreateForImageBuffer(
        allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer,
        formatDescriptionOut: &format) == noErr, let format else {
        throw ProbeError.invalid("format_description_create_failed")
    }
    var timing = CMSampleTimingInfo(
        duration: .invalid,
        presentationTimeStamp: CMTime(seconds: timestamp, preferredTimescale: 1_000_000),
        decodeTimeStamp: .invalid)
    var buffer: CMSampleBuffer?
    guard CMSampleBufferCreateForImageBuffer(
        allocator: kCFAllocatorDefault, imageBuffer: pixelBuffer, dataReady: true,
        makeDataReadyCallback: nil, refcon: nil, formatDescription: format,
        sampleTiming: &timing, sampleBufferOut: &buffer) == noErr, let buffer else {
        throw ProbeError.invalid("sample_buffer_create_failed")
    }
    return buffer
}

func safeError(_ error: Error) -> String {
    if let probe = error as? ProbeError { return probe.description }
    let value = error as NSError
    return "\(value.domain):\(value.code)"
}

func percentile(_ values: [Double], _ probability: Double) -> Double? {
    guard !values.isEmpty else { return nil }
    let sorted = values.sorted()
    let index = Int(ceil(probability * Double(sorted.count))) - 1
    return sorted[max(0, min(sorted.count - 1, index))]
}

func rms(_ values: [Double]) -> Double? {
    guard !values.isEmpty else { return nil }
    return sqrt(values.reduce(0) { $0 + $1 * $1 } / Double(values.count))
}

func validate(_ input: ProbeInput) throws {
    guard input.sourceId.range(of: "^[A-Za-z0-9._:-]+$", options: .regularExpression) != nil else {
        throw ProbeError.invalid("sourceId must be privacy-safe")
    }
    guard input.frameWidth > 0, input.frameHeight > 0 else {
        throw ProbeError.invalid("frame dimensions must be positive")
    }
    guard input.frames.count >= 2 else { throw ProbeError.invalid("at least two frames are required") }
    var prior = -Double.infinity
    for frame in input.frames {
        guard frame.timestampSeconds.isFinite, frame.timestampSeconds >= 0,
              frame.timestampSeconds > prior else {
            throw ProbeError.invalid("frame timestamps must be finite, nonnegative, and increasing")
        }
        prior = frame.timestampSeconds
    }
}

func run(_ input: ProbeInput) throws -> ProbeOutput {
    try validate(input)
    let request = VNTrackHomographicImageRegistrationRequest()
    request.revision = VNTrackHomographicImageRegistrationRequestRevision1
    let sequence = VNSequenceRequestHandler()
    var rows: [MotionObservation] = []
    var translations: [Double] = []
    var rotations: [Double] = []
    var errors = 0

    for index in 0..<input.frames.count {
        let frame = input.frames[index]
        do {
            let current = try loadImage(frame.image)
            let sample = try sampleBuffer(current, timestamp: frame.timestampSeconds)
            try sequence.perform([request], on: sample)
            if index == 0 {
                rows.append(MotionObservation(
                    frameIndex: 0, timestampSeconds: frame.timestampSeconds, state: "reference",
                    homographyRowMajor: nil, translationXPixels: nil, translationYPixels: nil,
                    translationXNormalized: nil, translationYNormalized: nil,
                    translationMagnitudePixels: nil, rotationProxyRadians: nil,
                    determinantProxy: nil, error: nil))
                continue
            }
            guard let observation = request.results?.first as? VNImageHomographicAlignmentObservation else {
                throw ProbeError.invalid("registration_observation_missing")
            }
            let h = observation.warpTransform
            // simd matrices are column-major. Export an unambiguous row-major array.
            let r00 = Double(h[0][0]); let r01 = Double(h[1][0]); let r02 = Double(h[2][0])
            let r10 = Double(h[0][1]); let r11 = Double(h[1][1]); let r12 = Double(h[2][1])
            let r20 = Double(h[0][2]); let r21 = Double(h[1][2]); let r22 = Double(h[2][2])
            let matrix: [Double] = [r00, r01, r02, r10, r11, r12, r20, r21, r22]
            let tx = matrix[2]
            let ty = matrix[5]
            let rotation = atan2(matrix[3], matrix[0])
            let determinantFirst = matrix[0] * matrix[4]
            let determinantSecond = matrix[1] * matrix[3]
            let determinant = determinantFirst - determinantSecond
            let magnitude = hypot(tx, ty)
            translations.append(magnitude)
            rotations.append(abs(rotation))
            rows.append(MotionObservation(
                frameIndex: index, timestampSeconds: frame.timestampSeconds, state: "measured",
                homographyRowMajor: matrix, translationXPixels: tx, translationYPixels: ty,
                translationXNormalized: tx / Double(input.frameWidth),
                translationYNormalized: ty / Double(input.frameHeight),
                translationMagnitudePixels: magnitude, rotationProxyRadians: rotation,
                determinantProxy: determinant, error: nil))
        } catch {
            if index > 0 { errors += 1 }
            rows.append(MotionObservation(
                frameIndex: index, timestampSeconds: frame.timestampSeconds, state: "error",
                homographyRowMajor: nil, translationXPixels: nil, translationYPixels: nil,
                translationXNormalized: nil, translationYNormalized: nil,
                translationMagnitudePixels: nil, rotationProxyRadians: nil,
                determinantProxy: nil, error: safeError(error)))
        }
    }

    return ProbeOutput(
        sourceId: input.sourceId,
        observations: rows,
        summary: Summary(
            outcome: translations.isEmpty ? "no_motion_observations" : "motion_observations_returned",
            requestedFrameCount: input.frames.count,
            measuredPairCount: translations.count,
            errorPairCount: errors,
            rootMeanSquareTranslationPixels: rms(translations),
            p95TranslationPixels: percentile(translations, 0.95),
            maximumTranslationPixels: translations.max(),
            rootMeanSquareRotationProxyRadians: rms(rotations),
            p95AbsoluteRotationProxyRadians: percentile(rotations, 0.95),
            maximumAbsoluteRotationProxyRadians: rotations.max()),
        limitations: [
            "Homography is image-registration evidence, not camera motion ground truth.",
            "Translation and rotation are local affine-derived proxies and may include parallax, rolling shutter, moving subjects, or registration error.",
            "Signed transform direction has not been calibrated because this environment returned no Vision observations.",
            "No stabilization or v360 runtime compensation is applied.",
            "Output contains no source path, pixels, thumbnails, faces, audio, GPS, or identity embeddings."
        ])
}

do {
    guard CommandLine.arguments.count == 3 else { throw ProbeError.usage }
    let inputData = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
    let input = try JSONDecoder().decode(ProbeInput.self, from: inputData)
    let output = try run(input)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    try encoder.encode(output).write(to: URL(fileURLWithPath: CommandLine.arguments[2]), options: .atomic)
} catch {
    FileHandle.standardError.write(Data(("vision_motion_probe: \(error)\n").utf8))
    exit(1)
}

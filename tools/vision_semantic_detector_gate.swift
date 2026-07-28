import CoreML
import Foundation
import ImageIO
import Vision

struct Label: Encodable {
    let identifier: String
    let confidence: Double
}

struct Box: Encodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct Detection: Encodable {
    let labels: [Label]
    let boundingBox: Box
}

struct Provenance: Encodable {
    let adapterId: String
    let backendId: String
    let modelId: String
    let modelSha256: String
    let projectionStrategy: String
}

struct Output: Encodable {
    let schemaVersion: Int
    let sourceId: String
    let frameIndex: Int
    let provenance: Provenance
    let resultType: String
    let detections: [Detection]
    let limitations: [String]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

guard CommandLine.arguments.count == 8 else {
    fail("usage: vision_semantic_detector_gate MODEL IMAGE OUTPUT SOURCE_ID FRAME_INDEX MODEL_ID MODEL_SHA256")
}
let modelPath = CommandLine.arguments[1]
let imagePath = CommandLine.arguments[2]
let outputPath = CommandLine.arguments[3]
let sourceId = CommandLine.arguments[4]
guard let frameIndex = Int(CommandLine.arguments[5]), frameIndex >= 0 else {
    fail("frame index must be nonnegative")
}
let modelId = CommandLine.arguments[6]
let modelSha256 = CommandLine.arguments[7]
let safe = try! NSRegularExpression(pattern: "^[A-Za-z0-9._:-]+$")
func safeId(_ value: String) -> Bool {
    safe.firstMatch(
        in: value, range: NSRange(value.startIndex..., in: value)
    ) != nil
}
guard safeId(sourceId), safeId(modelId),
      modelSha256.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil
else {
    fail("source, model ID, or checksum is not privacy-safe")
}
guard !FileManager.default.fileExists(atPath: outputPath) else {
    fail("refusing to overwrite output")
}

do {
    let modelURL = URL(fileURLWithPath: modelPath)
    let compiledURL = try MLModel.compileModel(at: modelURL)
    let coreModel = try MLModel(contentsOf: compiledURL)
    let visionModel = try VNCoreMLModel(for: coreModel)
    let imageURL = URL(fileURLWithPath: imagePath) as CFURL
    guard let source = CGImageSourceCreateWithURL(imageURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        fail("image_decode_failed")
    }
    let request = VNCoreMLRequest(model: visionModel)
    request.imageCropAndScaleOption = .scaleFill
    try VNImageRequestHandler(cgImage: image).perform([request])
    guard let results = request.results else {
        fail("Vision returned no results array")
    }
    guard results.allSatisfy({ $0 is VNRecognizedObjectObservation }) else {
        fail("model did not return recognized-object observations")
    }
    let detections = results.compactMap {
        $0 as? VNRecognizedObjectObservation
    }.map { observation in
        Detection(
            labels: observation.labels.prefix(3).map {
                Label(identifier: $0.identifier, confidence: Double($0.confidence))
            },
            boundingBox: Box(
                x: observation.boundingBox.origin.x,
                y: observation.boundingBox.origin.y,
                width: observation.boundingBox.width,
                height: observation.boundingBox.height
            )
        )
    }
    let document = Output(
        schemaVersion: 1,
        sourceId: sourceId,
        frameIndex: frameIndex,
        provenance: Provenance(
            adapterId: "aegis360.apple-yolov3-tiny-detector",
            backendId: "apple.vision-coreml",
            modelId: modelId,
            modelSha256: modelSha256,
            projectionStrategy: "rectilinear-viewport"
        ),
        resultType: "VNRecognizedObjectObservation",
        detections: detections,
        limitations: [
            "A synthetic contract pass does not establish natural-image recall.",
            "Labels and confidence are perception evidence, not editorial scores.",
            "This detector request does not establish temporal identity."
        ]
    )
    let data = try JSONEncoder().encode(document)
    try data.write(to: URL(fileURLWithPath: outputPath), options: .withoutOverwriting)
} catch {
    let value = error as NSError
    fail("detector_gate_failed:\(value.domain):\(value.code)")
}

import Foundation
import SoundAnalysis

private let allowedLabels = ["music", "applause", "clapping", "cheering"]

private final class Observer: NSObject, SNResultsObserving {
    var rows: [[String: Any]] = []
    var failure: Error?

    func request(_ request: any SNRequest, didProduce result: any SNResult) {
        guard let result = result as? SNClassificationResult else { return }
        let start = CMTimeGetSeconds(result.timeRange.start)
        let duration = CMTimeGetSeconds(result.timeRange.duration)
        var classifications: [[String: Any]] = []
        for label in allowedLabels {
            if let value = result.classification(forIdentifier: label) {
                classifications.append([
                    "label": label,
                    "confidence": value.confidence,
                ])
            }
        }
        rows.append([
            "start_seconds": start,
            "duration_seconds": duration,
            "classifications": classifications,
        ])
    }

    func request(_ request: any SNRequest, didFailWithError error: Error) {
        failure = error
    }

    func requestDidComplete(_ request: any SNRequest) {}
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("sound_event_gate: \(message)\n".utf8))
    exit(2)
}

guard CommandLine.arguments.count == 4 else {
    fail("usage: sound_event_gate INPUT_AUDIO SOURCE_ID OUTPUT_JSON")
}
let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let sourceID = CommandLine.arguments[2]
let outputURL = URL(fileURLWithPath: CommandLine.arguments[3])
guard FileManager.default.fileExists(atPath: inputURL.path) else {
    fail("input audio is missing")
}
guard !FileManager.default.fileExists(atPath: outputURL.path) else {
    fail("refusing to overwrite output")
}
guard sourceID.range(of: #"^[A-Za-z0-9._:-]+$"#, options: .regularExpression) != nil else {
    fail("source ID must be privacy-safe")
}

do {
    let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
    request.overlapFactor = 0.5
    let analyzer = try SNAudioFileAnalyzer(url: inputURL)
    let observer = Observer()
    try analyzer.add(request, withObserver: observer)
    analyzer.analyze()
    if let failure = observer.failure { throw failure }
    let artifact: [String: Any] = [
        "schema_version": "aegis360.apple-sound-events.v1",
        "source_id": sourceID,
        "classifier": [
            "framework": "Apple SoundAnalysis",
            "identifier": "SNClassifierIdentifierVersion1",
            "allowed_labels": allowedLabels,
            "overlap_factor": 0.5,
        ],
        "windows": observer.rows,
        "privacy": [
            "contains_source_path": false,
            "contains_audio": false,
            "contains_transcript": false,
        ],
        "limitations": [
            "classification confidence is model evidence, not editorial utility",
            "labels do not identify a sound source or direction",
        ],
    ]
    let payload = try JSONSerialization.data(
        withJSONObject: artifact, options: [.prettyPrinted, .sortedKeys]
    )
    try payload.write(to: outputURL, options: .withoutOverwriting)
    FileHandle.standardOutput.write(Data("windows=\(observer.rows.count)\n".utf8))
} catch {
    fail(String(describing: error))
}

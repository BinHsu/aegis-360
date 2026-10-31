import CoreImage
import CryptoKit
import Darwin
import Foundation
import MLX
import MLXLMCommon
import MLXVLM
import StageAProbe

@main
struct StageAFirstLogitsProbe {
    static func main() async {
        if CommandLine.arguments.count > 1 {
            exit(aegis_probe_dispatch(CommandLine.argc, CommandLine.unsafeArgv))
        }
        do {
            try await run()
        } catch {
            exit(3)
        }
    }

    static func run() async throws {
        guard CommandLine.arguments.count == 1,
              CommandLine.arguments[0].hasPrefix("/") else {
            throw StageAAdapterRequestError.invalid
        }
        var requestData = Data()
        while let part = try FileHandle.standardInput.read(
            upToCount: 65_537 - requestData.count), !part.isEmpty {
            requestData.append(part)
            if requestData.count > 65_536 { break }
        }
        let request = try StageAAdapterRequest.parse(requestData)
        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath,
                      isDirectory: true)
        let media = try StageAResolvedMedia.resolve(request, cwd: cwd)
        let promptRoot = URL(fileURLWithPath: request.promptRoot, isDirectory: true)
        let modelRoot = URL(fileURLWithPath: request.modelRoot, isDirectory: true)
        let prompt = try String(contentsOf:
            promptRoot.appending(component: "prompt.txt"), encoding: .utf8)
        let runtimeRoot = URL(fileURLWithPath: CommandLine.arguments[0])
            .deletingLastPathComponent()
        let library = runtimeRoot.appending(component: "default.metallib")
        guard FileManager.default.fileExists(atPath: library.path) else {
            throw StageAAdapterRequestError.invalid
        }
        GPU.metallib = library
        Memory.peakMemory = 0

        let processor = try await StageASmolProcessorRegistry.make(modelDirectory: modelRoot)
        let factory = VLMModelFactory(
            typeRegistry: VLMTypeRegistry.shared,
            processorRegistry: processor.registry,
            modelRegistry: VLMRegistry.shared)
        let container = try await factory.loadContainer(
            from: modelRoot, using: LocalTokenizerLoader())
        let sequence = try StageAFrameSequence.make(
            images: media.map { .ciImage(CIImage(cgImage: $0)) })
        let input = UserInput(chat: [
            .system(prompt),
            .user("Inspect the six ordered rows.", videos: [sequence.video]),
        ], processing: .init(video: sequence.processing))
        let prepared = try await container.prepare(input: input)
        let output: String = try await container.perform(nonSendable: prepared) {
            context, prepared in
            let promptTokens = prepared.text.tokens.asArray(Int32.self)
            let cache = try context.model.newCache(parameters: nil)
            let logits: MLXArray
            switch try context.model.prepare(
                prepared, cache: cache, state: nil,
                prefill: .init(stepSize: PrefillParameters.defaultStepSize)
            ) {
            case .logits(let result):
                logits = result.logits
            case .tokens:
                throw StageAAdapterRequestError.invalid
            }
            let values = logits[0..., -1, 0...].asType(.float32).asArray(Float.self)
            guard !values.isEmpty, values.allSatisfy(\.isFinite),
                  let top = values.enumerated().max(by: { $0.element < $1.element }) else {
                throw StageAAdapterRequestError.invalid
            }
            func sha256<T>(_ values: [T]) -> String {
                values.withUnsafeBytes { bytes in
                    SHA256.hash(data: Data(bytes: bytes.baseAddress!, count: bytes.count))
                        .map { String(format: "%02x", $0) }.joined()
                }
            }
            let record: [String: Any] = [
                "schema_version": "aegis360.stage-a-first-logits-probe.v1",
                "prompt_token_count": promptTokens.count,
                "prompt_token_sha256": sha256(promptTokens),
                "vocabulary_size": values.count,
                "first_logits_sha256": sha256(values),
                "top_token_id": top.offset,
            ]
            let data = try JSONSerialization.data(withJSONObject: record,
                options: [.sortedKeys])
            guard let text = String(data: data, encoding: .utf8) else {
                throw StageAAdapterRequestError.invalid
            }
            return text
        }
        guard !output.isEmpty, output.utf8.count <= 65_536,
              let bytes = output.data(using: .utf8) else {
            throw StageAAdapterRequestError.invalid
        }
        try writeMetrics()
        try FileHandle.standardOutput.write(contentsOf: bytes)
    }

    static func writeMetrics() throws {
        guard let temporary = ProcessInfo.processInfo.environment["TMPDIR"],
              temporary.hasPrefix("/Volumes/T7/aegis-360-items/") else {
            throw StageAAdapterRequestError.invalid
        }
        let path = URL(fileURLWithPath: temporary, isDirectory: true)
            .deletingLastPathComponent()
            .appending(component: "stage-a-guided-metrics.json")
        let data = try JSONSerialization.data(withJSONObject: [
            "schema_version": "aegis360.stage-a-guided-mlx-memory.v1",
            "peak_active_bytes": Memory.peakMemory,
            "final_active_bytes": Memory.activeMemory,
            "final_cache_bytes": Memory.cacheMemory,
        ], options: [.sortedKeys])
        let fd = open(path.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
        guard fd >= 0 else { throw StageAAdapterRequestError.invalid }
        defer { close(fd) }
        try data.withUnsafeBytes { buffer in
            guard let base = buffer.baseAddress else { return }
            var offset = 0
            while offset < buffer.count {
                let count = Darwin.write(fd, base.advanced(by: offset), buffer.count - offset)
                guard count > 0 else { throw StageAAdapterRequestError.invalid }
                offset += count
            }
        }
        guard fsync(fd) == 0 else { throw StageAAdapterRequestError.invalid }
    }
}

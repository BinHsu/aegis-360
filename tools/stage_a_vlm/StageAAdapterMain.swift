import CoreImage
import Foundation
import MLX
import MLXLMCommon
import MLXVLM
import StageAProbe

@main
struct StageAAdapterMain {
    static func main() async {
        if CommandLine.arguments.count > 1 {
            exit(aegis_probe_dispatch(CommandLine.argc, CommandLine.unsafeArgv))
        }
        do {
            try await run()
        } catch {
            // The coordinator maps every nonzero exit to an operational abstention.
            // Paths, source pixels and model diagnostics must not reach stderr.
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
        let parameters = GenerateParameters(maxTokens: 512, temperature: 0, seed: 0)
        let stream = try await container.generate(input: prepared, parameters: parameters)
        var output = ""
        for await generation in stream {
            switch generation {
            case .chunk(let text):
                output += text
                guard output.utf8.count <= 65_536 else {
                    throw StageAAdapterRequestError.invalid
                }
            case .info:
                break
            case .toolCall, .rejectedToolCall:
                throw StageAAdapterRequestError.invalid
            }
        }
        guard !output.isEmpty, let bytes = output.data(using: .utf8) else {
            throw StageAAdapterRequestError.invalid
        }
        try FileHandle.standardOutput.write(contentsOf: bytes)
    }
}

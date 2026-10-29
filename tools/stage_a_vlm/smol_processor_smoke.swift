import CoreImage
import Foundation
import MLX
import MLXLMCommon
import MLXVLM

@main
struct SmolProcessorSmoke {
    static func main() async {
        do {
            try await run()
        } catch {
            fputs("Smol processor input error\n", stderr)
            exit(5)
        }
    }

    static func run() async throws {
        guard CommandLine.arguments.count == 4 else {
            fputs("usage: smol-processor-smoke MODEL LIBRARY PROMPT\n", stderr)
            exit(2)
        }
        let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        GPU.metallib = URL(fileURLWithPath: CommandLine.arguments[2])
        let prompt = try String(contentsOfFile: CommandLine.arguments[3], encoding: .utf8)
        let tokenizer = try await LocalTokenizerLoader().load(from: directory)
        let setup = try await StageASmolProcessorRegistry.make(modelDirectory: directory)
        do {
            _ = try await setup.registry.createModel(
                configuration: Data(), processorType: "SmolVLMProcessor", tokenizer: tokenizer)
            fputs("changed processor metadata accepted\n", stderr)
            exit(3)
        } catch StageASmolProcessorError.changedPreprocessor {
            // A changed loader input must fail before image preparation.
        }
        let processor = try await setup.registry.createModel(
            configuration: setup.preprocessorData,
            processorType: "SmolVLMProcessor", tokenizer: tokenizer)
        let images: [UserInput.Image] = (0..<6).map { index in
            let color = CIColor(red: CGFloat(index + 1) / 10, green: 0, blue: 0, alpha: 1)
            return .ciImage(CIImage(color: color).cropped(
                to: CGRect(x: 0, y: 0, width: 2, height: 2)))
        }
        let sequence = try StageAFrameSequence.make(images: images)
        let input = UserInput(chat: [
            .system(prompt),
            .user("Inspect the six ordered rows.", videos: [sequence.video]),
        ], processing: .init(video: sequence.processing))
        let prepared = try await processor.prepare(input: input)
        let tokens = prepared.text.tokens.asArray(Int32.self)
        let imageTokens = tokens.filter { $0 == 49190 }.count
        guard imageTokens == 6 * 81,
              prepared.image?.frames?.count == 6 else {
            fputs("Smol image token or frame count mismatch\n", stderr)
            exit(4)
        }
        let decoded = tokenizer.decode(tokenIds: tokens.map(Int.init), skipSpecialTokens: false)
        guard let pixels = prepared.image?.pixels,
              pixels.shape == [6, 384, 384, 3] else {
            fputs("Smol prepared pixel shape mismatch\n", stderr)
            exit(7)
        }
        let red = (0..<6).map { pixels[$0, 192, 192, 0].item(Float.self) }
        guard zip(red, red.dropFirst()).allSatisfy({ $0.0 + 0.01 < $0.1 }) else {
            fputs("Smol prepared pixel order mismatch\n", stderr)
            exit(8)
        }
        guard let user = decoded.range(of: "User: "),
              let frames = decoded.range(of: "Frame from"),
              let instruction = decoded.range(of: "Inspect the six ordered rows."),
              let assistant = decoded.range(of: "Assistant:", options: .backwards),
              user.lowerBound < frames.lowerBound,
              frames.lowerBound < instruction.lowerBound,
              instruction.lowerBound < assistant.lowerBound else {
            fputs("Smol prepared prompt placement mismatch\n", stderr)
            exit(9)
        }
        guard decoded.contains("bounded visual observer"),
              !decoded.contains("You are a helpful assistant that can understand videos") else {
            fputs("Smol system prompt mismatch\n", stderr)
            exit(6)
        }
        print("Smol processor: 6 frames, 486 image tokens, ordered pixels, prompt placement")
    }
}

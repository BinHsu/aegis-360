import Foundation
import Tokenizers

@main
struct CheckStageATokenizer {
    static func main() async throws {
        guard CommandLine.arguments.count == 2 else {
            fputs("usage: tokenizer-smoke MODEL_DIRECTORY\n", stderr)
            exit(2)
        }
        let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let tokenizer = try await AutoTokenizer.from(modelFolder: directory)
        let text = "hello world"
        let tokens = tokenizer.encode(text: text, addSpecialTokens: false)
        let decoded = tokenizer.decode(tokens: tokens, skipSpecialTokens: true)
        guard !tokens.isEmpty, decoded == text else {
            fputs("tokenizer round trip failed\n", stderr)
            exit(3)
        }
        print("local tokenizer round trip: \(tokens.count) tokens")
    }
}

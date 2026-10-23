import Foundation
import MLXLMCommon
import MLXVLM

@main
struct BridgeSmoke {
    static func main() async {
        do {
            try await run()
        } catch {
            fputs("bridge input error\n", stderr)
            exit(5)
        }
    }

    static func run() async throws {
        guard CommandLine.arguments.count == 2 else {
            fputs("usage: bridge-smoke MODEL_DIRECTORY\n", stderr)
            exit(2)
        }
        let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let tokenizer = try await LocalTokenizerLoader().load(from: directory)
        let text = "hello world"
        let ids = tokenizer.encode(text: text, addSpecialTokens: false)
        let decoded = tokenizer.decode(tokenIds: ids, skipSpecialTokens: true)
        guard !ids.isEmpty, decoded == text else {
            fputs("bridge round trip failed\n", stderr)
            exit(3)
        }
        let messages: [[String: any Sendable]] = [["role": "user", "content": text]]
        let chat = try tokenizer.applyChatTemplate(messages: messages)
        guard !chat.isEmpty else {
            fputs("bridge chat template returned no tokens\n", stderr)
            exit(4)
        }
        print("local VLM tokenizer bridge: \(ids.count) text tokens, \(chat.count) chat tokens")
    }
}

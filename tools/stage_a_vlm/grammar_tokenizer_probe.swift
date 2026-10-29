import Foundation
import MLXGuidedGeneration
import MLXLMCommon

@main
struct GrammarTokenizerProbe {
    static func main() async throws {
        guard CommandLine.arguments.count == 3 else { throw ProbeError.arguments }
        let schema = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8)
        let model = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
        let host = try await LocalTokenizerLoader().load(from: model)
        let extracted = TokenizerVocabExtractor.extractForGrammar(from: host)
        guard let eos = host.eosTokenId else { throw ProbeError.missingEOS }
        let grammarTokenizer = try GrammarTokenizer(
            vocab: extracted.vocab, vocabType: extracted.vocabType,
            eosTokenId: Int32(eos))

        func allowed(_ mask: MaskResult, _ id: Int) -> Bool {
            guard id >= 0 && id < grammarTokenizer.vocabSize else { return false }
            let word = UInt32(bitPattern: mask.mask[id / 32])
            return (word & (UInt32(1) << (id % 32))) != 0
        }

        let constraint = try GrammarConstraint(tokenizer: grammarTokenizer,
                                               jsonSchema: schema)
        let first = try constraint.computeMask()
        let brace = host.encode(text: "{", addSpecialTokens: false)
        let prose = host.encode(text: "Hello", addSpecialTokens: false)
        guard let braceFirst = brace.first, let proseFirst = prose.first else {
            throw ProbeError.emptyEncoding
        }
        let braceAllowed = allowed(first, braceFirst)
        let proseExcluded = !allowed(first, proseFirst)

        let observed = """
        {"status":"observed","early_state_coherence":"observed","late_state_coherence":"observed","activity_relation":"same","setting_relation":"same","anonymous_participant_configuration":"same","transition_support":"contradicts","viewpoint_change":"absent","foreground_rearrangement":"absent","exposure_or_palette_change":"absent","capture_or_projection_artifact":"absent"}
        """
        var complete = true
        for id in host.encode(text: observed, addSpecialTokens: false) {
            if !allowed(try constraint.computeMask(), id) {
                complete = false
                break
            }
            _ = try constraint.commitToken(Int32(id))
        }
        if complete {
            complete = allowed(try constraint.computeMask(), eos)
            if complete { complete = try constraint.commitToken(Int32(eos)).isTerminated }
        }
        let result: [String: Any] = [
            "vocab_size": grammarTokenizer.vocabSize,
            "eos_token_id": eos,
            "brace_allowed": braceAllowed,
            "prose_excluded": proseExcluded,
            "observed_accepted": complete,
        ]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
        guard braceAllowed, proseExcluded, complete else { throw ProbeError.failed }
    }
}

enum ProbeError: Error { case arguments, missingEOS, emptyEncoding, failed }

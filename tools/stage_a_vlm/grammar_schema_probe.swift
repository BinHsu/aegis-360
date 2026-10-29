import Foundation
import MLXGuidedGeneration

@main
struct GrammarSchemaProbe {
    static func main() throws {
        guard CommandLine.arguments.count == 2 else { throw ProbeError.arguments }
        let schema = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8)
        let vocab = (0 ..< 256).map { String(format: "<0x%02X>", $0) }
        let tokenizer = try GrammarTokenizer(vocab: vocab, vocabType: .byteFallback,
                                             eosTokenId: 255)

        func allowed(_ mask: MaskResult, _ byte: UInt8) -> Bool {
            let index = Int(byte)
            let word = UInt32(bitPattern: mask.mask[index / 32])
            return (word & (UInt32(1) << (index % 32))) != 0
        }

        func accepts(_ value: String) throws -> Bool {
            let matcher = try GrammarConstraint(tokenizer: tokenizer, jsonSchema: schema)
            for byte in value.utf8 {
                let mask = try matcher.computeMask()
                if !allowed(mask, byte) { return false }
                _ = try matcher.commitToken(Int32(byte))
            }
            let last = try matcher.computeMask()
            guard allowed(last, 255) else { return false }
            return try matcher.commitToken(255).isTerminated
        }

        let matcher = try GrammarConstraint(tokenizer: tokenizer, jsonSchema: schema)
        let first = try matcher.computeMask()
        let proseExcluded = !allowed(first, 72) // H
        let braceAllowed = allowed(first, 123) // {

        let observed = """
        {"status":"observed","early_state_coherence":"observed","late_state_coherence":"observed","activity_relation":"same","setting_relation":"same","anonymous_participant_configuration":"same","transition_support":"contradicts","viewpoint_change":"absent","foreground_rearrangement":"absent","exposure_or_palette_change":"absent","capture_or_projection_artifact":"absent"}
        """
        let extra = observed.replacingOccurrences(of: "{\"status\"",
                                                   with: "{\"extra\":\"x\",\"status\"")
        let badAbstain = observed.replacingOccurrences(of: "\"observed\"",
                                                       with: "\"abstain\"",
                                                       range: observed.range(of: "\"observed\""))
        let result: [String: Bool] = [
            "schema_compiled": true,
            "brace_allowed": braceAllowed,
            "prose_excluded": proseExcluded,
            "observed_accepted": try accepts(observed),
            "extra_rejected": try !accepts(extra),
            "truncated_rejected": try !accepts("{"),
            "bad_abstain_rejected": try !accepts(badAbstain),
        ]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
        guard result["brace_allowed"] == true,
              result["prose_excluded"] == true,
              result["observed_accepted"] == true,
              result["extra_rejected"] == true,
              result["truncated_rejected"] == true else {
            throw ProbeError.failed
        }
    }
}

enum ProbeError: Error { case arguments, failed }

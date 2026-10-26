import Foundation
import MLXLMCommon
import MLXVLM

enum StageASmolProcessorError: Error {
    case unexpectedMetadata
    case changedPreprocessor
}

/// Merge the model's split local processor metadata without changing its asset tree.
struct StageASmolProcessorRegistry {
    static func make(modelDirectory: URL) async throws ->
        (registry: ProcessorTypeRegistry, preprocessorData: Data)
    {
        let preprocessorData = try Data(contentsOf:
            modelDirectory.appending(component: "preprocessor_config.json"))
        let processorData = try Data(contentsOf:
            modelDirectory.appending(component: "processor_config.json"))
        guard var preprocessor = try JSONSerialization.jsonObject(with: preprocessorData)
                as? [String: Any],
              let processor = try JSONSerialization.jsonObject(with: processorData)
                as? [String: Any],
              preprocessor["processor_class"] as? String == "SmolVLMProcessor",
              processor["processor_class"] as? String == "SmolVLMProcessor",
              let sequenceLength = processor["image_seq_len"] as? Int,
              sequenceLength == 81,
              preprocessor["image_seq_len"] == nil else {
            throw StageASmolProcessorError.unexpectedMetadata
        }
        preprocessor["image_seq_len"] = sequenceLength
        let merged = try JSONSerialization.data(withJSONObject: preprocessor)
        let configuration = try JSONDecoder().decode(
            SmolVLMProcessorConfiguration.self, from: merged)
        guard configuration.imageSequenceLength == sequenceLength else {
            throw StageASmolProcessorError.unexpectedMetadata
        }
        let registry = ProcessorTypeRegistry()
        await registry.registerProcessorType("SmolVLMProcessor") { raw, tokenizer in
            guard raw == preprocessorData else {
                throw StageASmolProcessorError.changedPreprocessor
            }
            return SmolVLMProcessor(configuration, tokenizer: tokenizer)
        }
        return (registry, preprocessorData)
    }
}

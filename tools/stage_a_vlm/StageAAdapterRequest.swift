import CoreFoundation
import Foundation

enum StageAAdapterRequestError: Error {
    case invalid
}

/// Shape-only parse of the coordinator's canonical one-packet request.
/// Root identity and asset contents are proved by the retained launcher, not here.
struct StageAAdapterRequest {
    let packetID: String
    let mediaPaths: [String]
    let promptRoot: String
    let modelRoot: String

    static func parse(_ data: Data) throws -> Self {
        guard !data.isEmpty, data.count <= 65_536,
              let value = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let canonical = try? JSONSerialization.data(
                withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes]),
              canonical == data,
              keys(value, ["schema_version", "packet_id", "projection", "media",
                           "prompt_schema", "model"]),
              value["schema_version"] as? String ==
                "aegis360.sparse-story-adapter-request.v1",
              let packetID = value["packet_id"] as? String,
              packetID.hasPrefix("packet-"), packetID.count == 27,
              hex(String(packetID.dropFirst(7)), count: 20),
              let projection = object(value["projection"], keys: [
                "schema_version", "packet_id", "rows", "privacy", "authority"]),
              projection["schema_version"] as? String ==
                "aegis360.sparse-story-adapter-projection.v1",
              projection["packet_id"] as? String == packetID,
              let rows = projection["rows"] as? [Any], rows.count == 6,
              let media = value["media"] as? [Any], media.count == 6,
              let privacy = projection["privacy"] as? [String: Any],
              let authority = projection["authority"] as? [String: Any],
              flags(privacy, names: [
                "contains_source_id", "contains_event_id", "contains_signal",
                "contains_source_time", "contains_position", "contains_proposal_control_role",
                "contains_lineage_hash", "contains_signal_evidence",
                "contains_score_or_confidence", "contains_expected_class",
                "contains_identity", "contains_real_candidate_id", "contains_geometry",
                "contains_chapter_label", "contains_narrative_function",
                "contains_prose", "contains_edit_request"], trueName: nil),
              flags(authority, names: [
                "semantic_observation_input", "exact_boundary", "chapter_map", "camera",
                "reorder", "render"], trueName: "semantic_observation_input"),
              let prompt = object(value["prompt_schema"], keys: [
                "manifest_sha256", "root_path", "prompt_path", "schema_path"]),
              let model = object(value["model"], keys: ["manifest_sha256", "root_path"]),
              let promptHash = prompt["manifest_sha256"] as? String,
              let modelHash = model["manifest_sha256"] as? String,
              hex(promptHash, count: 64), hex(modelHash, count: 64),
              prompt["prompt_path"] as? String == "prompt.txt",
              prompt["schema_path"] as? String == "raw-observation-schema.json",
              let promptRoot = prompt["root_path"] as? String, root(promptRoot),
              let modelRoot = model["root_path"] as? String, root(modelRoot) else {
            throw StageAAdapterRequestError.invalid
        }

        let roles = ["early_far", "early_near", "transition_before",
                     "transition_after", "late_near", "late_far"]
        let views = ["view-1", "view-2", "view-3", "view-4"]
        var paths: [String] = []
        for index in 0..<6 {
            let expected = "media/\(packetID)/row-\(String(format: "%02d", index + 1)).png"
            guard let row = Self.object(rows[index], keys: [
                "row_number", "row_role", "media_ref", "views"]),
                  let number = row["row_number"] as? NSNumber,
                  CFGetTypeID(number) != CFBooleanGetTypeID(),
                  number.intValue == index + 1,
                  row["row_role"] as? String == roles[index],
                  row["media_ref"] as? String == expected,
                  row["views"] as? [String] == views,
                  let item = Self.object(media[index], keys: ["media_ref", "path"]),
                  item["media_ref"] as? String == expected,
                  item["path"] as? String == expected else {
                throw StageAAdapterRequestError.invalid
            }
            paths.append(expected)
        }
        return .init(packetID: packetID, mediaPaths: paths,
                     promptRoot: promptRoot, modelRoot: modelRoot)
    }

    private static func keys(_ value: [String: Any], _ names: Set<String>) -> Bool {
        Set(value.keys) == names
    }

    private static func object(_ value: Any?, keys names: Set<String>) -> [String: Any]? {
        guard let value = value as? [String: Any], keys(value, names) else { return nil }
        return value
    }

    private static func hex(_ value: String, count: Int) -> Bool {
        value.utf8.count == count && value.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    private static func root(_ value: String) -> Bool {
        value.hasPrefix("/") && !value.contains("//") &&
            !value.split(separator: "/").contains(where: { $0 == "." || $0 == ".." }) &&
            (value == "/" || !value.hasSuffix("/"))
    }

    private static func flags(_ value: [String: Any], names: Set<String>,
                              trueName: String?) -> Bool {
        guard keys(value, names) else { return false }
        for name in names {
            guard let flag = value[name] as? NSNumber,
                  CFGetTypeID(flag) == CFBooleanGetTypeID(),
                  flag.boolValue == (name == trueName) else { return false }
        }
        return true
    }
}

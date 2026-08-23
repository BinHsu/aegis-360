"""Constrained raw output for a local scene-story adapter."""


def local_scene_story_json_schema() -> dict[str, object]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["status", "structural_role", "narrative_function",
                     "change_type", "viewer_value"],
        "properties": {
            "status": {"enum": ["observed", "abstain"]},
            "structural_role": {"enum": ["chapter_boundary", "within_chapter_cut",
                                                  "ending_transition", "unknown"]},
            "narrative_function": {"enum": ["establish_context", "action_continuation",
                                                     "activity_transition", "tension_build",
                                                     "tension_release", "closing", "unknown"]},
            "change_type": {"enum": ["hard_cut", "gradual_transition", "motion_peak", "unknown"]},
            "viewer_value": {"enum": ["primary", "supporting", "low", "unknown"]},
        },
    }

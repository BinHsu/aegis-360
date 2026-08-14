# SmolVLM2 2.2B context gate — 2026-08-13

Status: Group proposal selection passed; fine context class unverified

The owner authorized the pinned MLX BF16 conversion. The primary weight is
4,493,651,795 bytes and matches SHA-256
`ed6c59250704f09f921dce1a25e0d4eff611b6c9c53e382a7eb04ce9113f2773`.

The first four-frame grammar run recognized `conversation` and the relevant
visual evidence, but paired group scope with a person proposal. The schema was
corrected to encode mutually exclusive scope/candidate branches using `anyOf`;
llguidance 1.7.6 does not support strict `oneOf`, while the scope constants make
these branches mutually exclusive.

The corrected exploratory run returned `conversation`, `group`, and
`group:window:1`. Model elapsed time was 25.57 seconds, MLX peak memory 6.97 GB,
maximum RSS 3,350,822,912 bytes and swap zero.

The formal repository runner reproduced the valid group selection and emitted
a path-free scene-context v2 artifact. It took 25.05 seconds model elapsed,
MLX peak memory 6.97 GB, maximum RSS 1,961,394,176 bytes and swap zero. It
classified the same frames as `ambient_people` rather than `conversation`,
while retaining group selection and the same present visual flags. Therefore
the directing gate passes only for choosing the group proposal. Fine context
classification and cross-scene accuracy are not established.

## Fixed-input repeatability

Two additional formal runs used the same four rendered frame bytes, proposal,
model checksum, prompt, grammar and runtime. Both returned the same complete
decision as the retained formal artifact: `ambient_people`, `group`,
`group:window:1`, the same evidence flags, and silent-input audio marked
unknown. Model elapsed times were 24.75 and 25.15 seconds; both reported a
6.97 GB MLX peak. This establishes bounded repeatability for this fixed input
and runtime only. It is not an accuracy or cross-scene determinism claim.

## Held-out non-group gate

The first three seconds of the separate Old Ghost Road t60 bicycle render were
manually screened before inference. Three samples contain only environment and
bicycle-related background; the fourth contains one partial cyclist entering
the frame. No multi-person interaction is visible. The proposal declared only
one person slot and forward context, so the grammar contained no group branch.

The formal runner returned `uncertain` scope with no selected candidate and all
visual flags unknown. It did not promote the partial cyclist or environment to
a group. Model elapsed time was 25.77 seconds, MLX peak memory 6.97 GB, maximum
RSS 897,695,744 bytes and swap zero. The fine class remained `ambient_people`,
reinforcing that only proposal-selection behavior is accepted.

This one positive and one negative window establish a bounded proof against an
always-group selector, not held-out accuracy. More scenes are still required.

## Cross-video coordinated group gate

A Bellpuig 18.0–22.0 second window provides a distinct held-out positive. Four
manually screened `yaw=90`, 110-degree frames contain at least four motocross
riders jointly racing in every sample. The group remains inside the viewport;
this is neither the Old Ghost Road source nor a conversation scene.

The formal runner selected `group:window:1` with group scope in 25.80 seconds,
at a 6.97 GB MLX peak. This supports group selection across two sources and two
types of activity. It does not establish accuracy: the model called the scene
`ambient_people` and falsely marked mouth motion and reciprocal orientation as
present despite full-face helmets and forward racing. Treat every fine class
and evidence flag as scoreless; only the closed proposal selection passed.

External artifact:
`outputs/window-group-proposals/old-ghost-road-t68p5-4s-v2-pitch-guard5/local-vlm-context-2.2b.json`

Held-out Bellpuig artifacts:
`outputs/window-group-proposals/bellpuig-t18-4s-heldout-v1/`

## Cross-video landscape context failure

Four 360-degree-screened samples from Skiing at 389.0–393.0 seconds show an
open snow landscape. Tiny distant dark pixels may be people, so the annotation
does not claim complete human absence; it only declares that the samples do
not support a director-worthy person candidate. The proposal intentionally
contains only `context:forward`.

The formal runner returned uncertain scope with no selection in 24.91 seconds
at a 6.97 GB MLX peak. It also called the scene `ambient_people`, while leaving
all visual evidence unknown. This is a valid refusal but a failed context
selection. The accepted capability must therefore be narrowed from generic
proposal selection to a bounded group-vs-not-group gate when geometry supplies
a group proposal. Do not prompt-tune this single negative into a pass.

Held-out Skiing artifacts:
`outputs/window-group-proposals/skiing-t389-4s-heldout-v1/`

## Mechanical gate summary

`scripts/summarize_local_context_gate.py` matches path-free results to an
independently screened expectation manifest by source/window ID. It scores
only closed selection outcomes and deliberately excludes context class and
evidence flags. The three durable real artifacts produce two passing group
cases and one explicit failure: Skiing expected context selection but observed
abstention. The command exits nonzero because not all expectations are met.
No percentage or accuracy estimate is reported from this tiny bounded set.

No source path, frame path, pixels, embeddings or identity claim is stored.

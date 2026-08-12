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
classification and deterministic repeatability are not established.

External artifact:
`outputs/window-group-proposals/old-ghost-road-t68p5-4s-v2-pitch-guard5/local-vlm-context-2.2b.json`

No source path, frame path, pixels, embeddings or identity claim is stored.

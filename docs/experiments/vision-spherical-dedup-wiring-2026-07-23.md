# Vision spherical-dedup wiring — 2026-07-23

Status: Observed contract-wiring evidence; no quality or backend decision

## Question

Can the fixed-five Old Ghost Road Apple Vision evidence be ingested through
the model-independent perception contract, deduplicated in spherical space,
and optionally passed to the greedy baseline without using detector
confidence as editorial interest?

## Implementation and safety

The stable command is:

```sh
scripts/run_vision_spherical_dedup_report.sh \
  INPUT_BATCH_DIR OUTPUT_REPORT [GREEDY_TRACE]
```

The runner is parameterized, refuses existing output files, performs no
network or media decoding, and writes no absolute input path. The report
contains a privacy-safe source ID, adapter/deduplicator provenance, aggregate
and per-sample raw/cluster/kind counts, and cluster member observation IDs. It
does not copy bounding boxes or detector confidence.

Deduplication uses the existing confidence-free same-kind spherical geometry
rule: 12-degree maximum center distance, extent scale 0.6 and 2-degree minimum
extent gate. Connected components retain member IDs and provenance. This rule
can transitively merge a chain of nearby observations.

The optional greedy trace is deliberately non-editorial. Every candidate gets
one absent `neutral_contract_wiring` component with weight 0, hence utility 0.
Selection is only the deterministic candidate-ID tie-break. Vision confidence
is neither a scoring input nor a tie-break.

## Mock gate

`tests/test_vision_spherical_dedup_report.sh` creates two synthetic timestamps
with two same-kind, nearby candidates whose confidence values are deliberately
0.99 and 0.01. It verifies:

- four raw observations become two clusters;
- member observation IDs are retained;
- confidence is marked unused;
- every greedy contribution is zero;
- neither report contains its temporary absolute path or bounding boxes; and
- a second run cannot overwrite the first report.

The dependency-free Python suite had 51 passing tests after this addition.
Shell syntax validation also passed.

## Fixed-five observation

- Repository base: `f583407` plus this experiment implementation
- Source: `old_ghost_road_360`
- Source manifest SHA-256:
  `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`
- Input: existing Apple Vision fixed-five evidence at timestamps 15, 60, 105,
  150 and 210 seconds; no video was read
- Raw artifacts: configured external data root under
  `outputs/vision-spherical-dedup/old-ghost-road-fixed-v1/`; not committed

Observed counts:

| Kind | Raw candidates | Clusters |
| --- | ---: | ---: |
| attention saliency | 20 | 20 |
| objectness saliency | 12 | 12 |
| human rectangle | 5 | 5 |
| **Total** | **37** | **37** |

No candidates merged under the configured rule. This is only the output of
the rule on five unreviewed samples. It does not show that duplicates were
absent, that the thresholds are correct, or that the projection strategy has
acceptable duplicate behavior.

The optional trace produced five decisions. All candidate utilities were
exactly zero and the selected ID was `yaw_0:attention_saliency:0` at every
timestamp because it sorts first among the available IDs. That is contract
wiring, not a meaningful view choice or directing result.

A scan of both external JSON outputs found no `/Users/`, `/Volumes/`,
`bounding_box`, or copied confidence field.

## Conclusion and next evidence

Real Vision JSON now reaches spherical dedup and the greedy contract without
turning backend confidence into editorial value. The fixed-five run neither
measures duplicate rate nor validates directing quality. The next relevant
evidence is completed human review of these samples, followed by comparison
of annotated duplicate groups against geometric clustering and the addition
of genuine editorial signals before evaluating planner choices.

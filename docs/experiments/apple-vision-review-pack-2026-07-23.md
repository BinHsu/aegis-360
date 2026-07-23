# Apple Vision fixed-sample review pack

Status: Artifact generated; qualitative box-placement gate accepted

## User acceptance boundary

After reviewing the bootstrap presentation, the project owner judged the
candidate box placement accurate enough to continue the POC. This is a
qualitative localization gate: the boxes are usable for the next iteration.
It is not a per-candidate annotation, recall or precision measurement, viewer-
preference result, backend selection, or evidence that the chosen viewpoint is
interesting. Those questions remain separate gates.

## Purpose

Create a local, manually inspectable bridge between Apple Vision candidate
counts and later candidate-recall review. This is a review aid, not an
annotation result and not evidence that Vision is a sufficient perception
backend.

## Reproduction

The stable runner is `scripts/run_vision_review_pack.sh`. It accepts an input
video, a new output directory, a privacy-safe source ID, and a timestamp file.
For every timestamp it extracts four 100-degree equatorial rectilinear
viewports at yaw 0, 90, 180 and -90 degrees, runs the versioned Vision gate,
draws candidate ID and kind boxes, and creates a 2x2 contact sheet.

The runner refuses to overwrite an existing output directory. Review media is
local-only and must not be committed.

## Old Ghost Road artifact record

- Source manifest ID: `old_ghost_road_360`
- Source SHA-256: `4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc`
- Timestamp config: `benchmarks/vision-gate-timestamps/old_ghost_road_360.txt`
- Timestamps: 15, 60, 105, 150 and 210 seconds
- Samples/contact sheets: 5
- Raw rectilinear viewports: 20
- Annotated rectilinear viewports: 20
- Unreviewed candidates by timestamp: 6, 7, 14, 6 and 4 (37 total)
- Privacy-safe review index bytes: 8,962
- Review index SHA-256:
  `7f4a1e2af91640fd7eaa0ee3ae301297936abbf0b1223082ea8eba10393ccfb9`

The artifact is stored under the configured external data root. Its absolute
path is intentionally excluded from this record and from the review index.

## Privacy and review state

The index contains only source ID, timestamps, viewport IDs, candidate IDs and
kinds, relative artifact paths, counts, and explicit empty human-review
fields. It contains no absolute source path or identity label. Candidate
recall is `null`, notes are `null`, and reviewed is `false`; the tooling never
fills those values automatically.

## Limitations

- The candidate boxes and counts have not been manually validated.
- Candidate confidence is not editorial interest.
- The four equatorial viewports leave polar blind regions.
- Boxes use the gate's approximate rectilinear-to-spherical mapping.
- This run does not measure tracking, cross-timestamp identity, precision,
  recall, duplicate rate, compute placement, or sustained performance.
- Derived frames inherit the source footage's CC BY-SA 3.0 obligations and
  are not public repository artifacts.

# Perception review annotations

Status: Schema implemented; no benchmark annotations completed

## Purpose

Schema v1 records a minimal manual review of fixed-timestamp, four-viewport
Vision evidence. It separates what an ordinary first-time viewer might find
interesting from whether the perception backend emitted a useful candidate.
Detector confidence is backend evidence; it is neither an annotation field
nor ground truth.

Copy `benchmarks/review-annotations/template.json`, fill it without modifying
the template, then validate the copy:

```sh
python3 scripts/validate_review_annotations.py REVIEW.json
```

The blank template is deliberately invalid until a privacy-safe reviewer ID,
review date, and source ID are supplied. No annotation or result is implied.

## Frame review

Each timestamp records ordinal `ordinaryViewerInterest` from 0 (none) through
3 (high), controlled `eventLabels`, every emitted candidate as `hit`,
`false_positive`, or `uncertain`, cross-viewport duplicate groups, and
important regions missed by all candidates as spherical direction/extent.

`reviewable=false` is for corrupt, obscured, or otherwise unjudgeable evidence
and requires interest 0 with no event labels. Candidate and missed-region
arrays remain explicit rather than being inferred from interest.

## Privacy and limitations

Use pseudonymous reviewer IDs and privacy-safe source/candidate IDs. The
schema has no absolute-path, person-name, face-identity, free-text subject
description, image, audio, or biometric field.

Schema v1 requires `interRaterStatus: not_performed` and the limitation
`inter-rater agreement has not been measured`. A second-reviewer protocol,
agreement statistic, adjudication process, sampling acceptance threshold, and
completed benchmark annotations do not yet exist.

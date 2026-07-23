# 0002: Deliver Full Story before Highlights

Status: Accepted

## Context

Automatic viewpoint choice and aggressive temporal editing fail in different
ways. Combining them in the first proof makes it difficult to tell whether the
system looked in the wrong direction or removed valuable content. Low motion
also does not imply low editorial value.

## Decision

The first required POC mode is **Full Story**: preserve chronology and most of
the source duration while choosing viewpoints automatically. **Highlights**,
including aggressive removal of uneventful or repetitive footage, follows
after Full Story is credible.

The analysis pass must nevertheless retain explainable interest, novelty, and
event evidence so Highlights can reuse it later.

## Consequences

- Dead-air removal is not a first-gate acceptance requirement.
- No heuristic may define dead air solely as static or low-motion footage.
- Full Story and Highlights will use separate quality criteria even when they
  share perception and scoring artifacts.
- Time selection can be added without rerunning expensive perception if the
  cached evidence is adequate.

# 0011: Fail closed on chapter-aware foreshadow

Status: Accepted

## Context

Showing a destination before the journey can create a useful promise: briefly
show where the rider will arrive, return to the forest journey, then pay off
the promise when the rider reaches that place. The same edit becomes confusing
when chapter boundaries are wrong or the viewer cannot tell that the opening
image is a preview rather than the next chronological event.

ADR 0002 makes chronological Full Story the first acceptance mode. Aesthetic
preference alone is not enough to weaken that safety property.

## Decision

Full Story remains chronological by default. A foreshadow is one optional
prefix excerpt copied from a later chapter, followed immediately by the full
chronological body. The later occurrence remains in place as the payoff; the
planner may not relocate or remove it. At most one such prefix is allowed.

A planner may use that bounded prefix only when an independently validated
whole-film chapter map proves all of the following:

- the source is partitioned into ordered, non-overlapping chapters covering
  the complete selected story window;
- the future excerpt belongs to a later chapter with an explicit start and
  end, and its later chronological occurrence is retained as the payoff;
- the return point belongs to the opening chronological chapter;
- every boundary involved in the excursion is observed rather than inferred
  from an absent or abstained label;
- the foreshadow is represented explicitly in the decision trace, including
  source interval, destination chapter, return point and reason;
- the renderer can replay the trace deterministically without changing the
  underlying chapter order after the return.

The chapter map must also account explicitly for every retained scene-change
candidate, including candidates not promoted to chapter boundaries. Its
chapters must be positive-duration, ordered, gap-free, non-overlapping and
cover the complete selected story window. Model-reported confidence alone is
not evidence that this accounting is reliable.

If any condition is missing, contradictory or unverified, the planner must
preserve chronology. A scene-change candidate, isolated semantic label, or
locally plausible view is not a complete chapter map and cannot authorize
temporal reordering.

## Consequences

- The current five agent-authored story labels do not authorize foreshadow.
- The next evidence milestone is a complete chapter-map artifact and a
  fail-closed authorization gate, not an immediate waterfall cold-open render.
- An authorized trace has exactly one source-time exception at its prefix;
  the body remains monotonic and retains complete Full Story coverage.
- Chapter confidence must be established at the chapter-map boundary; the
  temporal planner must not invent confidence from view relevance or motion.
- Foreshadow is a disclosed narrative operation, not a general license for
  montage, arbitrary flash-forwards or a scrambled Full Story timeline.
- Highlights may later adopt broader reordering rules under a separate ADR.

# Decision trace

Status: Draft schema requirements

## Purpose

The trace makes plans reproducible and editorial choices inspectable without
embedding source frames or personal data. JSON is the initial interchange
format; a formal schema is added with the first executable producer.

## Required sections

- `schema_version`, tool revision and creation time;
- privacy-safe source identifier and media metadata, never an absolute path;
- projection/coordinate convention and explicit overrides;
- model/backend identifiers and weight checksums;
- analysis and planner configuration;
- candidate timestamps, directions/FOV, type and stable ephemeral IDs;
- named interest evidence with raw/normalized values and provenance;
- transition costs and constraints;
- selected candidate/path, cuts and rejected alternatives/reasons;
- warnings, fallbacks and missing evidence;
- aggregate objective/quality metrics and artifact-relative references.

## Privacy and determinism

Do not include frames, audio, names, face crops/embeddings, GPS, IMU payloads,
raw transcripts or source absolute paths. IDs are scoped to the job and cannot
be used as durable person identifiers. Stable key ordering and finite numeric
values are required; NaN/Inf is invalid.

## Acceptance criteria

A trace must reconstruct the selected proxy camera path without rerunning
perception, explain every switch/cut, identify all inputs/configuration needed
to reproduce the plan, and pass schema/privacy validation.

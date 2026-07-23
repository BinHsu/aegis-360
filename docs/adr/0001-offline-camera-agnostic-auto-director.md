# 0001: Build an offline, camera-agnostic auto-director

Status: Accepted

## Context

Subject tracking alone asks a user to decide whom to follow. The project aims
at the higher-level editorial problem: infer what an ordinary viewer is likely
to find interesting, choose among people, objects, action, travel direction,
groups, and context, and direct a virtual camera without a selected subject.

## Decision

Build a fully offline auto-director for standard 360 video. Runtime analysis
and rendering require no network, account, login, cloud processing, or
telemetry. The core workflow is independent of camera brand and operates on an
open, normalized spherical input boundary defined by ADR 0003.

The POC optimizes for a broadly understandable ordinary-viewer editorial
policy rather than a single activity-specific policy. Tracking is supporting
evidence, not the product definition.

## Consequences

- Candidate views may represent a person, object, interaction, group,
  forward/travel direction, or environment.
- Setup and explicit asset/model acquisition may use the network, but runtime
  must never download anything silently.
- Project claims must distinguish detection, tracking, subject selection,
  auto-directing, and temporal editing.
- General-interest directing requires diverse benchmarks and permits multiple
  reasonable viewpoints rather than one universal ground truth.

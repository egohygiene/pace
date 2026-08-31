---
schema: aether.architecture-document/v1
id: pace-architecture
title: Pace Architecture
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-31
governed_by:
  - architecture-architecture
depends_on:
  - pace-foundations
  - pace-system
related:
  - pace-purpose
  - pace-vision
  - pace-principles
  - pace-pillars
supersedes: []
---

# Pace Architecture

## Purpose and scope

Pace uses a layered, contract-driven architecture. This document owns structural boundaries, dependency direction, integration rules, and current-to-target evolution. Logical responsibilities remain canonical in [SYSTEM.md](SYSTEM.md).

## Layer model

1. **Intent and contracts** — identity, policy, specifications, schemas, and accepted decisions.
2. **Domain** — canonical concepts and pure domain behavior.
3. **Application** — planning, orchestration, use cases, and state transitions.
4. **Adapters** — filesystems, providers, frameworks, renderers, and external tools.
5. **Interfaces** — CLI, library, site, reports, generated artifacts, and automation contracts.
6. **Evidence** — tests, diagnostics, provenance, manifests, and health projections.

Dependencies point inward toward stable contracts and domain behavior. External details do not become canonical domain truth.

## Structural view

```mermaid
flowchart LR
  S1[Repository inventory reader]
  S2[Desired-state resolver]
  S3[Drift engine]
  S4[Reconciliation planner]
  S5[Change applier]
  S6[Override registry]
  S7[Reporting adapter]
  S1 --> S2
  S2 --> S3
  S3 --> S4
  S4 --> S5
  S5 --> S6
  S6 --> S7
```

The diagram is conceptual. [SYSTEM.md](SYSTEM.md) remains authoritative for responsibilities and implementation evidence determines current availability.

## Implemented lock-validation slice

```text
schemas/pace-lock-v1.schema.json  # closed desired-state contract
examples/pace.lock.json           # six-kind conformance example
scripts/validate_lock.py          # offline independent validator
tests/test_validate_lock.py       # adversarial contract evidence
.github/workflows/validate.yml    # least-privilege validation gate
```

The validator is deliberately independent from future source resolvers and
updaters. It reads one lock, validates immutable provenance, ownership,
compatibility, rollback, and exception time bounds, and emits evidence without
network or write capabilities.

## Implemented repository-presentation planning slice

```text
examples/repository-presentation.inventory.json  # privacy-safe observed fleet snapshot
schemas/repository-presentation-*-v1.schema.json  # inventory, plan, review, proposal contracts
scripts/plan_repository_presentation.py           # deterministic no-write planner and review gate
tests/test_repository_presentation_rollout.py     # privacy, integrity, and authority evidence
docs/repository-presentation-rollout.md           # operator workflow and rollback boundary
```

The planner is a pure adapter over checked observed state. It has no GitHub
client, credential input, consumer filesystem access, or pull-request write
port. Its proposal output binds one repository, represented commit, README blob,
Egolint report, reviewed plan, immutable contract set, and rollback snapshot.
An external authorized operator may consume that artifact only after the review
boundary; application remains outside this slice.

## Dependency rules

- Sibling domain capabilities integrate through versioned public contracts, not direct access to internals.
- Generated artifacts never become the canonical source unless an accepted decision explicitly changes ownership.
- Provider and platform adapters depend on application ports; core behavior does not depend on a provider implementation.
- Read, plan, apply, verify, publish, and recover remain separate authority boundaries when consequential.
- Cross-repository references use releases, immutable commits, schemas, packages, or documented APIs rather than mutable default-branch assumptions.

## Ecosystem interfaces

- Hygiene rules
- Empathy templates
- Holon manifests
- Aether bundles
- Relay automation
- Observatory health

## Deployment and portability

The architecture favors independently usable local and self-hosted operation. Optional managed services may add availability, collaboration, support, and hosted infrastructure without becoming the canonical holder of portable state.

## Evidence and uncertainty

- **Observed:** Pace owns a versioned dependency-lock validator plus a bounded
  repository-presentation inventory, deterministic drift/plan projection,
  exact review authorization, credential-free single-repository proposal,
  adversarial tests, and least-privilege CI gate. General update resolution and
  every consumer write/application path remain unimplemented.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

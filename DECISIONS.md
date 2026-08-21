---
schema: aether.architecture-document/v1
id: pace-decisions
title: Pace Decisions
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-21
governed_by:
  - architecture-decisions
depends_on:
  - pace-principles
  - pace-epistemology
  - pace-foundations
  - pace-system
  - pace-architecture
related:
  - pace-purpose
  - pace-vision
  - pace-pillars
  - pace-manifesto
supersedes: []
---

# Pace Decisions

## Purpose

This document preserves significant accepted architectural choices and their rationale. Issues coordinate work, proposals explore alternatives, and this file records decisions that constrain future implementation.

## Governance

Do not rewrite historical context to fit current understanding. Amend a record for corrections that do not change meaning; supersede it with a new record when the decision changes materially.

## Index

- ADR-001: Separate detection, planning, and application
- ADR-002: Preserve repository-local overrides as first-class records
- ADR-003: Require reviewable changes for synchronization
- ADR-004: Make desired-state locks independently verifiable

## ADR-001: Separate detection, planning, and application

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Separate detection, planning, and application.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-002: Preserve repository-local overrides as first-class records

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Preserve repository-local overrides as first-class records.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-003: Require reviewable changes for synchronization

- **Status:** Accepted as the current architectural direction
- **Date:** 2026-08-19
- **Context:** Repository evidence and ecosystem ownership require an explicit durable boundary.
- **Decision:** Require reviewable changes for synchronization.
- **Consequences:** The choice improves ownership and predictability while requiring maintained contracts, validation, and migration discipline.
- **Reconsider when:** New evidence shows that the boundary prevents standalone usefulness, safety, portability, or maintainability.

## ADR-004: Make desired-state locks independently verifiable

- **Status:** Accepted for the v1 lock contract
- **Date:** 2026-08-21
- **Context:** A synchronization tool cannot be the sole authority asserting that its own update output is safe. Repositories need a portable record of source identity, content integrity, generated ownership, compatibility, rollback, and temporary exceptions before any updater receives write authority.
- **Decision:** Define a closed JSON lock contract covering foundation, Aether, workflow, container, site, and schema dependencies. Require immutable references and SHA-256 digests. Validate the lock with a standard-library-only tool that has no network, updater, or write capability. Treat exceptions as approved records with bounded expiry, never as integrity bypasses.
- **Consequences:** Desired state is reviewable and independently testable before drift or apply exists. The lock duplicates some upstream metadata, and later resolvers must prove that fetched bytes match it. Contract-breaking changes require a new lock schema major and migration.
- **Reconsider when:** A portable signed manifest standard can express the same repository ownership, compatibility, rollback, and exception semantics without weakening offline validation.

## Open decisions

- Signing and transparency policy for future resolved locks and update plans.
- Exact self-hosted, managed, and organization-integrated deployment boundaries.
- Which target systems must exist before the architecture status may become active.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

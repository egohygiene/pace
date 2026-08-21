---
schema: aether.architecture-document/v1
id: pace-system
title: Pace System
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-21
governed_by:
  - architecture-system
depends_on:
  - pace-foundations
  - pace-ontology
related:
  - pace-purpose
  - pace-vision
  - pace-principles
  - pace-pillars
supersedes: []
---

# Pace System

## Purpose and scope

This document identifies Pace's logical systems and responsibilities. It answers what the major systems do; [ARCHITECTURE.md](ARCHITECTURE.md) owns their structural organization and dependency rules.

## System inventory

| System | State | Responsibility |
| --- | --- | --- |
| Desired-state lock contract | Active | Records immutable source identity, content digest, target ownership, compatibility, rollback, and bounded exceptions for six dependency kinds. |
| Independent lock validator | Active | Validates lock structure and semantics offline without trusting an updater or receiving write authority. |
| Repository inventory reader | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Desired-state resolver | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Drift engine | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Reconciliation planner | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Change applier | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Override registry | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |
| Reporting adapter | Target | Owns its bounded portion of the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; exposes explicit inputs, outputs, failure states, and evidence. |

## External systems

- Hygiene rules
- Empathy templates
- Holon manifests
- Aether bundles
- Relay automation
- Observatory health

External systems are integrations, not hidden implementation units. Each requires version, authentication, availability, data, error, and replacement boundaries appropriate to its risk.

## System interactions

Inputs enter through an adapter or validated contract, move through domain systems, produce artifacts and diagnostics, and leave through a stable interface. Evidence flows back to validation, review, and future decisions.

## Failure model

Systems fail closed at destructive, publication, privacy, and security boundaries. Partial results identify coverage and remain distinguishable from complete success.

## Evidence and uncertainty

- **Observed:** Desired-state lock validation is active. Repository inventory,
  drift, planning, application, override storage, and reporting remain target
  systems.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

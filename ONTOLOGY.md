---
schema: aether.architecture-document/v1
id: pace-ontology
title: Pace Ontology
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-19
governed_by:
  - architecture-ontology
depends_on:
  - pace-purpose
  - pace-vision
  - pace-principles
  - pace-epistemology
related:
  - pace-pillars
  - pace-manifesto
  - pace-ai-constitution
  - pace-personal-model
supersedes: []
---

# Pace Ontology

## Domain scope

Pace models the concepts needed for help repositories adopt and remain aligned with shared contracts without destroying intentional local extensions. The ontology names conceptual entities and relationships; it is not a source-code class model, API schema, or database design.

## Canonical concepts

| Concept | Meaning |
| --- | --- |
| Desired state | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Observed state | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Drift | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Adoption | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Reconciliation plan | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Override | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Provenance | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Conformance result | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |
| Change set | A canonical concept in the Pace domain whose exact fields belong to specifications or schemas, not this ontology. |

## Core relationships

- A repository or person provides source context to one or more domain artifacts.
- A specification constrains how an artifact is interpreted or produced.
- A plan separates proposed action from execution.
- Evidence supports a claim; a decision authorizes a durable direction.
- Provenance connects derived artifacts to their inputs and processing context.
- A consumer integrates through an explicit interface rather than internal structure.

## Boundaries

- Conceptual identity is distinct from filesystem path, database identifier, or display label.
- Observed state is distinct from desired state.
- Proposed relationships are not accepted facts.
- Neighboring repositories retain ownership of their domain concepts.

## Evidence and uncertainty

- **Observed:** The repository README establishes the intended boundary as the repository adoption, reconciliation, synchronization, and conformance mechanism for the Ego Hygiene organization; significant implementation remains incomplete.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

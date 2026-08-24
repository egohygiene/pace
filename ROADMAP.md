---
schema: aether.architecture-document/v1
id: pace-roadmap
title: Pace Roadmap
kind: architecture-document
version: 0.1.0
status: provisional
owners:
  - egohygiene
created: 2026-08-19
updated: 2026-08-24
governed_by:
  - architecture-roadmap
depends_on:
  - pace-vision
  - pace-pillars
  - pace-architecture
  - pace-decisions
related:
  - pace-purpose
  - pace-principles
  - pace-manifesto
  - pace-epistemology
supersedes: []
---

# Pace Roadmap

<!-- BEGIN ROADMAP EXECUTION SNAPSHOT -->
<!-- roadmap-manifest
schema: hygiene.roadmap/v1alpha1
repository: egohygiene/pace
visibility: public
publication: central
route: /roadmap/pace/
updated: 2026-08-24
-->
## 2026-08-24 execution snapshot

> This evidence-reconciled snapshot is the issue-generation and visual-roadmap handoff. The longer-horizon strategy below remains canonical context; generated HTML, JSON, progress, issue plans, and commit lists are projections.

**Lifecycle:** seed implementation  
**Current gate:** Add observed-state capture and a drift report before attempting the reviewable convergence plan tracked by issue #2.  
**North-star outcome:** Reviewable fleet convergence from declared desired state, observed state, and explicit drift.

### Visual roadmap publication

**Mode:** `central`  
**Route:** `/roadmap/pace/`  
**Current publication evidence:** GitHub source and CI only; no Pages or release publication observed.

Publish the public-safe projection through egohygiene.io at /roadmap/pace/. This repository owns intent and acceptance evidence; it does not add a second site deployment.

### Quest line

<!-- roadmap-step
id: PAC-Q01
status: complete
depends_on: []
issues: []
-->
#### PAC-Q01 — Lock desired state

**State:** `complete`  
**Depends on:** None

**Outcome:** Desired fleet state is represented by a deterministic lock artifact.

**Exit criteria:**

- [x] The lock is reproducible.
- [x] Validation runs green in CI.

**Current evidence:**

- PR #4 merged at 99d479445406.
- Desired-state lock validation was observed green.

<!-- roadmap-step
id: PAC-Q02
status: active
depends_on: [PAC-Q01]
issues: []
-->
#### PAC-Q02 — Capture observed state

**State:** `active`  
**Depends on:** `PAC-Q01`

**Outcome:** Pace can record what is actually deployed without mutating it.

**Exit criteria:**

- [ ] An observed-state schema and collector are implemented.
- [ ] Fixtures prove stable normalization of at least one representative fleet.

**Current evidence:**

- No observed-state implementation was found.

<!-- roadmap-step
id: PAC-Q03
status: planned
depends_on: [PAC-Q02]
issues: []
-->
#### PAC-Q03 — Render actionable drift

**State:** `planned`  
**Depends on:** `PAC-Q02`

**Outcome:** Desired and observed states produce a deterministic, human-reviewable drift report.

**Exit criteria:**

- [ ] Additions, removals, and changes are distinguished.
- [ ] Repeated runs on unchanged input are identical.

**Current evidence:**

- No drift engine or report was observed.

<!-- roadmap-step
id: PAC-Q04
status: planned
depends_on: [PAC-Q03]
issues: [2]
-->
#### PAC-Q04 — Create a reviewable convergence plan

**State:** `planned`  
**Depends on:** `PAC-Q03`

**Outcome:** Issue #2 yields an ordered plan with explicit risk, ownership, and rollback information.

**Exit criteria:**

- [ ] The plan is generated without applying changes.
- [ ] Each action links to the drift that caused it.

**Current evidence:**

- Issue #2 is the identified next planning gate.

<!-- roadmap-step
id: PAC-Q05
status: planned
depends_on: [PAC-Q04]
issues: []
-->
#### PAC-Q05 — Prove a no-write fleet pilot

**State:** `planned`  
**Depends on:** `PAC-Q04`

**Outcome:** A representative repository fleet can be assessed safely before rollout automation is considered.

**Exit criteria:**

- [ ] The pilot runs with read-only credentials.
- [ ] Operators approve the generated plan and documented rollback boundary.

**Current evidence:**

- No observed-state, drift, or fleet pilot evidence was found.

<!-- roadmap-step
id: PAC-Q06
status: planned
depends_on: [PAC-Q05, REL-Q05]
issues: []
-->
#### PAC-Q06 — Roll out roadmap adoption safely

**State:** `planned`  
**Depends on:** `PAC-Q05`, `REL-Q05`

**Outcome:** Pace detects stale roadmap adoption and proposes one bounded, reviewable repository update at a time.

**Exit criteria:**

- [ ] Dry-run drift covers contract, renderer, workflow, route, and publication-mode versions.
- [ ] Write authority is separately approved and every proposal has a rollback path.

**Current evidence:**

- Only the desired-state lock is implemented today; fleet rollout remains unproven.

### Roadmap-to-issue handoff

- A step is complete only when its exit criteria and required evidence are satisfied; commit count never determines progress.
- Ready or planned steps without an issue are candidates for the private, duplicate-aware roadmap.issue-plan.json dry run.
- Issue creation or reconciliation requires human approval or an explicitly authorized Pace operation and returns issue references through a reviewable roadmap pull request.
- Pull requests and commits should include Roadmap-Step: <ID>; historical evidence may be linked through existing issue and pull-request relationships.
- Public rendering uses only allowlisted build-time evidence and never places a GitHub token or private issue plan in the browser artifact.

<!-- END ROADMAP EXECUTION SNAPSHOT -->

## Strategic context

This roadmap describes capability evolution, not promised dates or an issue queue. Sequence follows architecture dependencies and may change when evidence or risk changes.

## Phase 1: Define desired and observed state schemas

**Status:** Desired dependency lock v1 is implemented and independently
validated. Observed-state and drift schemas remain planned for Phase 2.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 2: Implement read-only drift

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 3: Generate reviewable reconciliation plans

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 4: Apply bounded changes

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 5: Operate organization-wide synchronization

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Cross-cutting tracks

- Security, privacy, accessibility, licensing, and provenance.
- Documentation, architecture portals, examples, and onboarding.
- Packaging, release, compatibility, and self-hosting.
- Organization integration through explicit contracts.
- Observatory evidence and Pace conformance when those systems exist.

## Deferred direction

Optional managed services, enterprise controls, marketplaces, and the conversational organization compiler remain later architecture work. Current choices should preserve portability and avoid foreclosing them.

## Evidence and uncertainty

- **Observed:** Pace owns `egohygiene.pace.lock/v1`, an offline validator,
  adversarial exception and provenance tests, a six-kind example, and a CI gate.
  No updater or repository mutation path exists.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

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
updated: 2026-09-02
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
**Current gate:** Review PAC-02's general convergence contracts and bounded PR adapter, while issue #14 separately unblocks its three presentation canaries.

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
status: complete
depends_on: [PAC-Q01]
issues: []
-->
#### PAC-Q02 — Capture observed state

**State:** `complete`

**Depends on:** `PAC-Q01`

**Outcome:** Pace can record what is actually deployed without mutating it.

**Exit criteria:**

- [x] Pace consumes Observatory's pinned organization-health schema instead of adding a second collector.
- [x] Fixtures prove stable ingestion of represented fleet state and block stale or ambiguous evidence.

**Current evidence:**

- Observatory PR #15 provides the read-only organization-health contract.
- Pace pins that contract and binds the exact catalog bytes, snapshot ID, freshness, and represented commit into every plan.

<!-- roadmap-step
id: PAC-Q03
status: complete
depends_on: [PAC-Q02]
issues: []
-->
#### PAC-Q03 — Render actionable drift

**State:** `complete`

**Depends on:** `PAC-Q02`

**Outcome:** Desired and observed states produce a deterministic, human-reviewable drift report.

**Exit criteria:**

- [x] Additions, removals, and changes are distinguished.
- [x] Repeated runs on unchanged input are identical.

**Current evidence:**

- PAC-02 compares complete current and desired Pace lock entries and explains categorical risk.
- The canonical plan digest binds inputs, dependency order, drift, risk, blockers, and rollback state.

<!-- roadmap-step
id: PAC-Q04
status: complete
depends_on: [PAC-Q03]
issues: [2]
-->
#### PAC-Q04 — Create a reviewable convergence plan

**State:** `complete`

**Depends on:** `PAC-Q03`

**Outcome:** Issue #2 yields an ordered plan with explicit risk, ownership, and rollback information.

**Exit criteria:**

- [x] The plan is generated without applying changes.
- [x] Each action links to the drift that caused it.

**Current evidence:**

- PAC-02 emits topologically ordered repository units with full before/after lock entries, risk reasons, exact review records, and partial-fleet selection.
- One reviewed unit can verify one bounded candidate and open one non-default-branch PR; merge remains human-owned.

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

- A 29-repository public-safe snapshot and Mantle/Identity/Antidote canary wave now exist.
- Every canary is honestly blocked on Identity artifacts, reviewed facts, and pinned Egolint evidence; operator approval and consumer writes remain pending.

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
- Ready steps without an issue are candidates for the private, duplicate-aware roadmap.issue-plan.json dry run. Planned steps remain preview-only unless a reviewer explicitly opts them in with issue_policy: propose.
- Issue creation or reconciliation requires human approval or an explicitly authorized Pace operation and returns issue references through a reviewable roadmap pull request.
- Pull requests and commits should include Roadmap-Step: <ID>; historical evidence may be linked through existing issue and pull-request relationships.
- Public rendering uses only allowlisted build-time evidence and never places a GitHub token or private issue plan in the browser artifact.

<!-- END ROADMAP EXECUTION SNAPSHOT -->

## Strategic context

This roadmap describes capability evolution, not promised dates or an issue queue. Sequence follows architecture dependencies and may change when evidence or risk changes.

## Phase 1: Define desired and observed state schemas

**Status:** Desired dependency lock v1 and pinned Observatory ingestion are
implemented and independently validated.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 2: Implement read-only drift

**Status:** Implemented for current and desired Pace locks with explainable risk
and fail-closed Observatory freshness.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 3: Generate reviewable reconciliation plans

**Status:** Implemented with deterministic dependency order, exact-digest
reviews, blockers, pause state, and partial-fleet approval.

**Outcome:** A bounded capability advances from documented intent to validated, independently usable behavior.

**Exit signals:**

- The owning contract and acceptance criteria are versioned.
- Implementation and documentation agree.
- Relevant tests and safety checks pass.
- Downstream consumers and migration impact are understood.
- Remaining uncertainty is visible.

## Phase 4: Apply bounded changes

**Status:** Implemented only for one exact candidate tree and one pull request.
Default-branch writes, force, and merge remain unavailable.

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
  general fleet convergence contracts, exact review and rollback anchors, a
  bounded one-PR adapter, and a specialized repository-presentation planner.
  No default-branch or merge mutation path exists.
- **Decided for this draft:** The repository owns the bounded concern described here and participates through versioned contracts.
- **Proposed:** Target systems and later roadmap phases remain proposals until accepted and implemented.
- **Open question:** Which parts of this draft should become active in the first independently versioned release?

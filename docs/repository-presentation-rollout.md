# Repository-presentation fleet rollout

Pace reconciles repository presentation in two distinct authority phases:

1. read-only inventory, deterministic planning, and human review;
2. one credential-free proposal per repository, followed by separately authorized
   pull-request creation.

The planner never edits a consumer repository or calls GitHub. A generated
proposal is an integrity-bound handoff to an authorized operator, not a fleet
write.

## Immutable contract set

| Owner | Version | Revision |
| --- | --- | --- |
| Hygiene repository-presentation profile | 1.0.0-alpha.1 (proposed) | `cb2ed63425d29abada2d2bbb43a3b3e59d11aeb8` |
| Identity presentation package | 1.0.0 | `3c2fd3141371b355628e81f66f63159f19d63338` |
| Holon presentation blueprint | 1.0.0 | `4d436b631ea82c463d3a6a04b5664633f3c64b4c` |
| Egolint presentation validator | 0.1.0-alpha.1 | `4efe92a2609b3384fcf3b5cda343a4f64d108824` |

The Hygiene profile remains proposed. Inventory or rollout does not activate it
and cannot manufacture a passing evidence state.

## Reviewed fleet snapshot

`examples/repository-presentation.inventory.json` records every repository
visible to the linked organization installation on 2026-08-31. Every entry is
explicitly `eligible`, `deferred`, `exempt`, `blocked`, or
`not_applicable`.

The public artifact contains no private README digest, represented commit, facts,
or exception prose. The private repository is deferred to a separately
authorized private plan.

The first canary wave is:

| Role | Repository | Why |
| --- | --- | --- |
| Small tool | `egohygiene/mantle` | Exercises the CLI profile and preserves a substantial existing README. |
| Customized | `egohygiene/identity` | Exercises a deeply customized source repository and visual ownership boundary. |
| Publication/product | `egohygiene/antidote` | Exercises publication semantics and an incubating product/research surface. |

The observed canaries are currently blocked. They lack a complete consumer-local
Identity package, reviewed repository fact source, and current pinned Egolint
report. This is actionable drift, not a template placeholder and not a rollout
failure.

## Generate the exact dry-run plan

Validate the checked inventory:

    python3 scripts/plan_repository_presentation.py validate-inventory \
      --inventory "examples/repository-presentation.inventory.json"

Generate a deterministic plan without credentials or consumer writes:

    python3 scripts/plan_repository_presentation.py plan \
      --inventory "examples/repository-presentation.inventory.json" \
      --output "/tmp/repository-presentation.plan.json"

Verify it independently:

    python3 scripts/plan_repository_presentation.py verify-plan \
      --plan "/tmp/repository-presentation.plan.json"

The plan reports each repository's declared state, blockers, drift, represented
commit, Egolint state, rollback binding, wave, and privacy-safe Observatory
projection. Repeated runs over identical inventory bytes produce the same
inventory and plan digests.

## Unblock one repository

A repository becomes eligible only after all of the following are observed at
one represented commit:

- a consumer-local, immutable Identity package and manifest;
- complete, reviewed repository-owned presentation facts;
- an exact README Git blob identity;
- a valid report from the pinned Egolint revision; and
- no unresolved profile or merge blocker.

Holon must then create the exact preview plan. Pace records its checksum and
never asks Holon to force an overwrite. Existing authored README prose remains
outside Holon's checksum-bound managed region.

Update the inventory in a new reviewable Pace pull request. The changed
represented commit supersedes every earlier plan and proposal.

## Review authorization and proposal

Plan review is an explicit document, not an implicit CLI flag:

    {
      "schema": "egohygiene.pace.repository-presentation-review/v1",
      "planDigest": "<exact reviewed plan digest>",
      "reviewer": "szmyty",
      "reviewedAt": "2026-08-31T16:00:00Z",
      "decision": "approved"
    }

Only then can Pace produce a proposal:

    python3 scripts/plan_repository_presentation.py propose \
      --plan "/tmp/repository-presentation.plan.json" \
      --review "/tmp/repository-presentation.review.json" \
      --repository "egohygiene/mantle" \
      --output "/tmp/mantle.repository-presentation.proposal.json"

Proposal creation fails closed when the review digest, inventory, represented
commit, Identity package, facts, README blob, or Egolint evidence is missing or
stale. The proposal contains no token and grants no GitHub authority.

An authorized operator may turn one proposal into one small pull request. Canary
repositories are proposed independently; no all-or-nothing fleet branch exists.

## Verification after merge

A consumer adoption is not complete until its merged represented commit records:

- consumer CI success;
- Holon render verification;
- the pinned Egolint report;
- local banner and badge file integrity;
- alt and fallback text;
- local and canonical links;
- badge evidence destination and represented commit; and
- a fresh inventory observation showing no managed-region drift.

Observatory receives only adoption state, profile, freshness, drift categories,
and bounded exception metadata. Pace deliberately emits `healthScore: null`;
presentation polish is not a universal health score.

## Retry, supersession, and rollback

A proposal ID binds repository and represented commit, so retrying unchanged
input is idempotent. A new represented commit or inventory creates new digests
and supersedes the proposal.

Each proposal records the previous README Git blob and represented commit.
Rollback restores the reviewed README and Holon state together. Holon refuses
rollback after unreviewed README drift; Pace must then create a new observation
and plan rather than force replacement.

Deferred, exempt, private, archived, and not-applicable repositories remain
visible in later inventories. Archived repositories are never reopened solely
for visual consistency.

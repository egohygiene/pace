# Reviewed fleet convergence

Pace turns declared fleet intent and observed repository state into one bounded,
reviewable upgrade pull request at a time. Planning is offline and has no
credential input. GitHub access is available only in the final `open-pr`
command, after an exact plan and one unit have been approved.

## Contract ownership

| Input | Owner | Pace use |
| --- | --- | --- |
| Repository catalog v1 | Hygiene | Defines current fleet membership, lifecycle, maturity, and visibility. |
| Foundation manifest v1 | Holon | Defines repository class, capabilities, and immutable foundation intent. |
| Pace lock v1 | Pace | Defines current and desired immutable sources, target ownership, compatibility, exceptions, and rollback. |
| Organization-health v1 | Observatory | Supplies the current, freshness-qualified represented commit. |
| Materialization plan v1 | Holon | Authorizes exact generated-target operations when lock drift touches generated paths. |

The exact upstream schema revisions are recorded in `contracts/`. Pace does not
scan repositories, reinterpret Observatory checks, resolve Holon capabilities,
or render generated files.

## Fleet manifest

`egohygiene.pace.fleet-convergence-manifest/v1` joins those inputs without
copying them. Paths are normalized, relative to the fleet manifest, and cannot
escape its directory. Each repository declares:

- one Holon foundation manifest;
- an optional current Pace lock and one adoptable desired Pace lock;
- an optional exact Holon materialization plan;
- the consumer-local lock path and default branch;
- explicit repository-unit dependencies; and
- an `active` or `paused` state.

Dependencies must be managed by the same manifest and form an acyclic graph.
Repositories are topologically ordered with lexical tie-breaking. Repositories
in the Hygiene catalog but outside this manifest remain visible as unmanaged;
that is deliberate partial-fleet adoption, not implicit success.

## Generate a no-write plan

The checked example is a contract fixture, not a live consumer:

```bash
python3 scripts/plan_fleet_convergence.py plan \
  --manifest "examples/convergence/fleet.manifest.json" \
  --catalog "examples/convergence/catalog.json" \
  --observatory "examples/convergence/observatory.snapshot.json" \
  --output "/tmp/fleet-convergence.plan.json"

python3 scripts/plan_fleet_convergence.py verify-plan \
  --plan "/tmp/fleet-convergence.plan.json"
```

The planner requires the Observatory snapshot to bind the exact supplied
catalog bytes. A repository is blocked if Observatory evidence is stale,
unknown, mixed, or represents anything other than one full commit SHA. Pace
never substitutes the current branch head for missing observation.

Each repository is one bounded unit with one of four dispositions:

| Disposition | Meaning |
| --- | --- |
| `ready_for_review` | Drift exists, observation is current, locks are valid, and generated changes have exact Holon coverage. |
| `blocked` | A contract, freshness, ownership, or materialization precondition is missing. |
| `paused` | The manifest explicitly holds the unit; regenerating creates a superseding plan digest. |
| `no_change` | Current and desired locks are identical. |

Changes distinguish additions, removals, and updates and retain complete before
and after lock entries. Risk is explainable: removals, target ownership/path
changes, and compatibility-contract changes are high risk; new adoption,
provenance changes, migration/rollback changes, and exception changes are at
least medium risk. All other metadata-only changes are low risk.

The plan embeds every input needed to verify its drift again. Its
`plan_digest` binds the canonical plan, unit ordering, source digests, current
and desired locks, Holon operations, blockers, and risk.

## Review and partial adoption

Review is a separate document. `approved_units` may be a strict subset of the
plan; `completed_units` records dependency units already adopted:

```json
{
  "schema": "egohygiene.pace.fleet-convergence-review/v1",
  "plan_digest": "<exact plan digest>",
  "reviewer": "reviewer-name",
  "reviewed_at": "2026-09-02T13:00:00Z",
  "decision": "approved",
  "approved_units": ["upgrade:egohygiene/example-tool:<digest>"],
  "completed_units": []
}
```

Pace refuses an unapproved, blocked, paused, dependency-incomplete, unknown, or
tampered unit. Produce exactly one pull-request proposal:

```bash
python3 scripts/plan_fleet_convergence.py propose \
  --plan "/tmp/fleet-convergence.plan.json" \
  --review "/tmp/fleet-convergence.review.json" \
  --unit "upgrade:egohygiene/example-tool:<digest>" \
  --output "/tmp/example-tool.pull-request.json"
```

The proposal embeds the desired lock, rollback anchor, exact base commit,
deterministic branch, PR text, and a closed candidate-path allowlist. It carries
no credential.

## Prepare and open one pull request

Prepare a local checkout at the proposal's exact `base_commit`. Write the
desired lock to `lock_path`. If generated targets change, run Holon's `render`
with the exact plan embedded in the proposal; Pace requires every mutating
Holon operation to correspond to a changed generated lock target.

Then use a fine-grained token with contents and pull-request write access to
that consumer only:

```bash
GITHUB_TOKEN="<short-lived token>" \
python3 scripts/plan_fleet_convergence.py open-pr \
  --proposal "/tmp/example-tool.pull-request.json" \
  --candidate "/path/to/example-tool" \
  --output "/tmp/example-tool.pull-request-result.json"
```

Before any write, Pace verifies:

1. the proposal's internal digest and embedded review;
2. the candidate worktree is exactly at the reviewed commit;
3. every changed path is allowlisted and every required path changed;
4. the lock equals the reviewed desired lock;
5. generated bytes and Holon state match the reviewed Holon plan; and
6. the remote default branch still equals the represented commit.

The adapter creates blobs, one tree, one commit, one non-default branch, and one
pull request. It never updates the default-branch ref. A retry reuses the same
branch and PR only when the remote candidate tree is identical; a different
tree or an advanced base is refused and requires fresh observation and a new
plan.

## Pause, retry, rollback, and recovery

- **Pause:** set the unit to `paused` and regenerate. The new plan digest
  supersedes any earlier unexecuted review.
- **Retry:** reuse the unchanged proposal. Branch/tree equality makes retries
  idempotent and prevents silent replacement.
- **Partial adoption:** approve only selected units. A dependent unit is not
  proposed until its unit IDs appear in `completed_units`.
- **Rollback:** the proposal retains the full prior lock and Holon's plan ID and
  prior generated digests. After a failed merge, collect a fresh Observatory
  snapshot, make that prior lock the desired lock, use Holon's fail-closed
  rollback output for generated paths, and review the resulting reverse plan.
  There is no force rollback and no direct default-branch mutation.

Pull-request merge remains a human authority boundary outside Pace.

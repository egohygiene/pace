# pace

⚡ Automation, CI/CD, adoption, reconciliation, and synchronization infrastructure for evolving repositories.

Pace begins with a read-only, independently verifiable desired-state lock. The
`egohygiene.pace.lock/v1` contract records exact foundation, Aether, workflow,
container, site, and schema sources; their immutable references and SHA-256
digests; target ownership; compatibility and migration state; rollback mode;
and bounded exceptions.

## Validate a lock

```bash
python3 scripts/validate_lock.py "examples/pace.lock.json"
```

The validator has no updater dependency, third-party Python packages, network
access, or write behavior. It validates the example, contract semantics,
generated ownership, and exception expiry independently.

```bash
python3 scripts/validate_lock.py \
  "examples/pace.lock.json" \
  --as-of "2026-08-22T00:00:00Z" \
  --format "json"
```

See the complete [lock and update policy](LOCK_POLICY.md), the
[JSON Schema](schemas/pace-lock-v1.schema.json), and the
[six-kind example](examples/pace.lock.json).

## Plan reviewed fleet convergence

The general convergence path consumes Hygiene catalog membership, Holon
foundation intent, current and desired Pace locks, and Observatory's current
represented state. It produces deterministic dependency-ordered drift before
any write and requires an exact review for each repository-sized upgrade unit.

```bash
python3 scripts/plan_fleet_convergence.py plan \
  --manifest "examples/convergence/fleet.manifest.json" \
  --catalog "examples/convergence/catalog.json" \
  --observatory "examples/convergence/observatory.snapshot.json" \
  --output "/tmp/fleet-convergence.plan.json"

python3 scripts/plan_fleet_convergence.py verify-plan \
  --plan "/tmp/fleet-convergence.plan.json"
```

After review, `propose` prepares one credential-free PR request and `open-pr`
accepts only an exact candidate tree on the still-current represented commit.
See the [fleet convergence contract and operator guide](docs/fleet-convergence.md).

## Plan repository-presentation rollout

Pace now owns a read-only, privacy-safe repository-presentation inventory and a
deterministic fleet planner. The checked snapshot classifies every repository,
defines the Mantle/Identity/Antidote canary wave, reports blockers and drift,
and requires an exact reviewed plan plus pinned Egolint evidence before it can
emit one credential-free repository proposal.

```bash
python3 scripts/plan_repository_presentation.py validate-inventory \
  --inventory "examples/repository-presentation.inventory.json"
python3 scripts/plan_repository_presentation.py plan \
  --inventory "examples/repository-presentation.inventory.json" \
  --output "/tmp/repository-presentation.plan.json"
python3 scripts/plan_repository_presentation.py verify-plan \
  --plan "/tmp/repository-presentation.plan.json"
```

See the [rollout contract and operating guide](docs/repository-presentation-rollout.md).

## Current authority boundary

Pace validates desired locks and can turn pinned catalog, Holon, lock, and
Observatory inputs into deterministic no-write fleet plans. After an exact
human review, it can verify a locally materialized candidate and open one
bounded consumer pull request. It never scans repositories, renders Holon
outputs, updates a default branch, or merges a pull request.

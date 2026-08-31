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

Pace validates desired locks and can now turn a reviewed repository-presentation
inventory into a deterministic no-write fleet plan. It may emit a credential-free
single-repository proposal only after exact plan review and valid pinned Egolint
evidence. It still does not edit consumer files, open pull requests, or apply
changes; those remain separately authorized authority boundaries.

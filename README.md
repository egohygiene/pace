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

## Current authority boundary

Pace v1 validates desired state only. It does not resolve updates, edit files,
open pull requests, or apply changes. Future detection, planning, application,
verification, and publication phases remain separate authority boundaries.

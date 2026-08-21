# Pace lock, provenance, exception, and update policy

## Purpose

A Pace lock is a repository-owned record of the exact foundation, Aether,
workflow, container, site, and schema inputs a repository has adopted. It makes
desired state reviewable without giving Pace permission to update anything.

The v1 contract is [`egohygiene.pace.lock/v1`](schemas/pace-lock-v1.schema.json).
Locks are JSON so standard review tools, JSON Schema tooling, and the standalone
validator can inspect the same closed representation.

## Required provenance

Every lock entry records:

- a stable entry ID and one of the six supported dependency kinds;
- the source owner, locator, human version, immutable reference type, immutable
  reference, and SHA-256 content digest;
- the target repository path, its owner, whether it is generated or
  consumer-owned, and the generator when applicable;
- the compatibility contract and accepted major version;
- migration and rollback state;
- either no exception or one approved, tracked, time-bounded exception.

Git sources use a full lowercase 40-character commit SHA. OCI sources use an
immutable `sha256:` manifest digest. Content-addressed site or schema inputs use
a `sha256:` reference. For OCI and content-addressed sources, the reference and
recorded digest must agree. A future resolver may additionally fetch and verify
bytes, but the independent validator performs no network calls and never trusts
an updater's result.

## Generated ownership

Target ownership controls what a future Pace apply phase may change:

| Management | Generator | Required rollback | Meaning |
| --- | --- | --- | --- |
| `generated` | Required owner/repository identity | `restore-lock-and-generated-targets` | The named generator owns regeneration; reviewed rollback restores both the previous lock and generated target bytes |
| `consumer-owned` | Must be `null` | `restore-lock-only` | Pace records desired source state but never rewrites the target; the consumer owns migration and content rollback |

A lock does not grant write authority. Detection, update planning, application,
verification, and publication remain separate operations.

## Compatibility and migration

Every entry names a contract ending in `/vMAJOR`; `accepted_major` must match.
Unknown contracts fail closed. Compatibility within a major does not imply that
an update is behaviorally safe—it means the source declares the same contract
family and may proceed to review and verification.

Migration states are:

- `not-required`: the selected source is compatible with the target state;
- `required`: migration work is known but incomplete, so validation fails and
  the lock is not adoptable;
- `completed`: required migration evidence is included in the reviewed change.

A major transition requires a new contract declaration, explicit migration,
and a reviewed lock update. Pace never silently widens a compatibility range.

## Update sequence

A future updater must preserve these boundaries:

1. Read and independently validate the existing lock.
2. Resolve candidate source versions without modifying the repository.
3. Verify immutable references and content digests.
4. Compare declared contract majors and identify migration requirements.
5. Produce a deterministic plan containing lock and owned-target changes.
6. Open a reviewable pull request; never push directly to the default branch.
7. Run the standalone validator on the proposed lock independently of the
   updater.
8. Regenerate only targets marked `generated` and owned by the named generator.
9. Verify resulting bytes and repository tests before merge.

The v1 work implements steps 1 and 7. Resolution, planning, and application are
deliberately outside this issue.

## Rollback

The previous accepted lock is the rollback anchor. A failed or reverted update:

- restores the previous lock document;
- restores previous bytes for targets whose management is `generated`;
- leaves consumer-owned target content under consumer control;
- reruns independent validation and repository verification;
- records the failed source version so automation does not immediately repeat
  the same unsafe update.

Rollback never replaces a lock with an unreviewed mutable reference.

## Exceptions

Exceptions are first-class lock records, not comments or hidden repository
settings. Each includes a unique `EXC-YYYY-NNN` ID, reason, approver, issue time,
expiry time, and HTTPS tracking URL.

- Repository policy bounds exceptions to 1–90 days.
- An entry's expiry must be after issuance and within the repository maximum.
- Future and expired exceptions fail validation at the selected validation
  instant.
- Exceptions never bypass JSON structure, immutable-reference, digest,
  ownership, compatibility-major, or rollback requirements.
- Renewal is a new reviewed decision with a new bounded interval; expiry is not
  extended silently.

Use `--as-of` in tests and evidence pipelines for deterministic evaluation.
Normal local validation uses the current UTC instant.

## Independent validation

```bash
python3 scripts/validate_lock.py "path/to/pace.lock.json"

python3 scripts/validate_lock.py \
  "path/to/pace.lock.json" \
  --as-of "2026-08-22T00:00:00Z" \
  --format "json"
```

The validator uses only the Python standard library. It rejects duplicate JSON
keys, unknown fields, malformed or mutable references, inconsistent digests,
ambiguous ownership, unsafe rollback declarations, duplicate IDs or targets,
unsorted entries, pending migrations, and invalid exception windows.

Exit status `0` means the lock is valid at the evaluation instant. Status `1`
means the document could not be loaded or violates the lock contract. Argument
errors use the standard status `2`. JSON output uses
`egohygiene.pace.lock-validation/v1`.

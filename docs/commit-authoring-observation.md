# Offline commit-authoring inventory

Issue [#21](https://github.com/egohygiene/pace/issues/21) owns prospective
commit-authoring rollout. This checkpoint inventories a supplied, digest-pinned
snapshot through the existing [offline observation boundary](release-adoption-observation.md).
It does not rewrite history, install hooks, execute configuration, change
repository settings or enroll repositories in enforcement.

```sh
python3 scripts/observe_commit_authoring.py \
  --snapshot examples/observations/commit-authoring.snapshot.json \
  --lock examples/observations/commit-authoring.lock.json \
  --as-of 2026-11-14T00:00:00Z
```

The fictional fixture intentionally has two conflicting Commitizen adapters,
an executable JavaScript configuration that must never execute, hooks, a captured
PR-title workflow, package script names, missing Taskfiles and a supplied merge
policy observation. None describes the actual organization fleet.

The shared input schema uses kind `commit-authoring`. Digest checks precede
parsing, repository and source identities are explicit, input size/path/type
budgets apply, receipts refuse overwrite, and source observation clocks never
refresh themselves. Add captured `.husky/`, `.githooks/`, `hooks/` and workflow
paths when applicable. Candidate filenames are a discovery vocabulary, not a
claim that unlisted configurations do not exist. Missing, unavailable and
unknown remain distinct; an incomplete snapshot cannot prove configuration
absence. JavaScript, YAML, hook bodies and workflows are observed by path/hash
only and are not evaluated or interpreted as passing conformance.

The observer records package-script names without copying shell commands.
Known Commitizen JSON and package configuration can identify a simple npm
adapter name; malformed data and conflicting adapters are explicit. Local-path
or executable adapter resolution is unsupported rather than run. No configuration
precedence is silently chosen. Descriptive source presence does not mean a hook
is installed or a workflow is active.

An optional `merge_policy` source assertion has `state: observed`, the three
strict boolean fields `allow_merge_commit`, `allow_squash_merge`,
`allow_rebase_merge`, and its exact GitHub repository API source URL. Unknown or
unavailable assertions contain only their state. They are captured assertions,
not live API verification; the observer never changes those settings.

Output compatibility, adoption and enforcement remain `not-assessed` until the
canonical accepted policy and validator are actually available. Even matching
adapter names are not enough to call a repository canonical or compatible.
The target lock preserves supplied proposed/unknown/accepted authority; accepted
targets require an immutable source revision. Exemptions and ratchet/enforce
choices need their owning reviewed contracts, not a source-presence heuristic.

Public output rejects a restricted inventory; explicit file receipts are created
exclusively with owner-only permissions even under a permissive umask. This
shared writer also protects the preceding release observer when this stack is
integrated. No actual fleet scan, private source capture, history migration or
default-branch write occurs here. Full fleet coverage, specific real repository
divergence reconciliation, reviewed rollout waves and eventual integration with
Holon/EgoLint/Relay remain open under #21. Existing history and tooling stay put.

Run `python3 -B -m unittest discover --start-directory tests --pattern test_commit_observation.py --verbose`.

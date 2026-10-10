# Label rollout — Aether pilot

Refs [Pace #10](https://github.com/egohygiene/pace/issues/10).

The current checkpoint produces a real, checksum-bound synchronization plan for
`egohygiene/aether` using the pinned Relay planner and the organization's merged
Aether enrollment. It is **ready for review**. This Pace adapter remains read-only:
no provider labels, issue classifications, or titles have been changed by it.

## Result at the current observation

| Finding | Result |
| --- | --- |
| Observed labels | 41, all retained in the report |
| Missing universal labels | 18, including all six `type:*` labels |
| Native Relay operations | Create 18; update 0; delete 0 |
| Aether canonical assignment | Universal labels, no overlays or additions |
| Native Relay synchronization plan | Present with a content checksum |
| `.github/relay-labels.json` | Absent at the recorded Aether source revision |
| Aether label/issue mutations / workflow dispatches by this checkpoint | 0 / 0 |

Evidence:

- [Current public observation](evidence/label-rollout/aether-observation-2026-10-10.json)
- [Current machine preview](evidence/label-rollout/aether-preview-2026-10-10.json)
- [Current verification and handoff](evidence/label-rollout/checkpoint-2-verification-2026-10-10.json)

The observation spans 2026-10-10 02:54:43–02:54:54 UTC. One terminal label page
contained all 41 records. Public reads were credential-free GETs without redirect
following. Reads are sequential and non-atomic; capture times and raw response
digests are retained. Configuration absence is separately bound to Aether
`8ef3bd34d5fec835da54eb8acd0d074b79ee8fe2`. Neither the repository commit nor this
saved report proves that provider labels remain current later. Refresh before apply.

| Group | Required universal labels |
| --- | --- |
| Primary type | `type:architecture`, `type:feature`, `type:bug`, `type:documentation`, `type:research`, `type:maintenance` |
| Priority | `priority:p0`, `priority:p1`, `priority:p2`, `priority:p3` |
| Area | `area:automation`, `area:developer-experience`, `area:governance`, `area:security` |
| Coordination/status | `cross-repo`, `needs-routing`, `blocked`, `ready` |

The JSON retains canonical colors and descriptions. `native_sync_plan` is Relay's
canonical plan; the separate universal-only comparison stays advisory. Expressive
labels such as `🏗️ architecture` are retained and are not aliases for `type:architecture`.
Creating the six primary-type labels does not attach them to any issue.

## Ownership and exact inputs

The [pilot lock](../contracts/label-rollout-pilot.v1.lock.json) pins the Relay tree,
planner source and its label-contract lock. Byte-identical upstream catalog and
assignment files are retained under `vendor/github/label-rollout/` solely for offline
verification. They are snapshots, not Pace-owned taxonomy or enrollment.

| Owner | Selected input |
| --- | --- |
| Relay execution | `425d3cc22673b0509abb3c54f184e07111d5a4df` |
| Organization taxonomy/assignments selected by Relay | `egohygiene/.github@8b16273eaf0709a7ce95f5e352a2b0d38cfac131`, catalog 1.1.0 |
| Enrollment change | Organization PR #47; Aether receives universals with no overlay or additions |
| Issue-title preview | Separate existing contract selection; this label update does not promote title authority |

Relay owns canonical label resolution and provider mutation. Pace composes its
`validate_contract`, `plan_sync` and `verify_plan` functions from verified Git objects,
without executing a modified checkout file. No network or provider-write command
exists in the Pace adapter. Initial capture is an explicit bounded operator read;
the adapter only consumes the saved observation. Pace's separate Observatory-based
fleet convergence flow is unchanged.

## Values for the local apply handoff

Use the [pinned Relay local-apply guide](https://github.com/egohygiene/relay/blob/425d3cc22673b0509abb3c54f184e07111d5a4df/docs/label-rollout-local.md)
with the [current preview artifact](evidence/label-rollout/aether-preview-2026-10-10.json).
Its `native_sync_plan` proposes the 18 additions above. The concrete selections are:

```bash
RELAY_REVISION="425d3cc22673b0509abb3c54f184e07111d5a4df"
EXPECTED_PLAN_SHA256="c0ee4b005b477e88deb8235cf9b418de30319881c5f11771d241a087a6922f23"
```

The checksum belongs to the native plan, not this outer Pace report. The guide
recaptures provider state and requires its newly generated plan to match before
writing. A mismatch requires review of the changed state. No authenticated label
application or provider read-back is claimed here; retain those receipts separately.

## Local replay

Use Python 3.10+ and Git; the adapter and Relay planner use the standard library.
Acquire the selected Relay commit, then replay offline:

```bash
git clone --no-checkout "https://github.com/egohygiene/relay.git" \
  "/absolute/path/to/relay"
git -C "/absolute/path/to/relay" fetch origin \
  "425d3cc22673b0509abb3c54f184e07111d5a4df"

python3 scripts/preview_repository_labels.py \
  --relay "/absolute/path/to/relay" \
  --observation "docs/evidence/label-rollout/aether-observation-2026-10-10.json" \
  --output "/absolute/path/to/new-label-preview.json"
```

Exit **0 is expected for the current selection**: a native plan was generated for
review, not applied. Exit 2 identifies missing canonical enrollment. Exit 3 means
invalid/unavailable inputs or unsafe/existing output. The output parent must exist;
the destination must be new and have no symlink components. Partial inventories are
rejected; configured consumers require a separately reviewed extension.

Seven focused tests cover real pinned Relay planning, additive operations,
byte-identical CLI replay, unchanged observation bytes, incomplete coverage and
source drift rejection, and output preservation. Run only these when needed:

```bash
PACE_LABEL_RELAY_SOURCE="/absolute/path/to/relay" \
  python3 -m unittest discover --start-directory tests \
  --pattern "test_label_pilot.py" --verbose
```

Without the environment variable the native tests skip. Hosted Actions, broad tests,
linting, audits, path-labeler installation and fleet mutation remain deferred.

## Historical checkpoint 1

[Pace PR #33](https://github.com/egohygiene/pace/pull/33) merged at
`cfe8ed9db55a5ddf8580c72f4d7991f6391386a1`. Its original
[observation](evidence/label-rollout/aether-observation-2026-10-08.json),
[blocked preview](evidence/label-rollout/aether-preview-2026-10-08.json), and
[verification](evidence/label-rollout/checkpoint-1-verification-2026-10-08.json)
remain unchanged. Relay then selected organization revision
`b415c8029bf2fb5d474f367e7129791588ba3860`, which did not enroll Aether. The blocked
report is accurate for that historic selection. Replay that checkpoint from the
PR #33 merge commit; using today's lock intentionally yields today's selection.

## Checkpoint handoff and next work

1. **Complete:** organization-owned Aether enrollment and Relay/Pace pin updates;
   fresh provider observation and a native synchronization plan with 18 additive
   operations. Pace #10 remains open because rollout is broader than this pilot.
2. **Next:** refresh the bounded provider inventory, compare the exact plan, apply
   the reviewed additions through Relay's authorized provider path, and retain
   read-back evidence. A missing authenticated execution capability is a blocker,
   never evidence of application. Existing labels must be retained.
3. **Then:** explicitly classify selected issues and rerun the title preview.
   Label creation alone does not classify an issue or authorize title rewriting.
4. **Then:** complete the separate title apply/recovery checkpoint with fresh-state
   comparison, conflicts, receipts, guarded rollback, retry and no-op repeat.
   Path-labeler installation and broader Pace #10 rollout remain later work.

Rollback of this preview means reverting the Pace selection or discarding local
output; it has no provider state to reverse. A future additive label rollout must
not equate rollback with deleting labels that other issues may already use.

This scoped guide is the handoff; it does not install Pace #26's separate continuity
rollout. Fresh sessions should read this guide and Pace's architecture, system,
decisions and roadmap, then verify current issues, PRs and provider state.

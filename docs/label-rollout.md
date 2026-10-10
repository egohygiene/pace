# Label rollout — Aether pilot

Refs [Pace #10](https://github.com/egohygiene/pace/issues/10).

The bounded Aether label pilot has been applied and read back: 18 canonical
labels were created, all 41 existing labels were preserved, and the pinned Relay
planner now reports zero operations against 59 provider labels. An authorized
operator used GitHub's browser interface because the available connector could
not create repository labels. Pace's adapter remains read-only; this does not add
a provider write port or claim fleet rollout. Aether #63, #92 and #94 now have
`type:architecture` and their reviewed canonical titles. Provider read-back and a
fresh native preview verify all three titles conform and need no further changes.

## Applied label checkpoint

| Finding | Verified result |
| --- | --- |
| Provider labels after application | 59 |
| Canonical additions | 18; exact catalog names, colors, and descriptions verified |
| Existing labels | All 41 IDs and metadata preserved |
| Native Relay operations after read-back | Create 0; update 0; delete 0; unchanged 18 |
| Reviewed plan checksum before writes | `c0ee4b005b477e88deb8235cf9b418de30319881c5f11771d241a087a6922f23` |
| Native plan checksum after read-back | `c8547fee264dfb062ed97842d11bcb394e1a23c831ca5d0c1e7297cff520de69` |
| Hosted workflow dispatches | 0 |

These label checks establish convergence only for Aether at the recorded
read-back. Classification and title writes have separate receipts below; neither
pilot enforces future titles or establishes fleet convergence. The original
planning evidence remains unchanged.

## Applied three-issue title checkpoint

The operator added only `type:architecture` to Aether #63, #92 and #94, then
applied the three explicitly reviewed canonical titles. Existing subject wording
and the `[Release checkpoint 1]` identifier were preserved. Fresh issue reads
confirmed the expected titles and full label sets; the native after-preview
reports three unchanged, conformant titles. No other issues were selected.

Evidence for this bounded execution:

- [Execution receipt](evidence/label-rollout/aether-applied-2026-10-10/receipt.json)
  and [execution details](evidence/label-rollout/aether-applied-2026-10-10/execution.json).
- Label inventories [before](evidence/label-rollout/aether-applied-2026-10-10/labels-before.json)
  and [after](evidence/label-rollout/aether-applied-2026-10-10/labels-after.json),
  with native plans [before](evidence/label-rollout/aether-applied-2026-10-10/label-plan-before.json)
  and [after](evidence/label-rollout/aether-applied-2026-10-10/label-plan-after.json).
- Title [operation receipts](evidence/label-rollout/aether-applied-2026-10-10/title-operations.json);
  before [snapshot](evidence/label-rollout/aether-applied-2026-10-10/title-before/snapshot.json),
  [reviews](evidence/label-rollout/aether-applied-2026-10-10/title-before/reviews.json),
  [plan](evidence/label-rollout/aether-applied-2026-10-10/title-before/plan.json) and
  [preview](evidence/label-rollout/aether-applied-2026-10-10/title-before/preview.md).
- After [snapshot](evidence/label-rollout/aether-applied-2026-10-10/title-after/snapshot.json),
  [reviews](evidence/label-rollout/aether-applied-2026-10-10/title-after/reviews.json),
  [plan](evidence/label-rollout/aether-applied-2026-10-10/title-after/plan.json) and
  [preview](evidence/label-rollout/aether-applied-2026-10-10/title-after/preview.md).

This proves a manual pilot and repeat verification. No rollback or interruption
recovery drill was executed, and no reusable apply/recovery engine was introduced.

## Historical planning observation

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

- [Planning public observation](evidence/label-rollout/aether-observation-2026-10-10.json)
- [Planning machine preview](evidence/label-rollout/aether-preview-2026-10-10.json)
- [Planning verification and handoff](evidence/label-rollout/checkpoint-2-verification-2026-10-10.json)

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

## Replaying the original local apply handoff

Use the [pinned Relay local-apply guide](https://github.com/egohygiene/relay/blob/425d3cc22673b0509abb3c54f184e07111d5a4df/docs/label-rollout-local.md)
with the [current preview artifact](evidence/label-rollout/aether-preview-2026-10-10.json).
Its `native_sync_plan` proposes the 18 additions above. The concrete selections are:

```bash
RELAY_REVISION="425d3cc22673b0509abb3c54f184e07111d5a4df"
EXPECTED_PLAN_SHA256="c0ee4b005b477e88deb8235cf9b418de30319881c5f11771d241a087a6922f23"
```

The checksum belongs to the native plan, not this outer Pace report. This is the
original 18-create plan, not an instruction to repeat its writes. The guide
recaptures provider state and requires its newly generated plan to match before
writing. A mismatch requires review of changed state. After the recorded
application, a fresh plan should have no operations; never replay the old creates.

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

1. **Complete:** organization-owned Aether enrollment, Relay/Pace pin updates,
   reviewed synchronization plan, 18 browser-applied additions, and provider
   read-back with zero native operations. All 41 prior labels remain intact.
2. **Complete:** Aether #63, #92 and #94 were explicitly classified as
   `type:architecture` and received their reviewed titles. Fresh provider
   read-back and the pinned native preview confirm three unchanged titles.
3. **Later:** implement reusable title apply/recovery, event enforcement, path
   labelers and broader Pace #10 rollout. A successful manual pilot does not
   establish these capabilities. Pace #10 remains open.

## Scoped three-issue recovery procedure

This is an operator procedure for Aether #63, #92 and #94, not a generic apply
engine. The title contract and Relay preview selection remain separately pinned;
label catalog adoption does not promote title authority.

1. Save each issue's repository, number, stable provider ID, title, complete label
   set, body digest, state, `updated_at` and observation time. Bind explicit type/subject reviews
   to the collected snapshot digest and retain the exact native preview plan.
2. Immediately before each classification or title write, reread the issue and
   compare identity, title and the full normalized label set with that operation's
   recorded before-state. Also verify the body, open state and `updated_at` remain unchanged.
   Stop on drift; recollect and review it instead of overwriting another edit.
3. Add only `type:architecture` through the additive label operation. Preserve
   every existing label. Recollect and generate a fresh title preview after
   classification; do not use a plan made against the pre-classification state.
   Apply only the exact reviewed title, then read back identity, title, full label
   set, body digest, state and `updated_at`. Save a receipt immediately after each operation, including
   the requested transition, write result, read-back and any uncertainty.
4. On interruption or an uncertain response, reread before retrying. If current
   state exactly matches the recorded expected after-state, record reconciliation
   and skip the already-applied operation. Retry only a still-pending operation
   whose before-state matches. Any other state is a conflict requiring review.
   After all three, collect again and run the native preview: expect conformant
   titles with no proposed title changes, not merely successful API responses.
5. Title rollback is eligible only when fresh identity, title, complete label set,
   body digest, state and `updated_at` exactly match that title operation's recorded
   after-state. Restore only the prior title, then retain the reversal and read-back
   receipt. Stop on any drift. Classification retirement requires separate review;
   this procedure never removes labels or replaces the full label list.

These provider calls are sequential and do not provide atomic compare-and-swap.
A fresh comparison narrows the race window; read-back detects mismatches but cannot
prove no concurrent edit occurred. Preserve uncertain outcomes for reconciliation.

Reverting Pace evidence or a source selection does not reverse live labels. Do
not delete the 18 additions as a rollback shortcut: other issues may already use
them. Any label deletion needs a separate dependency review and authorization.

This scoped guide is the handoff; it does not install Pace #26's separate continuity
rollout. Fresh sessions should read this guide and Pace's architecture, system,
decisions and roadmap, then verify current issues, PRs and provider state.

# Label rollout — Aether checkpoint 1

Refs [Pace #10](https://github.com/egohygiene/pace/issues/10).

The first checkpoint is a local, read-only preview for `egohygiene/aether`.
It consumes a captured public label inventory and the actual pinned Relay label
planner. The checkpoint is complete for review; **canonical Aether synchronization
is blocked by missing enrollment**, not approved for application.

## Result at the recorded observation

| Finding | Result |
| --- | --- |
| Observed labels | 41, all retained in the report |
| Missing universal labels | 18, including all six `type:*` labels |
| Drifted existing universal labels | 0 |
| Proposed deletions / renames | 0 / 0 |
| Aether canonical assignment | Missing |
| Native Relay synchronization plan | Unavailable; no fabricated plan or checksum |
| `.github/relay-labels.json` | Absent at the recorded Aether source revision |
| Aether label/issue mutations / workflow dispatches | 0 / 0 |

Evidence:

- [Public observation](evidence/label-rollout/aether-observation-2026-10-08.json)
- [Machine preview](evidence/label-rollout/aether-preview-2026-10-08.json)
- [Verification and handoff](evidence/label-rollout/checkpoint-1-verification-2026-10-08.json)

The observation spans 2026-10-08 01:32:03–01:32:12 UTC. One terminal label page
contained all 41 records. Public reads were credential-free GETs without redirect
following. Provider reads are sequential and non-atomic; capture times and raw
response digests are retained. Git source/configuration evidence is separately
bound to Aether `8ef3bd34d5fec835da54eb8acd0d074b79ee8fe2`. Neither a repository
commit nor this saved report proves that provider labels remain current later.

The required universal names, if Aether is enrolled, are:

| Group | Labels |
| --- | --- |
| Primary type | `type:architecture`, `type:feature`, `type:bug`, `type:documentation`, `type:research`, `type:maintenance` |
| Priority | `priority:p0`, `priority:p1`, `priority:p2`, `priority:p3` |
| Area | `area:automation`, `area:developer-experience`, `area:governance`, `area:security` |
| Coordination/status | `cross-repo`, `needs-routing`, `blocked`, `ready` |

The JSON retains canonical colors and descriptions. This universal-only comparison
is advisory and deliberately distinct from `native_sync_plan`. Overlay selections
and repository-local additions require a canonical assignment; they are not inferred
from currently installed expressive labels. For example, `🏗️ architecture` is not
an alias that can silently replace `type:architecture`. Existing issue associations,
labels, titles, bodies, states and relationships have not been changed.

## Ownership and exact inputs

The [pilot lock](../contracts/label-rollout-pilot.v1.lock.json) pins the Relay tree,
planner source and its label-contract lock. Byte-identical upstream catalog and
assignment files are retained under `vendor/github/label-rollout/` solely for offline
verification. They are snapshots, not Pace-owned taxonomy or enrollment.

| Owner | Selected input |
| --- | --- |
| Relay execution | `e273030836b68bcb9912aae73e56ffbb31f33d48`, the merge of PR #136 |
| Organization taxonomy/assignments selected by Relay | `egohygiene/.github@b415c8029bf2fb5d474f367e7129791588ba3860` |
| Organization current-source comparison | `333e4e914b762cb817dcaed1d792435432f4fd5c`; assignment bytes unchanged and still only enroll `.github` |
| Issue-title preview | Relay #133 completed; its title contract remains candidate/observe at its separate existing pin |

The selected label catalog SHA-256 is
`7063a61608a66454310e5a7746b1514d1d11018da08427bfb49f4612326ff6ff`,
the same catalog bytes consumed by the issue-title pilot. The matching catalog
bytes do not grant Aether adoption or promote title-contract authority.

Relay remains responsible for canonical label resolution and provider mutation.
Pace composes its `validate_contract`, `plan_sync` and `verify_plan` functions from
verified Git objects, without executing a potentially modified checkout file.
No network or provider-write command exists in the Pace adapter. It does not alter
Pace's separate Observatory-based fleet convergence flow. Initial capture was an
explicit bounded operator read; this adapter consumes the saved observation.

## Local replay

Use Python 3.10+ and Git; the adapter and pinned Relay planner use the standard
library. Acquire the selected Relay commit, then replay offline:

```bash
git clone --no-checkout "https://github.com/egohygiene/relay.git" \
  "/absolute/path/to/relay"
git -C "/absolute/path/to/relay" fetch origin \
  "e273030836b68bcb9912aae73e56ffbb31f33d48"

python3 scripts/preview_repository_labels.py \
  --relay "/absolute/path/to/relay" \
  --observation "docs/evidence/label-rollout/aether-observation-2026-10-08.json" \
  --output "/absolute/path/to/new-label-preview.json"
```

Exit **2 is the expected blocked result** for this capture: the enrollment prerequisite
is missing. Exit 0 means an enrolled native plan was generated for review, not approved
or applied. Exit 3 means invalid/unavailable inputs or unsafe/existing output.
The output parent must already exist; the destination must be new and have no symlink
components. Existing evidence is never overwritten. A partial or unterminated label
inventory is rejected, and configured consumers require a separately reviewed extension.

Seven focused tests passed with no skips, including real pinned Relay execution,
byte-identical CLI replay, unchanged observation bytes, rejection of incomplete
coverage and source drift, and output preservation. Repeat locally if needed:

```bash
PACE_LABEL_RELAY_SOURCE="/absolute/path/to/relay" \
  python3 -m unittest discover --start-directory tests \
  --pattern "test_label_pilot.py" --verbose
```

Without that environment variable the native tests skip. Hosted Actions, broad tests,
linting, audits, path-labeler installation and fleet mutation remain deferred.

## Checkpoint handoff and next work

1. **Completed here:** capture Aether's labels, verify canonical inputs, run the actual
   planner, retain the enrollment blocker and universal-label comparison, prove replay,
   and deliver the evidence through a Pace draft PR. Pace #10 remains open.
2. **Next owner change — `.github`:** add explicit Aether enrollment to
   `.github/labels/repositories.v1.json`. A proposed minimal starting point is universal
   labels with no overlays or additions, retaining all existing provider labels.
   Review relevant overlays explicitly. Follow `docs/label-governance.md`: additive
   assignments require the appropriate catalog minor-version update and matching
   assignment version. This is a proposal, not an accepted assignment in this checkpoint.
3. **Then Relay/Pace:** repin Relay's label contract to the reviewed merged organization
   change, preserve compatible title-contract selection, update this pilot selection,
   acquire fresh provider evidence, and regenerate a real checksum-bound sync plan.
4. **Then label adoption/classification:** apply only the reviewed label operations,
   verify them, explicitly classify the selected issues, and rerun the title preview.
   Creating labels alone does not attach a primary type to an issue.
5. **Then title application:** the separate Relay apply/recovery checkpoint still needs
   approval binding, fresh-state comparison, conflicts, receipts, guarded rollback,
   interruption/retry and no-op repeat. Broader Pace #10 rollout remains later work.

Rollback of this preview means discarding its local output or reverting the Pace
candidate; it has no provider state to reverse. Future additive label adoption must
retain existing labels by default and must not equate rollback with deletion.

Relay PR #136 was merged at the source revision above and issue #133 was closed with
its preview-only acceptance receipt. Parallel Relay PR #135 remains separate.
Pace had no `AGENTS.md`, root `CONTINUITY.md`, or open PRs at inspection; this scoped
handoff does not claim installation of the separate Pace #26 continuity rollout.
Fresh sessions should read this guide, Pace's architecture/system/decisions/roadmap,
then verify the parent issue and current PR state before selecting the next action.

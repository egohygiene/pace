# Repository Intelligence adoption checkpoint

Pace owns the adoption projection and the next repository-sized handoff for
[Pace #13](https://github.com/egohygiene/pace/issues/13) and the roadmap capability
campaign [#31](https://github.com/egohygiene/pace/issues/31). Hygiene retains
membership, applicability, cadence and policy ownership through
[Hygiene #36](https://github.com/egohygiene/hygiene/issues/36). A missing builder,
origin or receipt does not decide eligibility, establish an exemption or retire
a repository.

The [dated ledger](evidence/intelligence-adoption/2026-11-11.ledger.json) and
[operator table](evidence/intelligence-adoption/2026-11-11.md) project all 28
entries in one exact reviewed **public snapshot**. They assert no organization
total, adoption percentage or fleet-completion verdict. Source and builder
observations remain separate from actual model artifacts, destinations, live
verification and refresh ownership.

## Exact inputs and clocks

| Input | Immutable source | Raw SHA-256 |
| --- | --- | --- |
| Public membership | Hygiene `49639c1845cdfd08fbd5a768261a8b3cf515f80f`, `catalog/public-repositories.json` | `af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26` |
| Source observations | .github `101a0d4553dc380ab3f88c50b11cb53beadfce18`, `docs/intelligence/repositories.source.json` | `c4e41df201500c5a00aa7b0e5e30cc4d8054f33eb39c842718266c70530175a9` |

The [input receipt](../contracts/repository-intelligence-adoption-inputs.v1.lock.json)
records trees and local byte mirrors. The projector contains the same literal
source pins; editing the receipt alone cannot admit a different inventory.
These mirrors are derived inputs, not a replacement catalog or a new scan.
Only the exact public artifacts are admitted before payload processing, IDs,
duplicates or joining. Errors disclose no unreviewed payload or calculated
mismatch digest. No private-input placeholders or excluded totals are emitted.

`projection_as_of` dates the projection. It does **not** refresh either input.
The inventory was observed at `2026-11-10T23:49:35Z`; the public catalog identity
snapshot was observed at `2026-11-09T14:06:57Z`. Each row retains its actual
inspection time and represented source commit. The inventory package revision
is distinct from those represented commits: the `.github` row still represents
`ac2e4035173ed252d71d6655e723964ef93684df`, before its later organization-home
work. Catalog roles, maturity and policy dates are neither copied into adoption
status nor refreshed by this ledger.

The two issue-reported holds were read on `2026-11-11T18:54:40Z`. Their issue
update times and narrow scopes remain explicit. An open issue reports a hold;
it does not prove a new native failure against every newer commit.

## Read the independent stages

| Field | Meaning in this source-only profile |
| --- | --- |
| `source` | Captured immutable source, inspected paths and observational gaps. Roadmap content and decision conformance remain unassessed. |
| `builder` | Exact workflow/action references, conditions, output paths and historical rollback alternatives. Same-workflow composition is a source declaration; execution remains unknown. |
| `model_artifact` | Unknown, with no selection. No run, attempt, artifact ID, digest, baseline, coverage or normalized-model success is invented. |
| `destination` | Explicit source origin/base path and declaration evidence. A derived Intelligence URL is offered only with a composition declaration and explicit path basis. Provider configuration and publication remain unknown. |
| `live_verification` | Unknown, without a deployment or live-byte receipt. A declared URL is not a verified endpoint. |
| `refresh_owner` | Unknown owner, procedure, cadence and evidence. Repository identity, role or workflow triggers do not appoint an operator or activate a cadence. |
| `next_action` / `next_issue` | A proposed bounded operator handoff and an existing coordination/owner issue. These fields create no issue, assignment, priority or approval. |

The initial model artifact, execution, provider, live verification and refresh
owner stages are unknown for every row. This means **not selected or checked
here**, rather than absent, failed, blocked, obsolete or healthy. The contract
deliberately cannot express completed adoption. Its
[closed schema](../schemas/repository-intelligence-adoption-ledger-v1.schema.json)
describes this source-only profile; semantic validation additionally requires
exact equality with the admitted source projection. Hand-editing a green status
cannot pass semantic validation.

## Replay the source projection

The standard-library-only implementation has no Git subprocess, network client,
credential input, consumer source execution or mutation adapter. It reads bounded
regular JSON files and emits JSON to stdout or a new explicitly named output.
Existing files are never overwritten. The following commands are operator
instructions, **not execution evidence from this checkpoint**:

```bash
python3 scripts/project_intelligence_adoption.py project \
  --as-of 2026-11-11T18:58:15Z \
  --output /tmp/repository-intelligence-adoption.ledger.json

python3 scripts/project_intelligence_adoption.py verify \
  --ledger docs/evidence/intelligence-adoption/2026-11-11.ledger.json
```

`--inventory` and `--public-catalog` may point to other local copies of the
**same exact bytes**, not arbitrary inventories. Missing, changed, oversized or
nonregular inputs fail closed with a neutral message. Timestamps use explicit
UTC seconds and cannot precede captured evidence. The pure API is
`project(inventory_bytes, public_catalog_bytes, *, as_of) -> dict`;
`validate_ledger(value, inventory_bytes, public_catalog_bytes) -> dict` verifies
the whole semantic projection, including pins, complete membership and unknown
states. `canonical_bytes(value)` is UTF-8, sorted keys, indent two, no NaN,
with a trailing newline. Schema shape validation alone authenticates no source.

This change received source/AST/JSON/schema review only. The shipped projector,
tests, builds, native collectors, CI, provider configuration and live publication
have not been qualified by this checkpoint. The dated data artifact was authored
from pinned structured source data without running the shipped projector.

## Work one row through its owning issue

1. Read the row's immutable source, current owner issue and preserved holds.
   If source has changed, record a new source observation through the canonical
   public inventory path and review the new source pins as a separate change.
   Do not make this old checkpoint appear freshly scanned by changing its date.
2. Review the intended delivery profile through Pace #13 and Hygiene's policy
   owner. A repository can need local Pages composition, central aggregation,
   artifact-only delivery or another explicit owner choice. Missing setup does
   not choose a profile. Keep the repository's existing publisher and rollback.
3. Prepare one repository-owned source change if required. Reuse Relay builders
   and Observatory models; do not copy their collection/validation semantics
   into Pace or introduce another publisher. Source changes and roadmap intent
   remain reviewable independently from operational acceptance.
4. During the separately authorized qualification phase, select the **actual**
   artifact identity and exact represented revision, raw digest, producer pin,
   run/attempt, freshness, model coverage and consumer destination. Capture the
   shared owner receipts for composition/non-clobber, deployment and live bytes
   separately. This initial profile accepts no fabricated or manually promoted
   receipt; a future receipt-consuming contract extension must bind and validate
   the owners' real artifacts before it can show those stages.
5. Record the actual refresh operator, documented command and accepted trigger
   or cadence with source evidence. Hygiene owns cadence policy; workflow source
   alone is not an accepted refresh commitment. Retain upgrade, retry, drift and
   rollback evidence in the row's owner issue and the campaign.
6. Update the next bounded issue after reviewing the resulting evidence. A
   closed renderer ticket or green CI result does not complete Pace #13/#31.

Specific next handoffs in this checkpoint:

- **Hygiene #47:** Preserve the original ADR-0001 metadata and human-disposition
  hold, canonical-policy-owner semantics and strict publisher admission. This
  ledger supplies no approval, waiver, successful build or deployment.
- **Akashic #197:** Preserve the issue-reported roadmap dependency conflict,
  ADR-first sequence and older rollback evidence. Its newer builder pin does not
  prove that the roadmap canary has passed source/model/delivery acceptance.
- **OptiFlow:** Record an explicit origin and base path through the campaign
  before any public Intelligence link or live acceptance. Its observed builder
  is retained; no historical hostname is substituted for missing declaration.
- **Antidote / Mindgarden:** Review their artifact/preview handoff and older
  immutable pins before extending their consumer delivery. Artifact workflow
  source alone supplies neither a model artifact nor Pages composition.
- **Other rows:** Review delivery intent through Pace #13, then choose one
  repository-sized issue. Relay's reusable Pages library is not its own consumer
  publisher, and egohygiene.io's fleet overview is not its repository's own
  Intelligence adoption.

## Refresh, versioning and recovery

This checkpoint is immutable historical evidence. A future reviewed snapshot
updates the source pin, raw digest, mirror, projector admission and input receipt
together; the prior ledger stays available. Preserve the complete fixed public
selection unless Hygiene publishes a new reviewed public projection. There is
no automatic fetch, scheduler, issue writer or ledger promotion. Replace this
derived artifact by regenerating from reviewed inputs, never by editing stages
or changing canonical repository source as a side effect.

ADR impact: no new ADR is required for this slice. It implements the existing
Pace ADR-0001 separation of detection/planning/application and ADR-0004 immutable
source verification without changing upstream policy or human authority.

Refs: [Pace #13](https://github.com/egohygiene/pace/issues/13),
[Pace #31](https://github.com/egohygiene/pace/issues/31),
[Hygiene #36](https://github.com/egohygiene/hygiene/issues/36).

# Pace schemas

| Contract | Schema identity | File |
| --- | --- | --- |
| Repository dependency lock | `egohygiene.pace.lock/v1` | [`pace-lock-v1.schema.json`](pace-lock-v1.schema.json) |
| Fleet convergence manifest | `egohygiene.pace.fleet-convergence-manifest/v1` | [`fleet-convergence-manifest-v1.schema.json`](fleet-convergence-manifest-v1.schema.json) |
| Fleet convergence plan | `egohygiene.pace.fleet-convergence-plan/v1` | [`fleet-convergence-plan-v1.schema.json`](fleet-convergence-plan-v1.schema.json) |
| Fleet convergence review | `egohygiene.pace.fleet-convergence-review/v1` | [`fleet-convergence-review-v1.schema.json`](fleet-convergence-review-v1.schema.json) |
| Bounded upgrade PR | `egohygiene.pace.upgrade-pull-request/v1` | [`upgrade-pull-request-v1.schema.json`](upgrade-pull-request-v1.schema.json) |
| Presentation fleet inventory | `egohygiene.pace.repository-presentation-inventory/v1` | [`repository-presentation-inventory-v1.schema.json`](repository-presentation-inventory-v1.schema.json) |
| Presentation dry-run plan | `egohygiene.pace.repository-presentation-plan/v1` | [`repository-presentation-plan-v1.schema.json`](repository-presentation-plan-v1.schema.json) |
| Reviewed-plan authorization | `egohygiene.pace.repository-presentation-review/v1` | [`repository-presentation-review-v1.schema.json`](repository-presentation-review-v1.schema.json) |
| Credential-free proposal | `egohygiene.pace.repository-presentation-proposal/v1` | [`repository-presentation-proposal-v1.schema.json`](repository-presentation-proposal-v1.schema.json) |

Pace-owned contracts use the stable namespace:

```text
https://egohygiene.github.io/pace/contracts/<contract>/v<major>/schema.json
```

Schema versions are independent from the Pace implementation version. A
breaking field or semantic change requires a new major schema and explicit
migration guidance; v1 never changes meaning in place.

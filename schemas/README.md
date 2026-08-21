# Pace schemas

| Contract | Schema identity | File |
| --- | --- | --- |
| Repository dependency lock | `egohygiene.pace.lock/v1` | [`pace-lock-v1.schema.json`](pace-lock-v1.schema.json) |

Pace-owned contracts use the stable namespace:

```text
https://egohygiene.github.io/pace/contracts/<contract>/v<major>/schema.json
```

Schema versions are independent from the Pace implementation version. A
breaking field or semantic change requires a new major schema and explicit
migration guidance; v1 never changes meaning in place.

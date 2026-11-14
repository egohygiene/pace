# Offline release-adoption observation

Issue [#17](https://github.com/egohygiene/pace/issues/17) owns release observation;
[#32](https://github.com/egohygiene/pace/issues/32) owns reviewed adoption. This
checkpoint adds a standard-library observer over explicitly supplied source
captures. It has no repository scanner, updater, network client or apply port.

```sh
python3 scripts/observe_release_adoption.py \
  --snapshot examples/observations/release.snapshot.json \
  --lock examples/observations/release.lock.json \
  --as-of 2026-11-14T00:00:00Z
```

The fixtures are fictional; they are not current organization inventory.
`--output` accepts a new receipt path and refuses overwrite. Source snapshots
are byte-bound by a separately reviewed lock before JSON parsing; each present
captured file also carries its SHA-256. Repository revision and observation time
are supplied evidence assertions, not a GitHub signature or fresh collection.
Every supplied row is represented. Coverage is explicitly that supplied roster,
not an inferred organization total. Missing/unavailable/unknown files stay distinct.

The input shape is `egohygiene.pace.observation-input/v1`: kind `release`, an
aware `observed_at`, and repository rows containing identity, full revision,
visibility/lifecycle, captured files and optional current/latest tag assertions.
A captured file is either `{ "state": "present", "text": "...", "sha256": "..." }`
or a single state `missing`, `unavailable` or `unknown`. Portable paths are
metadata only; the observer never opens a captured path. The lock declares
`egohygiene.pace.observation-lock/v1`, matching kind, exact snapshot hash and a
target schema identity, source repository/revision and supplied authority state.

The [output schema](../schemas/release-adoption-observation-v1.schema.json)
keeps conformance/adoption/publication unavailable in this source-only profile.
The output separates declaration/profile, changelog heading, observed version
authorities, supplied tags, declared channels, freshness and unknown conformance,
migration, adoption and publication. Supported local authorities are package
JSON, Cargo/pyproject TOML and the declared catalog selector. Unsupported or
missing authorities do not gain a guessed version. A configured GitHub channel
is never publication proof. Proposed/unknown target authority suppresses drift
assessment; a supplied accepted target permits only schema-identity comparison,
not conformance or ratification. Actual validator/release evidence remains open.

Public reports reject a snapshot containing any restricted row without revealing
which row. Use explicit `--audience private` for private/internal inventories;
that output remains private. This flag is not declassification or publication
approval. Input ownership and source disclosure review remain the operator's duty.
No private content, credentials or real repository capture is needed by tests.

Run `python3 -m unittest discover --start-directory tests --pattern test_release_observation.py --verbose`.
Live fleet collection, authenticated EgoLint evidence, complete source/profile
support, approved producer release comparisons and actual adoption remain open
under #17. A later adapter should feed this input contract instead of teaching
the observer to mutate consumers.

#!/usr/bin/env python3
"""Project an exact public source inventory into a no-write adoption checkpoint.

No scanner, provider client, eligibility resolver, build runner or apply port.
The immutable inputs are authentication boundaries, not user-editable catalogs.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "egohygiene.pace.repository-intelligence-adoption-ledger/v1"
LIMIT = 512 * 1024
INPUTS = {
    "source_inventory": {
        "repository": "egohygiene/.github",
        "revision": "101a0d4553dc380ab3f88c50b11cb53beadfce18",
        "path": "docs/intelligence/repositories.source.json",
        "sha256": "c4e41df201500c5a00aa7b0e5e30cc4d8054f33eb39c842718266c70530175a9",
    },
    "public_roster": {
        "repository": "egohygiene/hygiene",
        "revision": "49639c1845cdfd08fbd5a768261a8b3cf515f80f",
        "path": "catalog/public-repositories.json",
        "sha256": "af9c7186ded0bb57b18741eaa5905314b96d6adb03736946c868e0fc4aa50b26",
    },
}
CAMPAIGN = "https://github.com/egohygiene/pace/issues/13"
ROADMAP_CAMPAIGN = "https://github.com/egohygiene/pace/issues/31"
POLICY = "https://github.com/egohygiene/hygiene/issues/36"
HOLD_OBSERVED_AT = "2026-11-11T18:54:40Z"
HOLDS = {
    "egohygiene/hygiene": [{
        "issue": "https://github.com/egohygiene/hygiene/issues/47",
        "scope": "original-ADR-0001-metadata-and-human-disposition",
        "state": "issue-reported-unresolved",
        "issue_updated_at": "2026-10-20T04:23:39Z",
        "observed_at": HOLD_OBSERVED_AT,
        "effect": "Preserve original ADR-0001 and strict source admission; this checkpoint supplies no human disposition or publication waiver.",
    }],
    "egohygiene/akashic": [{
        "issue": "https://github.com/egohygiene/akashic/issues/197",
        "scope": "roadmap-canary-source-prerequisite",
        "state": "issue-reported-unresolved",
        "issue_updated_at": "2026-09-26T19:59:12Z",
        "observed_at": HOLD_OBSERVED_AT,
        "effect": "Reconcile the issue-reported AKA-Q03/AKA-Q02 dependency through source review; do not infer resolution from a newer builder pin.",
    }],
}


def require(condition, message="Unsupported adoption input"):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def parse(raw):
    require(type(raw) is bytes and len(raw) <= LIMIT)
    def invalid(_):
        raise ValueError("Unsupported adoption input")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def canonical_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def utc(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value),
            "An explicit UTC timestamp is required")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def read_file(path):
    # No FIFO/device reads, links, special paths, or unbounded JSON buffering.
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= LIMIT)
        raw = handle.read(LIMIT + 1)
    require(len(raw) <= LIMIT)
    return raw


def admit(raw, name):
    require(type(raw) is bytes and len(raw) <= LIMIT)
    # Only an exact already-public artifact may pass to JSON processing.
    # Mismatches disclose neither payload, identity, count nor computed hash.
    require(hashlib.sha256(raw).hexdigest() == INPUTS[name]["sha256"],
            "Input does not match the reviewed public source pin")
    return parse(raw)


def next_action(row):
    repository = row["repo"]
    if repository == "egohygiene/hygiene":
        return ("review-preserved-source-hold",
                "Resolve original ADR-0001 metadata and durable human disposition through the owning issue; retain strict admission and separate artifact/deployment/live evidence.",
                HOLDS[repository][0]["issue"])
    if repository == "egohygiene/akashic":
        return ("review-roadmap-canary-prerequisite",
                "Reconcile the roadmap source prerequisite in the canary issue, then select real revision-matched model and delivery evidence without changing its rollback path.",
                HOLDS[repository][0]["issue"])
    if repository == "egohygiene/optiflow":
        return ("record-explicit-destination",
                "Record the repository-owned Pages origin and base path before selecting a public destination; retain the observed builder and producer ownership.", CAMPAIGN)
    state = row["repository_intelligence"]["state"]
    if state == "pages-composition-source-declared":
        return ("select-revision-matched-model-evidence",
                "Select actual model artifact identity, source revision, provenance and coverage; assess consumer composition, deployment and live bytes independently.", CAMPAIGN)
    if state == "artifact-or-preview-source-declared":
        return ("review-artifact-to-destination-handoff",
                "Review the existing artifact/preview builder and intended delivery profile; retain its pin and publisher until a bounded consumer change is reviewed.", CAMPAIGN)
    return ("review-repository-delivery-intent",
            "Review eligibility and the repository-owned delivery profile in the campaign, then select one bounded owner issue; missing declarations confer no exemption.", CAMPAIGN)


def destination(row):
    pages = row["declared_pages"]
    composed = row["repository_intelligence"]["state"] == "pages-composition-source-declared"
    origin, base = pages["origin"], pages["base_path"]
    url, derivation = None, "unavailable"
    if composed and origin is not None and base is not None:
        url, derivation = origin + base + "intelligence/", "explicit-origin-and-base-path-with-composed-route"
    elif composed and origin is not None and "/intelligence/" in pages.get("required_routes", []):
        url, derivation = origin + "/intelligence/", "explicit-origin-and-absolute-required-route"
    return {
        "state": pages["state"], "origin": origin, "base_path": base,
        "intelligence_url": url, "intelligence_url_basis": derivation,
        "declarations": deepcopy(pages["declarations"]),
        "cname_domains": deepcopy(pages["cname_domains"]),
        "explicit_base_paths": deepcopy(pages["explicit_base_paths"]),
        "required_routes": deepcopy(pages.get("required_routes", [])),
        "provider_configuration": "unknown", "publication": "unknown",
    }


def project(inventory_bytes, public_catalog_bytes, *, as_of):
    """Return the dated source-only ledger after exact public byte admission.

    A new as_of dates the projection, never refreshes the observations it contains.
    Every row remains unassessed for eligibility and unverified for delivery.
    """
    boundary = utc(as_of)
    catalog = admit(public_catalog_bytes, "public_roster")
    inventory = admit(inventory_bytes, "source_inventory")
    require(catalog["schema"] == "egohygiene.repository-public-catalog/v1"
            and inventory["schema"] == "egohygiene.organization-home-repository-source-inventory/v1"
            and inventory["visibility"] == "public")
    # Exact public artifact authentication precedes IDs, duplicates and joining.
    members = {r["full_name"]: r for r in catalog["repositories"] if r.get("visibility") == "public"}
    rows = inventory["repositories"]
    require(all(r.get("visibility") == "public" and r.get("repo") in members for r in rows))
    require(len(members) == len(catalog["repositories"]) == len(rows)
            and {r["repo"] for r in rows} == set(members))
    require(boundary >= utc(inventory["observed_at"]) and boundary >= utc(HOLD_OBSERVED_AT),
            "Projection time precedes captured evidence")
    result = []
    for row in sorted(rows, key=lambda item: item["repo"]):
        require(row["repository_id"] == members[row["repo"]]["repository_id"])
        require(utc(row["observed_at"]) <= boundary)
        code, instruction, issue = next_action(row)
        result.append({
            "repository": row["repo"], "repository_id": row["repository_id"], "visibility": "public",
            "eligibility": "unassessed",
            "source": {
                "state": row["state"], "observed_at": row["observed_at"],
                "revision": row["source_commit"], "urls": deepcopy(row["source_urls"]),
                "paths": deepcopy(row["inspection"]["source_paths"]), "gaps": deepcopy(row["gaps"]),
                "roadmap_content": "not-assessed", "decision_conformance": "not-assessed",
            },
            "builder": {
                "state": row["repository_intelligence"]["state"],
                "declarations": deepcopy(row["repository_intelligence"]["builders"]),
                "components": deepcopy(row["repository_intelligence"]["components"]),
                "pages_workflows": deepcopy(row["pages_workflows"]),
                "execution": "unknown",
            },
            "model_artifact": {"state": "unknown", "selection": None,
                               "reason": "No actual model artifact was selected in the source-only inventory."},
            "destination": destination(row),
            "live_verification": {"state": "unknown", "receipt": None,
                                  "reason": "No deployment or live-byte verification was performed for this checkpoint."},
            "refresh_owner": {"state": "unknown", "owner": None, "procedure": None,
                              "cadence": None, "evidence": None},
            "holds": deepcopy(HOLDS.get(row["repo"], [])),
            "next_action": {"state": "proposed", "code": code, "instruction": instruction},
            "next_issue": issue,
        })
    sources = deepcopy(INPUTS)
    sources["source_inventory"]["observed_at"] = inventory["observed_at"]
    sources["public_roster"]["observed_at"] = catalog["observed_at"]
    for source in sources.values():
        source["url"] = f"https://github.com/{source['repository']}/blob/{source['revision']}/{source['path']}"
    return {
        "schema": SCHEMA, "visibility": "public", "projection_as_of": as_of,
        "scope": {"kind": "fixed-reviewed-public-roster", "organization": "egohygiene",
                  "organization_total_claim": False},
        "source_inputs": sources,
        "coordination": {"adoption": CAMPAIGN, "roadmaps": ROADMAP_CAMPAIGN, "membership_and_policy": POLICY},
        "authority": {"canonical_membership": "egohygiene/hygiene", "adoption_projection": "egohygiene/pace",
                      "source_observation": "egohygiene/.github", "mutation": "none",
                      "eligibility_decisions": "none", "human_dispositions": "none"},
        "qualification": {"source": "captured-immutable-source", "projector_runtime": "not-qualified",
                          "tests": "not-run", "ci": "not-checked", "build": "not-run",
                          "provider": "not-checked", "live": "not-checked"},
        "repositories": result,
    }


def validate_ledger(value, inventory_bytes, public_catalog_bytes):
    """Require semantic identity with the source-only projection, not a status claim."""
    require(type(value) is dict and value.get("schema") == SCHEMA
            and value.get("visibility") == "public")
    require(value == project(inventory_bytes, public_catalog_bytes, as_of=value.get("projection_as_of")),
            "Ledger does not match the reviewed source-only projection")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("project", "verify"))
    parser.add_argument("--inventory", type=Path, default=ROOT / "vendor/intelligence-adoption/repositories.source.json")
    parser.add_argument("--public-catalog", type=Path, default=ROOT / "vendor/intelligence-adoption/public-repositories.json")
    parser.add_argument("--as-of", help="Explicit UTC projection time, YYYY-MM-DDTHH:MM:SSZ")
    parser.add_argument("--ledger", type=Path, help="Existing ledger to verify")
    parser.add_argument("--output", type=Path, help="New output file; existing paths are never overwritten")
    args = parser.parse_args(argv)
    if args.operation == "project" and (args.as_of is None or args.ledger is not None):
        parser.error("project requires --as-of and does not accept --ledger")
    if args.operation == "verify" and (args.ledger is None or args.as_of is not None or args.output is not None):
        parser.error("verify requires --ledger and accepts neither --as-of nor --output")
    try:
        inventory, catalog = read_file(args.inventory), read_file(args.public_catalog)
        if args.operation == "verify":
            validate_ledger(parse(read_file(args.ledger)), inventory, catalog)
            print("Source-only adoption projection matches its reviewed inputs; delivery remains unverified.")
        else:
            raw = canonical_bytes(project(inventory, catalog, as_of=args.as_of))
            if args.output is not None:
                with args.output.open("xb") as output:
                    output.write(raw)
            else:
                sys.stdout.buffer.write(raw)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print("Adoption projection unavailable: invalid, inaccessible or unreviewed input/output.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

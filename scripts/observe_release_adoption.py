#!/usr/bin/env python3
"""Observe release declarations in explicitly supplied pinned source captures."""
from __future__ import annotations

import argparse
import re
import sys
import tomllib

from observation_inputs import captured, instant, load_pinned, output, parse, portable

SCHEMA = "egohygiene.pace.release-adoption-observation/v1"


def authority(row, component):
    source = component.get("version_authority", {})
    if not isinstance(source, dict):
        return {"state": "invalid"}
    kind = source.get("kind")
    if kind == "external":
        return {"state": "external", "kind": kind}
    if kind not in {"package-json", "cargo-manifest", "pyproject-project", "catalog-record"}:
        return {"state": "unsupported"}
    path = source.get("path")
    if not portable(path):
        return {"state": "unknown", "kind": kind}
    file = captured(row, path)
    result = {"state": file["state"], "kind": kind, "path": path}
    if file["state"] != "present":
        return result
    try:
        if kind == "package-json":
            value = parse(file["text"])["version"]
        elif kind in {"cargo-manifest", "pyproject-project"}:
            value = tomllib.loads(file["text"])["package" if kind == "cargo-manifest" else "project"]["version"]
        elif kind == "catalog-record" and source.get("selector") == "artifacts[*].artifact_version":
            value = [artifact["artifact_version"] for artifact in parse(file["text"])["artifacts"]]
        else:
            return {**result, "state": "unsupported"}
        def version(v):
            return isinstance(v, str) and re.fullmatch(r"[0-9A-Za-z.+_-]{1,100}", v)
        if not (version(value) or (isinstance(value, list) and value and all(version(v) for v in value))):
            raise ValueError()
        return {**result, "state": "observed", "value": value, "sha256": file["sha256"]}
    except (ValueError, KeyError, TypeError):
        return {**result, "state": "invalid"}


def observe(snapshot, lock, *, as_of, max_age_days=30, audience="public"):
    age = (instant(as_of) - instant(snapshot["observed_at"])).total_seconds()
    if max_age_days < 0 or age < 0:
        raise ValueError("Invalid observation clock or age budget")
    rows = []
    for row in sorted(snapshot["repositories"], key=lambda item: item["repository"].casefold()):
        file = captured(row, ".egohygiene/release.json")
        result = {key: row[key] for key in ("repository", "revision", "visibility", "lifecycle")}
        result.update(declaration={"state": file["state"]}, profile="unknown",
                      changelog={"state": "unknown"}, components=[], channels=[],
                      tags=row.get("tags", {"current": None, "latest": None}),
                      conformance={"state": "unknown", "reason": "No authenticated validator evidence selected"},
                      drift={"state": "not-assessed"}, adoption="not-assessed",
                      migration="not-assessed", publication="not-assessed")
        if file["state"] == "present":
            try:
                declaration = parse(file["text"])
                if not isinstance(declaration, dict):
                    raise ValueError()
                profile = declaration["repository"]["release_profile"]
                if (not isinstance(profile, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", profile)
                        or not isinstance(declaration.get("schema_version"), str)
                        or not re.fullmatch(r"[a-z][a-z0-9.-]+/v[0-9]+", declaration["schema_version"])
                        or declaration.get("repository", {}).get("id") != row["repository"]):
                    raise ValueError()
                result["profile"] = profile
                result["declaration"] = {"state": "observed", "sha256": file["sha256"],
                                         "schema_version": declaration["schema_version"]}
                change_path = declaration.get("changelog", {}).get("path", "CHANGELOG.md")
                if not portable(change_path):
                    raise ValueError()
                change = captured(row, change_path)
                result["changelog"] = {"state": change["state"]}
                if change["state"] == "present":
                    result["changelog"] = {"state": "observed", "sha256": change["sha256"],
                        "unreleased_heading": bool(re.search(r"^## \[Unreleased\]\s*$", change["text"], re.MULTILINE))}
                result["components"] = [authority(row, component) for component in declaration.get("components", [])]
                for channel in declaration.get("delivery", {}).get("channels", []):
                    if (not isinstance(channel, dict) or not isinstance(channel.get("kind"), str)
                            or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", channel["kind"])
                            or channel.get("state") not in {"configured", "planned", "unavailable", "external", "not-applicable"}):
                        raise ValueError()
                    result["channels"].append({"kind": channel["kind"], "declared_state": channel["state"],
                                               "publication": "not-assessed"})
                if lock["target"]["authority"] == "accepted":
                    result["drift"] = {"state": "schema-matches" if declaration["schema_version"] ==
                                       lock["target"]["schema_version"] else "schema-differs"}
            except (ValueError, KeyError, TypeError, AttributeError):
                result.update(declaration={"state": "invalid", "sha256": file["sha256"]},
                              profile="unknown", changelog={"state": "unknown"}, components=[], channels=[])
        rows.append(result)
    return {"schema_version": SCHEMA, "audience": audience, "observed_at": snapshot["observed_at"],
            "evaluated_at": as_of, "freshness": "stale" if age > max_age_days * 86400 else "within-age-budget",
            "snapshot_sha256": lock["snapshot_sha256"], "target": lock["target"],
            "coverage": "Explicit supplied inventory only; not organization discovery",
            "qualification": "source-observation-only", "repositories": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--audience", choices=("public", "private"), default="public")
    parser.add_argument("--output", help="New output file; existing receipts are refused")
    args = parser.parse_args(argv)
    try:
        snapshot, lock = load_pinned(args.snapshot, args.lock, "release", audience=args.audience)
        output(observe(snapshot, lock, as_of=args.as_of, max_age_days=args.max_age_days,
                       audience=args.audience), args.output)
    except (OSError, ValueError, TypeError):
        print("Release observation rejected; check bounded pinned inputs and output policy.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

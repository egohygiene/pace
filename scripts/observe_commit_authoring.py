#!/usr/bin/env python3
"""Inventory supplied commit-authoring source captures without executing configs."""
from __future__ import annotations

import argparse
import re
import sys

from observation_inputs import captured, instant, load_pinned, output, parse

SCHEMA = "egohygiene.pace.commit-authoring-observation/v1"
GROUPS = {
    "commitlint": (".commitlintrc.json", ".commitlintrc", "commitlint.config.js", "commitlint.config.cjs", "commitlint.config.mjs", "commitlint.config.ts"),
    "commitizen": (".czrc", ".cz.json"),
    "hooks": ("lefthook.yml", "lefthook.yaml", ".lefthook.yml", ".lefthook.yaml", ".pre-commit-config.yaml"),
    "taskfile": ("Taskfile.yml", "Taskfile.yaml"),
    "pr_titles": (".github/workflows/pr-title.yml", ".github/workflows/pr-title.yaml", ".github/workflows/semantic-pr.yml"),
    "release": (".egohygiene/release.json", ".releaserc.json", "release.config.js", "release.config.cjs"),
}


def inventory(row, paths):
    files = [{"path": path, "state": captured(row, path)["state"],
              **({"sha256": captured(row, path)["sha256"]} if captured(row, path)["state"] == "present" else {})}
             for path in sorted(set(paths))]
    states = {file["state"] for file in files}
    state = "observed-unparsed" if "present" in states else "missing" if states == {"missing"} else "unknown"
    return {"state": state, "files": files}


def package(row):
    file = captured(row, "package.json")
    if file["state"] != "present":
        return {}, file["state"]
    try:
        value = parse(file["text"])
        if not isinstance(value, dict):
            raise ValueError()
        return value, "observed"
    except (TypeError, ValueError):
        return {}, "invalid"


def adapters(row, manifest):
    values = []
    try:
        for path in GROUPS["commitizen"]:
            file = captured(row, path)
            if file["state"] == "present":
                values.append(parse(file["text"])["path"])
        embedded = manifest.get("config", {}).get("commitizen", {})
        if embedded:
            values.append(embedded["path"])
        if not all(isinstance(value, str) and re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", value) for value in values):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        return {"state": "invalid", "adapters": []}
    return {"state": "conflicting" if len(set(values)) > 1 else "observed" if values else "unknown",
            "adapters": sorted(set(values))}


def observe(snapshot, lock, *, as_of, audience="public", max_age_days=30):
    age = (instant(as_of) - instant(snapshot["observed_at"])).total_seconds()
    if max_age_days < 0 or age < 0:
        raise ValueError("Invalid observation clock or age budget")
    rows = []
    for row in sorted(snapshot["repositories"], key=lambda item: item["repository"].casefold()):
        scopes = {name: inventory(row, paths) for name, paths in GROUPS.items()}
        # Preserve additional captured hooks/workflows rather than assuming one
        # filename exhausts an unknown repository's configuration.
        scopes["hooks"] = inventory(row, [*GROUPS["hooks"], *[path for path in row["files"] if path.startswith((".husky/", ".githooks/", "hooks/"))]])
        scopes["workflow_sources"] = inventory(row, [path for path in row["files"] if path.startswith(".github/workflows/")])
        manifest, package_state = package(row)
        scripts = manifest.get("scripts", {})
        script_names = sorted(key for key in scripts if re.fullmatch(r"[a-zA-Z0-9:_-]+", key)) if isinstance(scripts, dict) else []
        scopes["package_scripts"] = {"state": package_state, "names": script_names}
        scopes["commitizen"]["configuration"] = adapters(row, manifest)
        result = {key: row[key] for key in ("repository", "revision", "visibility", "lifecycle")}
        result.update(scopes=scopes, merge_policy=row.get("merge_policy", {"state": "unknown"}),
                      compatibility="not-assessed", adoption="not-assessed", enforcement="not-assessed",
                      next_action="Review captured sources against an accepted pinned contract and validator before proposing changes")
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
        snapshot, lock = load_pinned(args.snapshot, args.lock, "commit-authoring", audience=args.audience)
        output(observe(snapshot, lock, as_of=args.as_of, audience=args.audience, max_age_days=args.max_age_days), args.output)
    except (OSError, ValueError, TypeError):
        print("Commit-authoring observation rejected; check bounded pinned inputs and output policy.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

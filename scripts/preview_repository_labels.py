#!/usr/bin/env python3
"""Replay the Aether label pilot through pinned Relay; never contact a provider."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts/label-rollout-pilot.v1.lock.json"
LIMIT = 2_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def load(path):
    raw = path.read_bytes()
    require(len(raw) <= LIMIT, "Input exceeds limit")
    def invalid(_):
        raise ValueError("Non-finite JSON number")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def git(source, *args):
    return subprocess.run(["git", "-C", str(source), *args], capture_output=True,
                          check=True, timeout=30).stdout


def validate_observation(value, repository):
    require(set(value) == {"schema", "kind", "repository", "observed_at", "finished_at", "coverage", "configuration", "labels"}, "Unknown observation shape")
    require(value["schema"] == "egohygiene.pace.label-pilot-observation/v1" and value["kind"] == "github-public", "Unknown observation contract")
    identity = value["repository"]
    require(set(identity) == {"name", "id", "visibility"} and identity["name"] == repository
            and identity["visibility"] == "public" and type(identity["id"]) is int and identity["id"] > 0, "Repository mismatch")
    for key in ("observed_at", "finished_at"):
        require(value[key].endswith("Z"), "Expected UTC observation timestamp")
    require(datetime.fromisoformat(value["finished_at"].replace("Z", "+00:00")) >=
            datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00")), "Reversed observation interval")
    coverage = value["coverage"]
    require(set(coverage) == {"status", "per_page", "pages", "error"}, "Unknown coverage shape")
    require(coverage["status"] == "complete" and coverage["error"] is None
            and coverage["per_page"] == 100, "Complete label coverage required")
    pages = coverage["pages"]
    require(1 <= len(pages) <= 20 and [p["number"] for p in pages] == list(range(1, len(pages) + 1)), "Invalid page sequence")
    for page in pages:
        require(set(page) == {"number", "records", "response_sha256"} and type(page["records"]) is int
                and 0 <= page["records"] <= 100 and re.fullmatch(r"[0-9a-f]{64}", page["response_sha256"]), "Invalid page evidence")
    require(pages[-1]["records"] < 100 and all(p["records"] == 100 for p in pages[:-1]), "Terminal page missing")
    labels = value["labels"]
    require(sum(p["records"] for p in pages) == len(labels), "Coverage count mismatch")
    require(len({row["id"] for row in labels}) == len(labels), "Duplicate label ID")
    for row in labels:
        require(set(row) == {"id", "name", "color", "description"} and type(row["id"]) is int
                and row["id"] > 0, "Invalid label identity")
    config = value["configuration"]
    require(set(config) == {"path", "status", "source_revision", "directory_response_sha256"}
            and config["path"] == ".github/relay-labels.json" and config["status"] == "absent"
            and re.fullmatch(r"[0-9a-f]{40}", config["source_revision"])
            and re.fullmatch(r"[0-9a-f]{64}", config["directory_response_sha256"]), "Pilot requires evidenced absent configuration; configured consumers need a reviewed extension")


def preview(source, observation_path):
    lock = load(LOCK)
    require(lock["mode"] == "observe" and lock["status"] == "proposed"
            and lock["repository"] == "egohygiene/aether", "Unsupported pilot selection")
    observation = load(observation_path)
    validate_observation(observation, lock["repository"])
    pin = lock["relay"]
    tree = git(source, "rev-parse", pin["revision"] + "^{tree}").decode().strip()
    require(tree == pin["tree"], "Relay tree mismatch")
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        selected = {}
        for path, digest in pin["files"].items():
            raw = git(source, "show", f"{pin['revision']}:{path}")
            require(sha(raw) == digest, "Relay source digest mismatch")
            target = temporary / Path(path).name
            target.write_bytes(raw)
            selected[path] = target
        script = selected["actions/repository-labels/scripts/repository_labels.py"]
        spec = importlib.util.spec_from_file_location("pinned_relay_labels", script)
        relay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(relay)
        upstream = lock["organization"]
        paths = {}
        for name, entry in upstream["files"].items():
            path = ROOT / entry["local_path"]
            require(sha(path.read_bytes()) == entry["sha256"], "Organization source digest mismatch")
            paths[name] = path
        native_lock_path = selected["actions/repository-labels/contracts/organization-labels.lock.json"]
        catalog_path = paths[".github/labels/catalog.v1.json"]
        assignments_path = paths[".github/labels/repositories.v1.json"]
        native_lock, catalog, assignments = relay.validate_contract(native_lock_path, catalog_path, assignments_path)
        require(native_lock["revision"] == upstream["revision"] and native_lock["repository"] == upstream["repository"], "Organization selection mismatch")
        observed = relay.normalize_observed_labels(observation["labels"])
        observed_path = temporary / "observed.json"
        observed_path.write_bytes(encoded(observed))
        assignment = [row for row in assignments["repositories"] if row["repository"] == lock["repository"]]
        require(len(assignment) <= 1, "Ambiguous canonical assignment")
        native_plan = None
        diagnostics = []
        try:
            native_plan = relay.plan_sync(argparse.Namespace(repository=lock["repository"], lock=native_lock_path,
                catalog=catalog_path, assignments=assignments_path, config=temporary / "absent-config.json",
                observed_labels=observed_path))
            relay.verify_plan(native_plan, relay.SYNC_PLAN_SCHEMA)
        except relay.ContractError:
            # Only the known enrollment gap is a valid blocked pilot, never a synthetic success.
            require(not assignment, "Pinned Relay refused enrolled repository planning")
            diagnostics.append("CANONICAL_ASSIGNMENT_MISSING")
        universal = [relay.validate_label(row, "catalog universal label") for row in catalog["universal"]]
        observed_map = {row["name"]: row for row in observed}
        advisory = {"advisory_only": True, "scope": "universal catalog only; not an enrolled repository plan",
                    "create": [], "update": [], "unchanged": []}
        for row in sorted(universal, key=lambda item: item["name"]):
            before = observed_map.get(row["name"])
            if before is None:
                advisory["create"].append(row)
            elif before != row:
                advisory["update"].append({"before": before, "after": row})
            else:
                advisory["unchanged"].append(row)
        return {
            "schema": "egohygiene.pace.label-pilot-preview/v1", "mode": "observe", "provider_writes": "forbidden",
            "status": "blocked" if diagnostics else "ready-for-review", "diagnostics": diagnostics,
            "repository": observation["repository"], "observed_at": observation["observed_at"],
            "finished_at": observation["finished_at"], "coverage": observation["coverage"],
            "configuration": observation["configuration"], "canonical_assignment": assignment[0] if assignment else None,
            "native_sync_plan": native_plan, "universal_preview": advisory,
            "preserved_observed_labels": observed,
            "summary": {"observed": len(observed), "missing_universal": len(advisory["create"]),
                        "drifted_universal": len(advisory["update"]), "current_universal": len(advisory["unchanged"]),
                        "proposed_deletions": 0, "proposed_renames": 0},
            "provenance": {"pilot_lock_sha256": sha(LOCK.read_bytes()), "adapter_sha256": sha(Path(__file__).read_bytes()),
                           "observation_sha256": sha(observation_path.read_bytes()), "selection": lock},
            "next": "Review canonical Aether enrollment and overlays in .github, then repin Relay and regenerate; separate label application and issue classification remain required.",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--relay", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = preview(args.relay, args.observation)
        payload = encoded(result)
        require(len(payload) <= LIMIT, "Output exceeds limit")
        # Exclusive creation preserves existing evidence and rejects destination symlinks.
        require(not any(part.is_symlink() for part in [args.output, *args.output.parents]), "Symlink output denied")
        with args.output.open("xb") as handle:
            handle.write(payload)
        print(json.dumps({"status": result["status"], "summary": result["summary"], "provider_writes": "forbidden"}))
        return 2 if result["status"] == "blocked" else 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError):
        print("Label pilot refused invalid, unavailable or unsafe input/output; no provider writes.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

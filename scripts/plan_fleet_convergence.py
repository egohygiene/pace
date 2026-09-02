#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Plan reviewed fleet convergence and open one bounded pull request at a time."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from validate_lock import load_lock, validate_lock

MANIFEST_SCHEMA = "egohygiene.pace.fleet-convergence-manifest/v1"
PLAN_SCHEMA = "egohygiene.pace.fleet-convergence-plan/v1"
REVIEW_SCHEMA = "egohygiene.pace.fleet-convergence-review/v1"
PROPOSAL_SCHEMA = "egohygiene.pace.upgrade-pull-request/v1"
CATALOG_SCHEMA_VERSION = "1.0.0"
FOUNDATION_MANIFEST_VERSION = "1.0.0"
OBSERVATORY_SCHEMA = "egohygiene.observatory.organization-health/v1"
OBSERVATORY_VERSION = "1.0.0-alpha.1"
HOLON_PLAN_SCHEMA = "holon.materialization-plan/v1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[a-z0-9][a-z0-9.-]*/(?:\.github|[a-z0-9][a-z0-9.-]*)$")
UNIT_RE = re.compile(r"^upgrade:[a-z0-9_.-]+/[a-z0-9_.-]+:[0-9a-f]{12}$")
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
MUTATING_HOLON_ACTIONS = {"create", "update", "delete"}
MANIFEST_POLICY = {
    "unknown_state": "block",
    "update_mode": "reviewed-pull-request",
    "unit": "repository",
    "partial_adoption": True,
}


class ContractError(ValueError):
    """Raised when an input crosses a closed contract boundary."""


class DuplicateKeyError(ValueError):
    """Raised when strict JSON input repeats a key."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object
    )
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest(value: object) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _require_keys(value: object, keys: set[str], location: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{location} must be an object")
    missing = keys - set(value)
    unknown = set(value) - keys
    if missing:
        raise ContractError(f"{location} is missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ContractError(
            f"{location} has unknown keys: {', '.join(sorted(unknown))}"
        )
    return value


def _timestamp(value: object, location: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{location} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ContractError(f"{location} must be an RFC 3339 UTC timestamp") from error
    return parsed


def _unique_sorted_strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and value == sorted(set(value))
    )


def _relative_path(value: object, location: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or "//" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or ".git" in value.split("/")
    ):
        raise ContractError(f"{location} must be a normalized relative path")
    return value


def _branch(value: object, location: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", value)
        or value.startswith(("/", "."))
        or value.endswith(("/", ".", ".lock"))
        or "//" in value
        or ".." in value
        or "@{" in value
    ):
        raise ContractError(f"{location} is not a safe Git branch name")
    return value


def _resolve_input(directory: Path, value: object, location: str) -> Path:
    relative = _relative_path(value, location)
    resolved = (directory / relative).resolve()
    try:
        resolved.relative_to(directory.resolve())
    except ValueError as error:
        raise ContractError(f"{location} escapes the manifest directory") from error
    if not resolved.is_file():
        raise ContractError(f"{location} does not identify a readable file: {relative}")
    return resolved


def _validate_fleet_manifest(document: object) -> list[dict[str, Any]]:
    root = _require_keys(
        document,
        {"$schema", "schema", "organization", "policy", "repositories"},
        "fleet manifest",
    )
    if root["schema"] != MANIFEST_SCHEMA:
        raise ContractError(f"fleet manifest.schema must be {MANIFEST_SCHEMA}")
    if root["organization"] != "egohygiene":
        raise ContractError("fleet manifest.organization must be egohygiene")
    if root["policy"] != MANIFEST_POLICY:
        raise ContractError(
            "fleet manifest.policy does not preserve the review boundary"
        )
    repositories = root["repositories"]
    if not isinstance(repositories, list) or not repositories:
        raise ContractError("fleet manifest.repositories must be a non-empty array")
    expected = {
        "repository",
        "foundation_manifest",
        "current_lock",
        "desired_lock",
        "holon_plan",
        "lock_path",
        "default_branch",
        "depends_on",
        "state",
    }
    normalized: list[dict[str, Any]] = []
    names: list[str] = []
    for index, raw in enumerate(repositories):
        item = dict(_require_keys(raw, expected, f"repositories[{index}]"))
        repository = item["repository"]
        if (
            not isinstance(repository, str)
            or REPOSITORY_RE.fullmatch(repository) is None
        ):
            raise ContractError(f"repositories[{index}].repository is invalid")
        names.append(repository)
        for field in ("foundation_manifest", "desired_lock", "lock_path"):
            _relative_path(item[field], f"repositories[{index}].{field}")
        for field in ("current_lock", "holon_plan"):
            if item[field] is not None:
                _relative_path(item[field], f"repositories[{index}].{field}")
        _branch(item["default_branch"], f"repositories[{index}].default_branch")
        dependencies = item["depends_on"]
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) and REPOSITORY_RE.fullmatch(dependency)
            for dependency in dependencies
        ):
            raise ContractError(f"repositories[{index}].depends_on is invalid")
        if dependencies != sorted(set(dependencies)):
            raise ContractError(
                f"repositories[{index}].depends_on must be unique and sorted"
            )
        if repository in dependencies:
            raise ContractError(f"repositories[{index}] cannot depend on itself")
        if item["state"] not in {"active", "paused"}:
            raise ContractError(f"repositories[{index}].state must be active or paused")
        normalized.append(item)
    if names != sorted(set(names)):
        raise ContractError("fleet manifest repositories must be unique and sorted")
    known = set(names)
    for item in normalized:
        missing = set(item["depends_on"]) - known
        if missing:
            raise ContractError(
                f"{item['repository']} depends on unmanaged repositories: {', '.join(sorted(missing))}"
            )
    _topological_repositories(normalized)
    return normalized


def _topological_repositories(records: Sequence[Mapping[str, Any]]) -> list[str]:
    dependencies = {item["repository"]: set(item["depends_on"]) for item in records}
    ordered: list[str] = []
    ready = sorted(name for name, values in dependencies.items() if not values)
    while ready:
        name = ready.pop(0)
        ordered.append(name)
        for candidate in sorted(dependencies):
            if name in dependencies[candidate]:
                dependencies[candidate].remove(name)
                if (
                    not dependencies[candidate]
                    and candidate not in ordered
                    and candidate not in ready
                ):
                    ready.append(candidate)
                    ready.sort()
    if len(ordered) != len(records):
        cycle = sorted(name for name, values in dependencies.items() if values)
        raise ContractError(f"fleet manifest dependency cycle: {', '.join(cycle)}")
    return ordered


def _catalog_records(catalog: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(catalog, dict):
        raise ContractError("catalog must be an object")
    if catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ContractError("catalog schema_version is unsupported")
    if catalog.get("organization") != "egohygiene":
        raise ContractError("catalog organization must be egohygiene")
    repositories = catalog.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ContractError("catalog.repositories must be a non-empty array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(repositories):
        if not isinstance(item, dict):
            raise ContractError(f"catalog.repositories[{index}] must be an object")
        name = item.get("full_name")
        if not isinstance(name, str) or REPOSITORY_RE.fullmatch(name) is None:
            raise ContractError(f"catalog.repositories[{index}].full_name is invalid")
        if name in result:
            raise ContractError(f"catalog contains duplicate repository {name}")
        result[name] = item
    declared_count = catalog.get("repository_count")
    if declared_count != len(repositories):
        raise ContractError("catalog.repository_count does not match repositories")
    return result


def _observation_records(
    observation: object, catalog_path: Path
) -> tuple[Mapping[str, Any], dict[str, Mapping[str, Any]]]:
    if not isinstance(observation, dict):
        raise ContractError("Observatory snapshot must be an object")
    if observation.get("schema") != OBSERVATORY_SCHEMA:
        raise ContractError(f"Observatory snapshot schema must be {OBSERVATORY_SCHEMA}")
    if observation.get("contract_version") != OBSERVATORY_VERSION:
        raise ContractError(
            f"Observatory contract must be pinned to {OBSERVATORY_VERSION}"
        )
    if observation.get("organization") != "egohygiene":
        raise ContractError("Observatory organization must be egohygiene")
    snapshot_id = observation.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not re.fullmatch(
        r"organization-health:sha256:[0-9a-f]{64}", snapshot_id
    ):
        raise ContractError("Observatory snapshot_id is invalid")
    _timestamp(observation.get("as_of"), "Observatory as_of")
    sources = observation.get("sources")
    if not isinstance(sources, dict) or not isinstance(sources.get("catalog"), dict):
        raise ContractError("Observatory catalog provenance is missing")
    if sources["catalog"].get("sha256") != file_digest(catalog_path):
        raise ContractError(
            "Observatory snapshot does not represent the supplied catalog bytes"
        )
    repositories = observation.get("repositories")
    if not isinstance(repositories, list):
        raise ContractError("Observatory repositories must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(repositories):
        if not isinstance(item, dict) or not isinstance(item.get("repository"), dict):
            raise ContractError(f"Observatory repositories[{index}] is malformed")
        name = item["repository"].get("full_name")
        if not isinstance(name, str) or REPOSITORY_RE.fullmatch(name) is None:
            raise ContractError(
                f"Observatory repositories[{index}] has an invalid name"
            )
        if name in result:
            raise ContractError(f"Observatory snapshot repeats repository {name}")
        result[name] = item
    return observation, result


def _validate_foundation_manifest(document: object, repository: str) -> None:
    if not isinstance(document, dict):
        raise ContractError(f"{repository} foundation manifest must be an object")
    if document.get("schema_version") != FOUNDATION_MANIFEST_VERSION:
        raise ContractError(f"{repository} foundation manifest version is unsupported")
    if document.get("repository") != repository:
        raise ContractError(f"{repository} foundation manifest identity does not match")
    pins = document.get("pins")
    if not isinstance(pins, dict) or not all(
        isinstance(pins.get(key), str) and pins[key].strip()
        for key in ("architecture", "foundation")
    ):
        raise ContractError(
            f"{repository} foundation manifest lacks immutable core pins"
        )


def _as_of(observation: Mapping[str, Any]) -> datetime:
    return _timestamp(observation["as_of"], "Observatory as_of")


def _lock_errors(document: object, observation: Mapping[str, Any]) -> list[str]:
    return validate_lock(document, _as_of(observation))


def _ownership_errors(document: Mapping[str, Any], repository: str) -> list[str]:
    errors: list[str] = []
    for item in document.get("locks", []):
        if isinstance(item, dict) and item.get("target", {}).get("owner") != repository:
            errors.append(f"lock {item.get('id')} target owner is not {repository}")
    return errors


def _change_risk(
    before: object, after: object, change_type: str
) -> tuple[str, list[str]]:
    if change_type == "remove":
        return "high", ["removes a dependency and its recorded rollback state"]
    if change_type == "add":
        return "medium", ["adopts a new dependency and target ownership record"]
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ContractError(
            "updated lock entries must contain before and after objects"
        )
    reasons: list[str] = []
    risk = "low"
    if before.get("target") != after.get("target"):
        risk = "high"
        reasons.append("changes target path or ownership")
    before_contract = before.get("compatibility", {}).get("contract")
    after_contract = after.get("compatibility", {}).get("contract")
    if before_contract != after_contract:
        risk = "high"
        reasons.append("changes the compatibility contract")
    if before.get("exception") != after.get("exception"):
        risk = max((risk, "medium"), key=RISK_ORDER.get)
        reasons.append("changes a bounded exception")
    if before.get("source") != after.get("source"):
        risk = max((risk, "medium"), key=RISK_ORDER.get)
        reasons.append("changes immutable source provenance")
    if before.get("compatibility") != after.get("compatibility") and not reasons:
        risk = "medium"
        reasons.append("changes migration or rollback declarations")
    if not reasons:
        reasons.append("changes dependency metadata")
    return risk, reasons


def _lock_changes(
    current: Mapping[str, Any], desired: Mapping[str, Any]
) -> list[dict[str, Any]]:
    before_by_id = {item["id"]: item for item in current.get("locks", [])}
    after_by_id = {item["id"]: item for item in desired.get("locks", [])}
    changes: list[dict[str, Any]] = []
    if current.get("policy") != desired.get("policy"):
        changes.append(
            {
                "id": "lock-policy",
                "type": "update",
                "kind": "policy",
                "risk": "medium",
                "reasons": ["changes fleet update, exception, or rollback policy"],
                "before": current.get("policy"),
                "after": desired.get("policy"),
            }
        )
    for identifier in sorted(set(before_by_id) | set(after_by_id)):
        before = before_by_id.get(identifier)
        after = after_by_id.get(identifier)
        if before == after:
            continue
        if before is None:
            change_type = "add"
        elif after is None:
            change_type = "remove"
        else:
            change_type = "update"
        risk, reasons = _change_risk(before, after, change_type)
        changes.append(
            {
                "id": identifier,
                "type": change_type,
                "kind": (after or before)["kind"],
                "risk": risk,
                "reasons": reasons,
                "before": before,
                "after": after,
            }
        )
    return changes


def _plan_without_digest(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in plan.items() if key != "plan_digest"}


def _holon_operations(
    document: Mapping[str, Any], repository: str
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if document.get("schema_version") != HOLON_PLAN_SCHEMA:
        errors.append("Holon plan schema is unsupported")
    if document.get("repository") != repository:
        errors.append("Holon plan repository does not match")
    operations = document.get("operations")
    if not isinstance(operations, list):
        return [], errors + ["Holon plan operations are missing"]
    payload = {key: value for key, value in document.items() if key != "plan_id"}
    if document.get("plan_id") != digest(payload):
        errors.append("Holon plan_id does not match its canonical payload")
    normalized: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            errors.append(f"Holon operation {index} is malformed")
            continue
        action = operation.get("action")
        path = operation.get("path")
        if action == "conflict":
            errors.append(f"Holon reports a conflict at {path}")
        if action in MUTATING_HOLON_ACTIONS:
            try:
                _relative_path(path, f"Holon operation {index}.path")
            except ContractError as error:
                errors.append(str(error))
                continue
            normalized.append(dict(operation))
    return normalized, errors


def _generated_targets(changes: Sequence[Mapping[str, Any]]) -> set[str]:
    targets: set[str] = set()
    for change in changes:
        for side in (change.get("before"), change.get("after")):
            if (
                isinstance(side, dict)
                and side.get("target", {}).get("management") == "generated"
            ):
                targets.add(side["target"]["path"])
    return targets


def build_plan(
    manifest_path: Path, catalog_path: Path, observation_path: Path
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    fleet_records = _validate_fleet_manifest(manifest)
    catalog = load_json(catalog_path)
    catalog_records = _catalog_records(catalog)
    observation, observation_records = _observation_records(
        load_json(observation_path), catalog_path
    )
    if set(catalog_records) != set(observation_records):
        raise ContractError("Observatory and Hygiene repository membership differ")

    manifest_directory = manifest_path.resolve().parent
    records_by_name = {item["repository"]: item for item in fleet_records}
    order = _topological_repositories(fleet_records)
    units_by_repository: dict[str, dict[str, Any]] = {}

    for repository in order:
        configured = records_by_name[repository]
        if repository not in catalog_records:
            raise ContractError(f"{repository} is absent from the Hygiene catalog")
        foundation_path = _resolve_input(
            manifest_directory,
            configured["foundation_manifest"],
            f"{repository}.foundation_manifest",
        )
        desired_path = _resolve_input(
            manifest_directory, configured["desired_lock"], f"{repository}.desired_lock"
        )
        current_path = None
        if configured["current_lock"] is not None:
            current_path = _resolve_input(
                manifest_directory,
                configured["current_lock"],
                f"{repository}.current_lock",
            )
        holon_path = None
        if configured["holon_plan"] is not None:
            holon_path = _resolve_input(
                manifest_directory, configured["holon_plan"], f"{repository}.holon_plan"
            )

        foundation = load_json(foundation_path)
        _validate_foundation_manifest(foundation, repository)
        desired = load_lock(desired_path)
        if desired.get("repository") != repository:
            raise ContractError(f"{repository} desired lock identity does not match")
        desired_errors = _lock_errors(desired, observation) + _ownership_errors(
            desired, repository
        )
        if desired_errors:
            raise ContractError(
                f"{repository} desired lock is not adoptable: {'; '.join(desired_errors)}"
            )
        current: dict[str, Any] = {
            "$schema": desired["$schema"],
            "schema": desired["schema"],
            "repository": repository,
            "policy": desired["policy"],
            "locks": [],
        }
        current_errors: list[str] = []
        if current_path is not None:
            current = load_lock(current_path)
            if current.get("repository") != repository:
                raise ContractError(
                    f"{repository} current lock identity does not match"
                )
            current_errors = _lock_errors(current, observation) + _ownership_errors(
                current, repository
            )

        changes = _lock_changes(current, desired)
        blockers = list(current_errors)
        observed = observation_records[repository]
        evidence = observed.get("evidence")
        if not isinstance(evidence, dict):
            blockers.append("Observatory repository evidence is malformed")
            represented_commit = None
        else:
            freshness = evidence.get("freshness")
            commits = evidence.get("represented_commits")
            if freshness != "current":
                blockers.append(
                    f"Observatory evidence freshness is {freshness or 'unknown'}"
                )
            if (
                not isinstance(commits, list)
                or len(commits) != 1
                or not isinstance(commits[0], str)
                or COMMIT_RE.fullmatch(commits[0]) is None
            ):
                blockers.append(
                    "Observatory must identify exactly one represented commit"
                )
                represented_commit = None
            else:
                represented_commit = commits[0]

        holon_plan = None
        holon_operations: list[dict[str, Any]] = []
        if holon_path is not None:
            holon_plan = load_json(holon_path)
            holon_operations, holon_errors = _holon_operations(holon_plan, repository)
            blockers.extend(holon_errors)
        generated = _generated_targets(changes)
        operation_paths = {operation["path"] for operation in holon_operations}
        coverage_paths = set(operation_paths)
        if holon_plan is not None:
            for operation in holon_plan.get("operations", []):
                if not isinstance(operation, dict):
                    continue
                if operation.get("action") == "noop":
                    coverage_paths.add(operation.get("path"))
                if (
                    operation.get("action") == "preserve"
                    and operation.get("path") in generated
                ):
                    blockers.append(
                        f"Holon preserves generated lock target: {operation.get('path')}"
                    )
        if generated and holon_plan is None:
            blockers.append(
                "generated-target drift requires an exact Holon materialization plan"
            )
        missing_operations = generated - coverage_paths
        if missing_operations:
            blockers.append(
                "Holon plan does not cover generated targets: "
                + ", ".join(sorted(missing_operations))
            )
        extra_operations = operation_paths - generated
        if extra_operations:
            blockers.append(
                "Holon plan mutates paths outside lock drift: "
                + ", ".join(sorted(extra_operations))
            )

        risk = max(
            (change["risk"] for change in changes),
            key=RISK_ORDER.get,
            default="low",
        )
        unit_seed = {
            "repository": repository,
            "current_lock": digest(current),
            "desired_lock": digest(desired),
            "represented_commit": represented_commit,
        }
        unit_id = f"upgrade:{repository}:{digest(unit_seed)[:12]}"
        if not changes:
            disposition = "no_change"
        elif configured["state"] == "paused":
            disposition = "paused"
        elif blockers:
            disposition = "blocked"
        else:
            disposition = "ready_for_review"
        units_by_repository[repository] = {
            "unit_id": unit_id,
            "order": len(units_by_repository) + 1,
            "repository": repository,
            "default_branch": configured["default_branch"],
            "represented_commit": represented_commit,
            "catalog": {
                "lifecycle": catalog_records[repository].get("lifecycle"),
                "maturity": catalog_records[repository].get("maturity"),
                "visibility": catalog_records[repository].get("visibility"),
            },
            "disposition": disposition,
            "risk": risk,
            "blockers": sorted(set(blockers)),
            "depends_on_repositories": configured["depends_on"],
            "depends_on": [],
            "lock_path": configured["lock_path"],
            "changes": changes,
            "sources": {
                "foundation_manifest_sha256": digest(foundation),
                "current_lock_sha256": digest(current),
                "desired_lock_sha256": digest(desired),
                "holon_plan_sha256": digest(holon_plan) if holon_plan else None,
            },
            "foundation_manifest": foundation,
            "current_lock_present": current_path is not None,
            "current_lock": current,
            "desired_lock": desired,
            "holon_plan": holon_plan,
            "holon_operations": holon_operations,
        }

    units = [units_by_repository[name] for name in order]
    for unit in units:
        unit["depends_on"] = [
            units_by_repository[name]["unit_id"]
            for name in unit.pop("depends_on_repositories")
            if units_by_repository[name]["disposition"] != "no_change"
        ]
    counts = Counter(unit["disposition"] for unit in units)
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "sources": {
            "fleet_manifest_sha256": digest(manifest),
            "catalog_sha256": file_digest(catalog_path),
            "observatory_snapshot_id": observation["snapshot_id"],
            "observatory_snapshot_sha256": digest(observation),
            "observatory_as_of": observation["as_of"],
        },
        "policy": MANIFEST_POLICY,
        "review": {
            "required_before_pull_request": True,
            "approved": False,
            "review_record": None,
        },
        "summary": {
            "catalog_repositories": len(catalog_records),
            "managed_repositories": len(units),
            "unmanaged_repositories": sorted(
                set(catalog_records) - set(records_by_name)
            ),
            "dispositions": dict(sorted(counts.items())),
            "risk": dict(sorted(Counter(unit["risk"] for unit in units).items())),
        },
        "units": units,
    }
    plan["plan_digest"] = digest(_plan_without_digest(plan))
    return plan


def validate_plan(plan: object) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    errors: list[str] = []
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append(f"plan.schema must be {PLAN_SCHEMA}")
    if plan.get("policy") != MANIFEST_POLICY:
        errors.append("plan policy changed")
    if plan.get("plan_digest") != digest(_plan_without_digest(plan)):
        errors.append("plan_digest does not match the canonical plan")
    review = plan.get("review")
    if review != {
        "required_before_pull_request": True,
        "approved": False,
        "review_record": None,
    }:
        errors.append("plan does not preserve the unreviewed boundary")
    units = plan.get("units")
    if not isinstance(units, list):
        return errors + ["plan.units must be an array"]
    ids: set[str] = set()
    repositories: set[str] = set()
    prior: set[str] = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            errors.append(f"units[{index}] must be an object")
            continue
        identifier = unit.get("unit_id")
        repository = unit.get("repository")
        if not isinstance(identifier, str) or UNIT_RE.fullmatch(identifier) is None:
            errors.append(f"units[{index}].unit_id is invalid")
        elif identifier in ids:
            errors.append(f"duplicate unit_id: {identifier}")
        else:
            ids.add(identifier)
        if (
            not isinstance(repository, str)
            or REPOSITORY_RE.fullmatch(repository) is None
        ):
            errors.append(f"units[{index}].repository is invalid")
        elif repository in repositories:
            errors.append(f"duplicate unit repository: {repository}")
        else:
            repositories.add(repository)
        dependencies = unit.get("depends_on")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            errors.append(f"units[{index}].depends_on must be an array of unit IDs")
        elif any(item not in prior for item in dependencies):
            errors.append(f"units[{index}] dependencies are not in plan order")
        if unit.get("order") != index + 1:
            errors.append(f"units[{index}].order is not deterministic")
        sources = unit.get("sources")
        if not isinstance(sources, dict):
            errors.append(f"units[{index}].sources must be an object")
        else:
            source_bindings = (
                ("foundation_manifest_sha256", "foundation_manifest"),
                ("current_lock_sha256", "current_lock"),
                ("desired_lock_sha256", "desired_lock"),
            )
            for source_key, document_key in source_bindings:
                if sources.get(source_key) != digest(unit.get(document_key)):
                    errors.append(
                        f"units[{index}].{source_key} does not match embedded input"
                    )
            expected_holon_digest = (
                digest(unit.get("holon_plan"))
                if unit.get("holon_plan") is not None
                else None
            )
            if sources.get("holon_plan_sha256") != expected_holon_digest:
                errors.append(
                    f"units[{index}].holon_plan_sha256 does not match embedded input"
                )
            seed = {
                "repository": repository,
                "current_lock": sources.get("current_lock_sha256"),
                "desired_lock": sources.get("desired_lock_sha256"),
                "represented_commit": unit.get("represented_commit"),
            }
            expected_id = f"upgrade:{repository}:{digest(seed)[:12]}"
            if identifier != expected_id:
                errors.append(f"units[{index}].unit_id does not bind its inputs")
        current = unit.get("current_lock")
        desired = unit.get("desired_lock")
        if not isinstance(unit.get("current_lock_present"), bool):
            errors.append(f"units[{index}].current_lock_present must be boolean")
        if isinstance(current, dict) and isinstance(desired, dict):
            try:
                expected_changes = _lock_changes(current, desired)
            except (AttributeError, KeyError, TypeError):
                expected_changes = []
                errors.append(f"units[{index}] embedded locks are malformed")
            if unit.get("changes") != expected_changes:
                errors.append(f"units[{index}].changes do not match lock drift")
            expected_risk = max(
                (change["risk"] for change in expected_changes),
                key=RISK_ORDER.get,
                default="low",
            )
            if unit.get("risk") != expected_risk:
                errors.append(f"units[{index}].risk does not match explained drift")
            disposition = unit.get("disposition")
            if not expected_changes and disposition != "no_change":
                errors.append(f"units[{index}] without drift must be no_change")
            if expected_changes and disposition == "no_change":
                errors.append(f"units[{index}] with drift cannot be no_change")
        else:
            errors.append(f"units[{index}] must embed current and desired locks")
        holon_plan = unit.get("holon_plan")
        if holon_plan is None:
            expected_operations: list[dict[str, Any]] = []
        elif isinstance(holon_plan, dict) and isinstance(repository, str):
            expected_operations, holon_errors = _holon_operations(
                holon_plan, repository
            )
            errors.extend(f"units[{index}]: {error}" for error in holon_errors)
        else:
            expected_operations = []
            errors.append(f"units[{index}].holon_plan is malformed")
        if unit.get("holon_operations") != expected_operations:
            errors.append(
                f"units[{index}].holon_operations do not match the Holon plan"
            )
        if isinstance(identifier, str):
            prior.add(identifier)
    return errors


def validate_review(review: object, plan: Mapping[str, Any]) -> list[str]:
    if not isinstance(review, dict):
        return ["review must be an object"]
    errors: list[str] = []
    expected = {
        "schema",
        "plan_digest",
        "reviewer",
        "reviewed_at",
        "decision",
        "approved_units",
        "completed_units",
    }
    if set(review) != expected:
        errors.append("review contains unsupported or missing fields")
    if review.get("schema") != REVIEW_SCHEMA:
        errors.append(f"review.schema must be {REVIEW_SCHEMA}")
    if review.get("plan_digest") != plan.get("plan_digest"):
        errors.append("review does not authorize this exact plan digest")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        errors.append("reviewer is required")
    try:
        _timestamp(review.get("reviewed_at"), "review.reviewed_at")
    except ContractError as error:
        errors.append(str(error))
    if review.get("decision") != "approved":
        errors.append("review decision must be approved")
    plan_units = plan.get("units")
    if not isinstance(plan_units, list):
        plan_units = []
    unit_ids = {
        unit.get("unit_id")
        for unit in plan_units
        if isinstance(unit, dict) and isinstance(unit.get("unit_id"), str)
    }
    for field in ("approved_units", "completed_units"):
        values = review.get(field)
        if not _unique_sorted_strings(values):
            errors.append(f"review.{field} must be a unique sorted array")
        elif not set(values) <= unit_ids:
            errors.append(f"review.{field} contains an unknown unit")
    return errors


def _proposal_without_digest(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in proposal.items() if key != "proposal_digest"}


def _single_line(value: object) -> str:
    return " ".join(str(value).split()).replace("`", "'")


def build_proposal(
    plan: dict[str, Any], review: dict[str, Any], unit_id: str
) -> dict[str, Any]:
    errors = validate_plan(plan) + validate_review(review, plan)
    if errors:
        raise ContractError("pull-request proposal refused: " + "; ".join(errors))
    units = {
        item.get("unit_id"): item
        for item in plan.get("units", [])
        if isinstance(item, dict)
    }
    unit = units.get(unit_id)
    if unit is None:
        errors.append(f"unit is absent from the reviewed plan: {unit_id}")
    else:
        if unit["disposition"] != "ready_for_review":
            errors.append(f"unit is {unit['disposition']}, not ready_for_review")
        if unit_id not in review.get("approved_units", []):
            errors.append("review does not approve this unit")
        missing_dependencies = set(unit["depends_on"]) - set(
            review.get("completed_units", [])
        )
        if missing_dependencies:
            errors.append(
                "unit dependencies are incomplete: "
                + ", ".join(sorted(missing_dependencies))
            )
    if errors:
        raise ContractError("pull-request proposal refused: " + "; ".join(errors))
    if unit is None:  # pragma: no cover - guarded by the refusal above
        raise ContractError("reviewed unit disappeared during proposal construction")

    expected_changes: list[dict[str, Any]] = [
        {
            "path": unit["lock_path"],
            "action": "upsert",
            "verification": "exact-json",
            "desired_sha256": unit["sources"]["desired_lock_sha256"],
            "previous_sha256": (
                unit["sources"]["current_lock_sha256"]
                if unit["current_lock_present"]
                else None
            ),
        }
    ]
    for operation in unit["holon_operations"]:
        expected_changes.append(
            {
                "path": operation["path"],
                "action": "delete" if operation["action"] == "delete" else "upsert",
                "verification": "sha256",
                "desired_sha256": operation["desired_sha256"],
                "previous_sha256": operation["previous_sha256"],
            }
        )
    if unit["holon_operations"]:
        expected_changes.append(
            {
                "path": ".holon/materialization-state.v1.json",
                "action": "upsert",
                "verification": "holon-state",
                "desired_sha256": None,
                "previous_sha256": None,
            }
        )
    expected_changes.sort(key=lambda item: item["path"])
    branch_slug = re.sub(
        r"[^a-z0-9-]+", "-", unit["repository"].split("/", 1)[1]
    ).strip("-")
    branch = f"pace/{branch_slug}-{plan['plan_digest'][:12]}"
    change_lines = [
        f"- `{change['id']}`: {change['type']} {change['kind']} ({change['risk']} risk)"
        for change in unit["changes"]
    ]
    body = "\n".join(
        [
            f"Converges `{unit['repository']}` through reviewed Pace unit `{unit_id}`.",
            "",
            "## Explainable drift",
            "",
            *change_lines,
            "",
            "## Safety boundary",
            "",
            f"- Plan: `{plan['plan_digest']}`",
            f"- Reviewed by: `{_single_line(review['reviewer'])}` at `{review['reviewed_at']}`",
            f"- Base commit: `{unit['represented_commit']}`",
            "- Retry is idempotent on the proposal branch and candidate tree.",
            "- Rollback restores the previous lock and uses Holon's recorded prior bytes for generated targets.",
            "",
            f"Closes no issue automatically. Planned from egohygiene/pace#{2}.",
        ]
    )
    proposal: dict[str, Any] = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": f"pull-request:{digest({'plan': plan['plan_digest'], 'unit': unit_id})}",
        "plan_digest": plan["plan_digest"],
        "review": review,
        "unit_id": unit_id,
        "repository": unit["repository"],
        "base_branch": unit["default_branch"],
        "base_commit": unit["represented_commit"],
        "head_branch": branch,
        "title": f"chore(pace): converge {unit['repository'].split('/', 1)[1]}",
        "body": body,
        "risk": unit["risk"],
        "changes": unit["changes"],
        "depends_on": unit["depends_on"],
        "lock_path": unit["lock_path"],
        "expected_candidate_changes": expected_changes,
        "desired_lock": unit["desired_lock"],
        "holon_plan": unit["holon_plan"],
        "rollback": {
            "mode": "new-reviewed-convergence-plan",
            "previous_lock_present": unit["current_lock_present"],
            "previous_lock": unit["current_lock"],
            "holon_plan_id": unit["holon_plan"].get("plan_id")
            if unit["holon_plan"]
            else None,
            "force": False,
        },
        "controls": {
            "pause": "set the fleet manifest unit state to paused and regenerate the plan",
            "retry": "reuse this exact proposal; a different candidate tree is refused",
            "partial_adoption": "only units named by review.approved_units may be proposed",
        },
    }
    proposal["proposal_digest"] = digest(_proposal_without_digest(proposal))
    return proposal


def validate_proposal(proposal: object) -> list[str]:
    if not isinstance(proposal, dict):
        return ["proposal must be an object"]
    errors: list[str] = []
    if proposal.get("schema") != PROPOSAL_SCHEMA:
        errors.append(f"proposal.schema must be {PROPOSAL_SCHEMA}")
    if proposal.get("proposal_digest") != digest(_proposal_without_digest(proposal)):
        errors.append("proposal_digest does not match the canonical proposal")
    if (
        not isinstance(proposal.get("base_commit"), str)
        or COMMIT_RE.fullmatch(proposal["base_commit"]) is None
    ):
        errors.append("proposal.base_commit is invalid")
    try:
        _branch(proposal.get("base_branch"), "proposal.base_branch")
        _branch(proposal.get("head_branch"), "proposal.head_branch")
    except ContractError as error:
        errors.append(str(error))
    review = proposal.get("review")
    if not isinstance(review, dict):
        errors.append("proposal.review must be an object")
    else:
        review_keys = {
            "schema",
            "plan_digest",
            "reviewer",
            "reviewed_at",
            "decision",
            "approved_units",
            "completed_units",
        }
        if set(review) != review_keys:
            errors.append("proposal review contains unsupported or missing fields")
        if (
            review.get("schema") != REVIEW_SCHEMA
            or review.get("decision") != "approved"
        ):
            errors.append("proposal does not contain an approved convergence review")
        if (
            not isinstance(review.get("reviewer"), str)
            or not review["reviewer"].strip()
        ):
            errors.append("proposal review requires a reviewer")
        if review.get("plan_digest") != proposal.get("plan_digest"):
            errors.append("proposal review does not bind the plan digest")
        approved_units = review.get("approved_units")
        completed_units = review.get("completed_units")
        if not _unique_sorted_strings(approved_units):
            errors.append(
                "proposal review approved_units must be a unique sorted array"
            )
            approved_units = []
        if not _unique_sorted_strings(completed_units):
            errors.append(
                "proposal review completed_units must be a unique sorted array"
            )
            completed_units = []
        if proposal.get("unit_id") not in approved_units:
            errors.append("proposal unit is not approved by the embedded review")
        dependencies = proposal.get("depends_on")
        if not _unique_sorted_strings(dependencies):
            errors.append("proposal.depends_on must be a unique sorted array")
        elif not set(dependencies) <= set(completed_units):
            errors.append("proposal has incomplete dependencies")
        try:
            _timestamp(review.get("reviewed_at"), "proposal.review.reviewed_at")
        except ContractError as error:
            errors.append(str(error))
    unit_id = proposal.get("unit_id")
    repository = proposal.get("repository")
    expected_proposal_id = (
        f"pull-request:{digest({'plan': proposal.get('plan_digest'), 'unit': unit_id})}"
    )
    if proposal.get("proposal_id") != expected_proposal_id:
        errors.append("proposal_id does not bind the plan and unit")
    if isinstance(repository, str) and REPOSITORY_RE.fullmatch(repository):
        seed = {
            "repository": repository,
            "current_lock": digest(proposal.get("rollback", {}).get("previous_lock")),
            "desired_lock": digest(proposal.get("desired_lock")),
            "represented_commit": proposal.get("base_commit"),
        }
        if unit_id != f"upgrade:{repository}:{digest(seed)[:12]}":
            errors.append("proposal unit_id does not bind its lock and base inputs")
        branch_slug = re.sub(r"[^a-z0-9-]+", "-", repository.split("/", 1)[1]).strip(
            "-"
        )
        if (
            proposal.get("head_branch")
            != f"pace/{branch_slug}-{str(proposal.get('plan_digest'))[:12]}"
        ):
            errors.append("proposal head branch is not deterministic")
    else:
        errors.append("proposal.repository is invalid")
    current_lock = proposal.get("rollback", {}).get("previous_lock")
    if not isinstance(proposal.get("rollback", {}).get("previous_lock_present"), bool):
        errors.append("proposal rollback must record whether the prior lock existed")
    desired_lock = proposal.get("desired_lock")
    if isinstance(current_lock, dict) and isinstance(desired_lock, dict):
        try:
            expected_drift = _lock_changes(current_lock, desired_lock)
        except (AttributeError, KeyError, TypeError):
            expected_drift = []
            errors.append("proposal embedded locks are malformed")
        if proposal.get("changes") != expected_drift:
            errors.append("proposal changes do not match embedded lock drift")
        expected_risk = max(
            (change["risk"] for change in expected_drift),
            key=RISK_ORDER.get,
            default="low",
        )
        if proposal.get("risk") != expected_risk:
            errors.append("proposal risk does not match embedded lock drift")
    else:
        errors.append("proposal must embed current and desired locks")
    changes = proposal.get("expected_candidate_changes")
    if not isinstance(changes, list) or not changes:
        errors.append("proposal.expected_candidate_changes must be non-empty")
    elif [item.get("path") for item in changes if isinstance(item, dict)] != sorted(
        item.get("path") for item in changes if isinstance(item, dict)
    ):
        errors.append("proposal expected changes must be sorted")
    elif isinstance(current_lock, dict) and isinstance(desired_lock, dict):
        try:
            lock_path = _relative_path(proposal.get("lock_path"), "proposal.lock_path")
        except ContractError as error:
            errors.append(str(error))
            lock_path = proposal.get("lock_path")
        expected_changes: list[dict[str, Any]] = [
            {
                "path": lock_path,
                "action": "upsert",
                "verification": "exact-json",
                "desired_sha256": digest(desired_lock),
                "previous_sha256": (
                    digest(current_lock)
                    if proposal.get("rollback", {}).get("previous_lock_present")
                    else None
                ),
            }
        ]
        holon_plan = proposal.get("holon_plan")
        holon_operations: list[dict[str, Any]] = []
        if holon_plan is not None:
            if isinstance(holon_plan, dict) and isinstance(repository, str):
                holon_operations, holon_errors = _holon_operations(
                    holon_plan, repository
                )
                errors.extend(holon_errors)
            else:
                errors.append("proposal.holon_plan is malformed")
        for operation in holon_operations:
            expected_changes.append(
                {
                    "path": operation["path"],
                    "action": "delete" if operation["action"] == "delete" else "upsert",
                    "verification": "sha256",
                    "desired_sha256": operation["desired_sha256"],
                    "previous_sha256": operation["previous_sha256"],
                }
            )
        if holon_operations:
            expected_changes.append(
                {
                    "path": ".holon/materialization-state.v1.json",
                    "action": "upsert",
                    "verification": "holon-state",
                    "desired_sha256": None,
                    "previous_sha256": None,
                }
            )
        expected_changes.sort(key=lambda item: str(item["path"]))
        if changes != expected_changes:
            errors.append(
                "proposal expected changes do not match its lock and Holon inputs"
            )
        for index, item in enumerate(changes):
            if not isinstance(item, dict):
                errors.append(f"proposal expected change {index} is malformed")
                continue
            try:
                _relative_path(
                    item.get("path"), f"proposal expected change {index}.path"
                )
            except ContractError as error:
                errors.append(str(error))
    return errors


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise ContractError("git is required to verify a candidate tree")
    return executable


def _git(arguments: Sequence[str], directory: Path) -> str:
    result = subprocess.run(
        [_git_executable(), *arguments],
        cwd=directory,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ContractError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _candidate_changes(directory: Path) -> dict[str, str]:
    tracked = subprocess.run(
        [
            _git_executable(),
            "diff",
            "HEAD",
            "--name-status",
            "--no-renames",
            "-z",
        ],
        cwd=directory,
        check=False,
        capture_output=True,
    )
    if tracked.returncode != 0:
        raise ContractError(tracked.stderr.decode("utf-8", errors="replace").strip())
    fields = tracked.stdout.decode("utf-8").split("\0")
    changes: dict[str, str] = {}
    index = 0
    while index + 1 < len(fields) and fields[index]:
        status = fields[index]
        path = fields[index + 1]
        index += 2
        if status not in {"A", "M", "D"}:
            raise ContractError(f"unsupported candidate Git status {status}: {path}")
        changes[path] = status
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z"], directory)
    for path in filter(None, untracked.split("\0")):
        changes[path] = "A"
    return changes


def _base_blob(directory: Path, path: str) -> bytes | None:
    result = subprocess.run(
        [_git_executable(), "cat-file", "blob", f"HEAD:{path}"],
        cwd=directory,
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout
    return None


def _verify_candidate(proposal: Mapping[str, Any], directory: Path) -> dict[str, str]:
    if _git(["rev-parse", "--show-toplevel"], directory) != str(directory.resolve()):
        raise ContractError("candidate tree must be the Git worktree root")
    if _git(["rev-parse", "HEAD"], directory) != proposal["base_commit"]:
        raise ContractError(
            "candidate tree HEAD does not match the reviewed base commit"
        )
    actual = _candidate_changes(directory)
    expected = {item["path"]: item for item in proposal["expected_candidate_changes"]}
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise ContractError(
            "candidate tree differs from the reviewed boundary: " + "; ".join(details)
        )
    for path, specification in expected.items():
        target = directory / path
        previous = _base_blob(directory, path)
        previous_sha256 = specification["previous_sha256"]
        if (
            specification["verification"] != "holon-state"
            and previous_sha256 is None
            and previous is not None
        ):
            raise ContractError(f"reviewed base unexpectedly contains {path}")
        if (
            specification["verification"] != "holon-state"
            and previous_sha256 is not None
        ):
            if previous is None:
                raise ContractError(f"reviewed base is missing {path}")
            if specification["verification"] == "exact-json":
                try:
                    previous_document = json.loads(
                        previous.decode("utf-8"), object_pairs_hook=_strict_object
                    )
                except (UnicodeError, json.JSONDecodeError, DuplicateKeyError) as error:
                    raise ContractError(
                        f"reviewed base lock is not strict JSON: {path}"
                    ) from error
                actual_previous_sha256 = digest(previous_document)
            else:
                actual_previous_sha256 = hashlib.sha256(previous).hexdigest()
            if actual_previous_sha256 != previous_sha256:
                raise ContractError(f"reviewed base digest does not match {path}")
        if specification["action"] == "delete":
            if actual[path] != "D" or target.exists():
                raise ContractError(f"candidate must delete {path}")
            continue
        if actual[path] == "D" or not target.is_file() or target.is_symlink():
            raise ContractError(f"candidate must contain a regular file at {path}")
        if specification["verification"] == "exact-json":
            if load_json(target) != proposal["desired_lock"]:
                raise ContractError(
                    f"candidate lock does not match the reviewed desired lock: {path}"
                )
        elif specification["verification"] == "sha256":
            if file_digest(target) != specification["desired_sha256"]:
                raise ContractError(
                    f"candidate digest does not match the Holon plan: {path}"
                )
        elif specification["verification"] == "holon-state":
            state = load_json(target)
            if state.get("schema_version") != "holon.materialization-state/v1":
                raise ContractError("candidate Holon state schema is unsupported")
            if state.get("plan_id") != proposal["rollback"]["holon_plan_id"]:
                raise ContractError(
                    "candidate Holon state does not match the reviewed plan"
                )
    return actual


class GitHubClient:
    """Small GitHub REST adapter used only after exact plan review."""

    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        parsed = urlparse(api_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ContractError(
                "GitHub API URL must be an HTTPS origin without user info"
            )
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(
        self, method: str, path: str, payload: object | None = None
    ) -> tuple[int, Any]:
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.api_url + path,
            method=method,
            data=data,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "egohygiene-pace",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except HTTPError as error:
            body = error.read()
            value = json.loads(body) if body else None
            return error.code, value


def _mode(directory: Path, path: str, status: str) -> str:
    if status != "A":
        entry = _git(["ls-files", "--stage", "--", path], directory)
        if entry:
            return entry.split()[0]
    return "100755" if os.access(directory / path, os.X_OK) else "100644"


def open_pull_request(
    proposal: dict[str, Any], candidate: Path, client: GitHubClient
) -> dict[str, Any]:
    errors = validate_proposal(proposal)
    if errors:
        raise ContractError("invalid proposal: " + "; ".join(errors))
    changes = _verify_candidate(proposal, candidate)
    repository = proposal["repository"]
    prefix = f"/repos/{repository}"
    status, base_ref = client.request(
        "GET", f"{prefix}/git/ref/heads/{proposal['base_branch']}"
    )
    if status != 200 or not isinstance(base_ref, dict):
        raise ContractError("could not read the target base branch")
    if base_ref.get("object", {}).get("sha") != proposal["base_commit"]:
        raise ContractError(
            "target base branch advanced; collect Observatory state and re-plan"
        )
    status, base_commit = client.request(
        "GET", f"{prefix}/git/commits/{proposal['base_commit']}"
    )
    if status != 200 or not isinstance(base_commit, dict):
        raise ContractError("could not read the target base commit")
    tree_entries: list[dict[str, Any]] = []
    for path in sorted(changes):
        if changes[path] == "D":
            tree_entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": None}
            )
            continue
        content = base64.b64encode((candidate / path).read_bytes()).decode("ascii")
        status, blob = client.request(
            "POST", f"{prefix}/git/blobs", {"content": content, "encoding": "base64"}
        )
        if status != 201 or not isinstance(blob, dict) or not blob.get("sha"):
            raise ContractError(f"GitHub refused candidate blob {path}")
        tree_entries.append(
            {
                "path": path,
                "mode": _mode(candidate, path, changes[path]),
                "type": "blob",
                "sha": blob["sha"],
            }
        )
    status, tree = client.request(
        "POST",
        f"{prefix}/git/trees",
        {"base_tree": base_commit["tree"]["sha"], "tree": tree_entries},
    )
    if status != 201 or not isinstance(tree, dict) or not tree.get("sha"):
        raise ContractError("GitHub refused the bounded candidate tree")

    status, existing_ref = client.request(
        "GET", f"{prefix}/git/ref/heads/{proposal['head_branch']}"
    )
    commit_sha: str
    if status == 200 and isinstance(existing_ref, dict):
        commit_sha = existing_ref.get("object", {}).get("sha", "")
        check_status, existing_commit = client.request(
            "GET", f"{prefix}/git/commits/{commit_sha}"
        )
        if (
            check_status != 200
            or not isinstance(existing_commit, dict)
            or existing_commit.get("tree", {}).get("sha") != tree["sha"]
            or [parent.get("sha") for parent in existing_commit.get("parents", [])]
            != [proposal["base_commit"]]
        ):
            raise ContractError(
                "proposal branch exists with a different candidate tree"
            )
    elif status == 404:
        identity = {
            "name": "Ego Hygiene Pace",
            "email": "pace@users.noreply.github.com",
            "date": proposal["review"]["reviewed_at"],
        }
        commit_status, commit = client.request(
            "POST",
            f"{prefix}/git/commits",
            {
                "message": proposal["title"],
                "tree": tree["sha"],
                "parents": [proposal["base_commit"]],
                "author": identity,
                "committer": identity,
            },
        )
        if (
            commit_status != 201
            or not isinstance(commit, dict)
            or not commit.get("sha")
        ):
            raise ContractError("GitHub refused the reviewed candidate commit")
        commit_sha = commit["sha"]
        ref_status, _ = client.request(
            "POST",
            f"{prefix}/git/refs",
            {"ref": f"refs/heads/{proposal['head_branch']}", "sha": commit_sha},
        )
        if ref_status != 201:
            raise ContractError("GitHub refused the proposal branch")
    else:
        raise ContractError("could not inspect the proposal branch")

    query = urlencode(
        {
            "state": "open",
            "head": f"{repository.split('/', 1)[0]}:{proposal['head_branch']}",
            "base": proposal["base_branch"],
        }
    )
    status, pulls = client.request("GET", f"{prefix}/pulls?{query}")
    if status != 200 or not isinstance(pulls, list):
        raise ContractError("could not inspect existing pull requests")
    if pulls:
        pull = pulls[0]
    else:
        status, pull = client.request(
            "POST",
            f"{prefix}/pulls",
            {
                "title": proposal["title"],
                "head": proposal["head_branch"],
                "base": proposal["base_branch"],
                "body": proposal["body"],
                "maintainer_can_modify": True,
            },
        )
        if status != 201 or not isinstance(pull, dict):
            raise ContractError("GitHub refused the bounded pull request")
    return {
        "repository": repository,
        "number": pull.get("number"),
        "url": pull.get("html_url"),
        "head_branch": proposal["head_branch"],
        "commit": commit_sha,
        "proposal_digest": proposal["proposal_digest"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="generate a no-write fleet plan")
    plan.add_argument("--manifest", type=Path, required=True)
    plan.add_argument("--catalog", type=Path, required=True)
    plan.add_argument("--observatory", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify-plan", help="verify a generated plan")
    verify.add_argument("--plan", type=Path, required=True)

    propose = subparsers.add_parser("propose", help="prepare one reviewed PR request")
    propose.add_argument("--plan", type=Path, required=True)
    propose.add_argument("--review", type=Path, required=True)
    propose.add_argument("--unit", required=True)
    propose.add_argument("--output", type=Path, required=True)

    open_pr = subparsers.add_parser("open-pr", help="open exactly one reviewed PR")
    open_pr.add_argument("--proposal", type=Path, required=True)
    open_pr.add_argument("--candidate", type=Path, required=True)
    open_pr.add_argument("--token-env", default="GITHUB_TOKEN")
    open_pr.add_argument("--api-url", default="https://api.github.com")
    open_pr.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "plan":
            plan = build_plan(
                arguments.manifest, arguments.catalog, arguments.observatory
            )
            write_json(arguments.output, plan)
            print(
                f"WROTE no-write convergence plan {arguments.output} ({plan['plan_digest']})"
            )
            return 0
        if arguments.command == "verify-plan":
            errors = validate_plan(load_json(arguments.plan))
            if errors:
                raise ContractError("; ".join(errors))
            print(f"VALID convergence plan {arguments.plan}")
            return 0
        if arguments.command == "propose":
            proposal = build_proposal(
                load_json(arguments.plan), load_json(arguments.review), arguments.unit
            )
            write_json(arguments.output, proposal)
            print(f"WROTE one-unit pull-request proposal {arguments.output}")
            return 0
        if arguments.command == "open-pr":
            token = os.environ.get(arguments.token_env)
            if not token:
                raise ContractError(
                    f"token environment variable is unset: {arguments.token_env}"
                )
            proposal = load_json(arguments.proposal)
            result = open_pull_request(
                proposal,
                arguments.candidate.resolve(),
                GitHubClient(token, arguments.api_url),
            )
            if arguments.output:
                write_json(arguments.output, result)
            print(f"OPENED pull request {result['url']}")
            return 0
    except (
        ContractError,
        DuplicateKeyError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

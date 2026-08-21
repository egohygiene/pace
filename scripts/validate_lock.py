#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Validate a Pace v1 lock independently of any updater or network service."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

LOCK_SCHEMA = "egohygiene.pace.lock/v1"
LOCK_SCHEMA_FILE = "pace-lock-v1.schema.json"
LOCK_KINDS = {"foundation", "aether", "workflow", "container", "site", "schema"}
REFERENCE_TYPES = {"git-commit", "oci-digest", "content-digest"}
MIGRATIONS = {"not-required", "required", "completed"}
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXCEPTION_ID = re.compile(r"^EXC-[0-9]{4}-[0-9]{3,}$")
SHA_1 = re.compile(r"^[0-9a-f]{40}$")
SHA_256 = re.compile(r"^[0-9a-f]{64}$")
DIGEST_REFERENCE = re.compile(r"^sha256:[0-9a-f]{64}$")
CONTRACT = re.compile(r"^[A-Za-z0-9._/-]+/v([1-9][0-9]*)$")
LOCATOR = re.compile(r"^(?:https|oci)://[^\s]+$")
HTTPS_URL = re.compile(r"^https://[^\s]+$")
UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)

ROOT_KEYS = {"$schema", "schema", "repository", "policy", "locks"}
POLICY_KEYS = {"unknown_contract", "update_mode", "max_exception_days", "rollback"}
LOCK_KEYS = {"id", "kind", "source", "target", "compatibility", "exception"}
SOURCE_KEYS = {"owner", "locator", "version", "reference_type", "reference", "digest"}
DIGEST_KEYS = {"algorithm", "value"}
TARGET_KEYS = {"path", "management", "owner", "generator"}
COMPATIBILITY_KEYS = {"contract", "accepted_major", "migration", "rollback"}
EXCEPTION_KEYS = {
    "id",
    "reason",
    "approved_by",
    "issued_at",
    "expires_at",
    "tracking_url",
}


class DuplicateKeyError(ValueError):
    """Raised when JSON repeats an object key."""


def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Construct a JSON object while refusing ambiguous duplicate keys."""

    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_lock(path: Path) -> dict[str, Any]:
    """Load one UTF-8 lock object without resolving sources or targets."""

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=object_without_duplicates,
    )
    if not isinstance(value, dict):
        raise ValueError("lock document must be a JSON object")
    return value


def parse_timestamp(value: Any, label: str, errors: list[str]) -> datetime | None:
    """Parse one canonical UTC timestamp into an aware datetime."""

    if not isinstance(value, str) or UTC_TIMESTAMP.fullmatch(value) is None:
        errors.append(f"{label} must be an RFC 3339 UTC timestamp ending in Z")
        return None
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        errors.append(f"{label} is not a valid RFC 3339 timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        errors.append(f"{label} must use UTC")
        return None
    return parsed


def require_object(value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    """Return a typed object or append one validation error."""

    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    return value


def require_closed_keys(
    value: dict[str, Any], expected: set[str], label: str, errors: list[str]
) -> None:
    """Reject missing and unknown keys at a closed contract boundary."""

    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        errors.append(f"{label} is missing keys: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label} has unknown keys: {', '.join(unknown)}")


def valid_repository(value: Any) -> bool:
    """Return whether a value is an owner/repository identifier."""

    return isinstance(value, str) and REPOSITORY.fullmatch(value) is not None


def valid_target_path(value: Any) -> bool:
    """Return whether a target is one normalized repository-relative path."""

    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or "\\" in value
        or "\x00" in value
    ):
        return False
    parts = value.split("/")
    return bool(parts) and all(part not in {".", ".."} for part in parts)


def validate_source(source: Any, label: str, errors: list[str]) -> None:
    """Validate immutable source identity and content provenance."""

    value = require_object(source, label, errors)
    if value is None:
        return
    require_closed_keys(value, SOURCE_KEYS, label, errors)
    if not valid_repository(value.get("owner")):
        errors.append(f"{label}.owner must be an owner/repository identifier")
    locator = value.get("locator")
    if not isinstance(locator, str) or LOCATOR.fullmatch(locator) is None:
        errors.append(f"{label}.locator must use https:// or oci://")
    if not isinstance(value.get("version"), str) or not value["version"].strip():
        errors.append(f"{label}.version must be non-empty")
    reference_type = value.get("reference_type")
    reference = value.get("reference")
    if reference_type not in REFERENCE_TYPES:
        errors.append(f"{label}.reference_type is unsupported: {reference_type}")
    elif reference_type == "git-commit":
        if not isinstance(reference, str) or SHA_1.fullmatch(reference) is None:
            errors.append(f"{label}.reference must be a full lowercase Git commit SHA")
    elif not isinstance(reference, str) or DIGEST_REFERENCE.fullmatch(reference) is None:
        errors.append(f"{label}.reference must be a lowercase sha256 digest reference")

    digest = require_object(value.get("digest"), f"{label}.digest", errors)
    if digest is None:
        return
    require_closed_keys(digest, DIGEST_KEYS, f"{label}.digest", errors)
    if digest.get("algorithm") != "sha256":
        errors.append(f"{label}.digest.algorithm must be sha256")
    digest_value = digest.get("value")
    if not isinstance(digest_value, str) or SHA_256.fullmatch(digest_value) is None:
        errors.append(f"{label}.digest.value must be 64 lowercase hexadecimal characters")
    if reference_type in {"oci-digest", "content-digest"} and isinstance(reference, str):
        if reference.removeprefix("sha256:") != digest_value:
            errors.append(f"{label}.reference and digest.value must agree")


def validate_target(target: Any, compatibility: Any, label: str, errors: list[str]) -> str | None:
    """Validate target path, generated ownership, and rollback coupling."""

    value = require_object(target, label, errors)
    if value is None:
        return None
    require_closed_keys(value, TARGET_KEYS, label, errors)
    path = value.get("path")
    if not valid_target_path(path):
        errors.append(f"{label}.path must be a normalized repository-relative path")
        path = None
    if not valid_repository(value.get("owner")):
        errors.append(f"{label}.owner must be an owner/repository identifier")
    management = value.get("management")
    generator = value.get("generator")
    if management == "generated":
        if not valid_repository(generator):
            errors.append(f"{label}.generator is required for generated targets")
        expected_rollback = "restore-lock-and-generated-targets"
    elif management == "consumer-owned":
        if generator is not None:
            errors.append(f"{label}.generator must be null for consumer-owned targets")
        expected_rollback = "restore-lock-only"
    else:
        errors.append(f"{label}.management is unsupported: {management}")
        expected_rollback = None
    if isinstance(compatibility, dict) and expected_rollback is not None:
        if compatibility.get("rollback") != expected_rollback:
            errors.append(
                f"{label} management requires compatibility.rollback={expected_rollback}"
            )
    return path if isinstance(path, str) else None


def validate_compatibility(value: Any, label: str, errors: list[str]) -> None:
    """Validate the compatibility, migration, and rollback declaration."""

    compatibility = require_object(value, label, errors)
    if compatibility is None:
        return
    require_closed_keys(compatibility, COMPATIBILITY_KEYS, label, errors)
    contract = compatibility.get("contract")
    match = CONTRACT.fullmatch(contract) if isinstance(contract, str) else None
    if match is None:
        errors.append(f"{label}.contract must end with an explicit /vMAJOR")
    accepted_major = compatibility.get("accepted_major")
    if (
        isinstance(accepted_major, bool)
        or not isinstance(accepted_major, int)
        or accepted_major < 1
    ):
        errors.append(f"{label}.accepted_major must be a positive integer")
    elif match is not None and int(match.group(1)) != accepted_major:
        errors.append(f"{label}.accepted_major must match the contract major")
    migration = compatibility.get("migration")
    if migration not in MIGRATIONS:
        errors.append(f"{label}.migration is unsupported: {migration}")
    elif migration == "required":
        errors.append(f"{label}.migration remains required; the lock is not adoptable")
    if compatibility.get("rollback") not in {
        "restore-lock-only",
        "restore-lock-and-generated-targets",
    }:
        errors.append(f"{label}.rollback is unsupported")


def validate_exception(
    value: Any,
    label: str,
    as_of: datetime,
    max_days: int | None,
    errors: list[str],
) -> None:
    """Validate one bounded, approved, non-expired exception."""

    if value is None:
        return
    exception = require_object(value, label, errors)
    if exception is None:
        return
    require_closed_keys(exception, EXCEPTION_KEYS, label, errors)
    identifier = exception.get("id")
    if not isinstance(identifier, str) or EXCEPTION_ID.fullmatch(identifier) is None:
        errors.append(f"{label}.id must use EXC-YYYY-NNN format")
    for field in ("reason", "approved_by"):
        if not isinstance(exception.get(field), str) or not exception[field].strip():
            errors.append(f"{label}.{field} must be non-empty")
    tracking = exception.get("tracking_url")
    if not isinstance(tracking, str) or HTTPS_URL.fullmatch(tracking) is None:
        errors.append(f"{label}.tracking_url must use https://")
    issued = parse_timestamp(exception.get("issued_at"), f"{label}.issued_at", errors)
    expires = parse_timestamp(exception.get("expires_at"), f"{label}.expires_at", errors)
    if issued is None or expires is None:
        return
    if expires <= issued:
        errors.append(f"{label}.expires_at must be later than issued_at")
    elif max_days is not None and (expires - issued).total_seconds() > max_days * 86400:
        errors.append(f"{label} exceeds policy.max_exception_days")
    if as_of < issued:
        errors.append(f"{label} is not active yet at the validation instant")
    if as_of >= expires:
        errors.append(f"{label} expired at {exception['expires_at']}")


def validate_lock(document: Any, as_of: datetime) -> list[str]:
    """Return every v1 lock violation without mutating state or using a network."""

    errors: list[str] = []
    root = require_object(document, "lock document", errors)
    if root is None:
        return errors
    require_closed_keys(root, ROOT_KEYS, "lock document", errors)
    schema_path = root.get("$schema")
    if not isinstance(schema_path, str) or not (
        schema_path == LOCK_SCHEMA_FILE or schema_path.endswith(f"/{LOCK_SCHEMA_FILE}")
    ):
        errors.append(f"lock document.$schema must reference {LOCK_SCHEMA_FILE}")
    if root.get("schema") != LOCK_SCHEMA:
        errors.append(f"lock document.schema must be {LOCK_SCHEMA}")
    if not valid_repository(root.get("repository")):
        errors.append("lock document.repository must be an owner/repository identifier")

    policy = require_object(root.get("policy"), "lock document.policy", errors)
    max_days: int | None = None
    if policy is not None:
        require_closed_keys(policy, POLICY_KEYS, "lock document.policy", errors)
        if policy.get("unknown_contract") != "fail-closed":
            errors.append("lock document.policy.unknown_contract must be fail-closed")
        if policy.get("update_mode") != "reviewed-pull-request":
            errors.append("lock document.policy.update_mode must be reviewed-pull-request")
        if policy.get("rollback") != "restore-previous-lock-and-owned-targets":
            errors.append(
                "lock document.policy.rollback must restore the previous lock and owned targets"
            )
        candidate = policy.get("max_exception_days")
        if (
            isinstance(candidate, bool)
            or not isinstance(candidate, int)
            or not 1 <= candidate <= 90
        ):
            errors.append("lock document.policy.max_exception_days must be between 1 and 90")
        else:
            max_days = candidate

    locks = root.get("locks")
    if not isinstance(locks, list) or not locks:
        errors.append("lock document.locks must be a non-empty array")
        return errors
    identifiers: list[str] = []
    paths: set[str] = set()
    for index, item in enumerate(locks):
        label = f"lock document.locks[{index}]"
        lock = require_object(item, label, errors)
        if lock is None:
            continue
        require_closed_keys(lock, LOCK_KEYS, label, errors)
        identifier = lock.get("id")
        if not isinstance(identifier, str) or IDENTIFIER.fullmatch(identifier) is None:
            errors.append(f"{label}.id is invalid")
        else:
            if identifier in identifiers:
                errors.append(f"duplicate lock id: {identifier}")
            identifiers.append(identifier)
        if lock.get("kind") not in LOCK_KINDS:
            errors.append(f"{label}.kind is unsupported: {lock.get('kind')}")
        validate_source(lock.get("source"), f"{label}.source", errors)
        compatibility = lock.get("compatibility")
        validate_compatibility(compatibility, f"{label}.compatibility", errors)
        path = validate_target(lock.get("target"), compatibility, f"{label}.target", errors)
        if path is not None:
            if path in paths:
                errors.append(f"duplicate lock target path: {path}")
            paths.add(path)
        validate_exception(lock.get("exception"), f"{label}.exception", as_of, max_days, errors)
    if identifiers != sorted(identifiers):
        errors.append("lock entries must be sorted by id for deterministic review")
    return errors


def parse_as_of(value: str) -> datetime:
    """Parse a command-line validation instant or raise argparse's error type."""

    errors: list[str] = []
    parsed = parse_timestamp(value, "--as-of", errors)
    if parsed is None:
        raise argparse.ArgumentTypeError(errors[0])
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone validator command contract."""

    parser = argparse.ArgumentParser(
        description="Validate a Pace v1 lock without contacting sources or running an updater."
    )
    parser.add_argument("lock_file", type=Path, help="Path to a Pace JSON lock file.")
    parser.add_argument(
        "--as-of",
        type=parse_as_of,
        default=None,
        help="Deterministic RFC 3339 UTC instant for exception evaluation.",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Validation result format.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run independent lock validation and return a stable process status."""

    arguments = build_parser().parse_args(argv)
    as_of = arguments.as_of or datetime.now(timezone.utc)
    try:
        document = load_lock(arguments.lock_file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        errors = [f"could not load lock: {error}"]
    else:
        errors = validate_lock(document, as_of)
    if arguments.format == "json":
        print(
            json.dumps(
                {
                    "schema": "egohygiene.pace.lock-validation/v1",
                    "valid": not errors,
                    "lock": str(arguments.lock_file),
                    "as_of": as_of.isoformat().replace("+00:00", "Z"),
                    "errors": errors,
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif errors:
        print(f"INVALID {arguments.lock_file}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print(f"VALID {arguments.lock_file}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Adversarial evidence for the independent Pace lock validator."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_lock.py"
EXAMPLE_PATH = REPOSITORY_ROOT / "examples/pace.lock.json"
SCHEMA_PATH = REPOSITORY_ROOT / "schemas/pace-lock-v1.schema.json"
SPEC = importlib.util.spec_from_file_location("validate_lock", VALIDATOR_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
AS_OF = datetime(2026, 8, 22, tzinfo=timezone.utc)


def example() -> dict[str, object]:
    """Return a mutable copy of the checked-in valid lock."""

    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class PaceLockTests(unittest.TestCase):
    """Require immutable provenance and bounded exception semantics."""

    def assert_error(self, document: object, fragment: str) -> None:
        """Assert that one mutated lock produces a named violation."""

        errors = validator.validate_lock(document, AS_OF)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_example_covers_every_lock_kind_and_is_valid(self) -> None:
        document = example()

        self.assertEqual(validator.validate_lock(document, AS_OF), [])
        self.assertEqual(
            {lock["kind"] for lock in document["locks"]},
            validator.LOCK_KINDS,
        )

    def test_schema_identity_matches_the_executable_contract(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            schema["$id"],
            "https://egohygiene.github.io/pace/contracts/lock/v1/schema.json",
        )
        self.assertEqual(schema["properties"]["schema"]["const"], validator.LOCK_SCHEMA)
        self.assertEqual(
            set(schema["$defs"]["lock"]["properties"]["kind"]["enum"]),
            validator.LOCK_KINDS,
        )

    def test_source_references_and_digests_are_immutable_and_consistent(self) -> None:
        invalid_commit = example()
        invalid_commit["locks"][0]["source"]["reference"] = "main"
        self.assert_error(invalid_commit, "full lowercase Git commit SHA")

        mismatched_digest = example()
        mismatched_digest["locks"][1]["source"]["digest"]["value"] = "f" * 64
        self.assert_error(mismatched_digest, "reference and digest.value must agree")

    def test_generated_ownership_controls_generator_and_rollback(self) -> None:
        missing_generator = example()
        missing_generator["locks"][0]["target"]["generator"] = None
        self.assert_error(missing_generator, "generator is required")

        unsafe_rollback = example()
        unsafe_rollback["locks"][0]["compatibility"]["rollback"] = "restore-lock-only"
        self.assert_error(unsafe_rollback, "restore-lock-and-generated-targets")

    def test_compatibility_major_and_migration_state_fail_closed(self) -> None:
        wrong_major = example()
        wrong_major["locks"][0]["compatibility"]["accepted_major"] = 2
        self.assert_error(wrong_major, "must match the contract major")

        pending_migration = example()
        pending_migration["locks"][0]["compatibility"]["migration"] = "required"
        self.assert_error(pending_migration, "lock is not adoptable")

    def test_active_bounded_exception_is_valid(self) -> None:
        document = example()
        document["locks"][0]["exception"] = {
            "id": "EXC-2026-001",
            "reason": "Temporary compatibility hold while the consumer migrates.",
            "approved_by": "example/hygiene#1",
            "issued_at": "2026-08-21T00:00:00Z",
            "expires_at": "2026-09-01T00:00:00Z",
            "tracking_url": "https://example.invalid/exceptions/1",
        }

        self.assertEqual(validator.validate_lock(document, AS_OF), [])

    def test_expired_future_and_overlong_exceptions_are_rejected(self) -> None:
        expired = example()
        expired["locks"][0]["exception"] = {
            "id": "EXC-2026-001",
            "reason": "Expired fixture.",
            "approved_by": "example/hygiene#1",
            "issued_at": "2026-08-01T00:00:00Z",
            "expires_at": "2026-08-21T00:00:00Z",
            "tracking_url": "https://example.invalid/exceptions/1",
        }
        self.assert_error(expired, "expired at")

        future = deepcopy(expired)
        future["locks"][0]["exception"]["issued_at"] = "2026-08-23T00:00:00Z"
        future["locks"][0]["exception"]["expires_at"] = "2026-08-24T00:00:00Z"
        self.assert_error(future, "not active yet")

        overlong = deepcopy(expired)
        overlong["locks"][0]["exception"]["issued_at"] = "2026-08-01T00:00:00Z"
        overlong["locks"][0]["exception"]["expires_at"] = "2026-10-01T00:00:00Z"
        self.assert_error(overlong, "exceeds policy.max_exception_days")

    def test_paths_identifiers_order_and_unknown_fields_are_closed(self) -> None:
        traversal = example()
        traversal["locks"][0]["target"]["path"] = "../AGENTS.md"
        self.assert_error(traversal, "normalized repository-relative path")

        duplicate = example()
        duplicate["locks"][1]["id"] = duplicate["locks"][0]["id"]
        self.assert_error(duplicate, "duplicate lock id")

        duplicate_target = example()
        duplicate_target["locks"][1]["target"]["path"] = duplicate_target["locks"][0][
            "target"
        ]["path"]
        self.assert_error(duplicate_target, "duplicate lock target path")

        unsorted = example()
        unsorted["locks"][0], unsorted["locks"][1] = (
            unsorted["locks"][1],
            unsorted["locks"][0],
        )
        self.assert_error(unsorted, "sorted by id")

        unknown = example()
        unknown["locks"][0]["source"]["branch"] = "main"
        self.assert_error(unknown, "unknown keys: branch")

    def test_duplicate_json_keys_are_rejected_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema":"one","schema":"two"}\n', encoding="utf-8")

            with self.assertRaisesRegex(validator.DuplicateKeyError, "duplicate JSON key"):
                validator.load_lock(path)

    def test_cli_emits_stable_json_and_status(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_PATH),
                str(EXAMPLE_PATH),
                "--as-of",
                "2026-08-22T00:00:00Z",
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["schema"], "egohygiene.pace.lock-validation/v1")
        self.assertTrue(document["valid"])
        self.assertEqual(document["errors"], [])


if __name__ == "__main__":
    unittest.main()

# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Adversarial evidence for the repository-presentation rollout planner."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/plan_repository_presentation.py"
INVENTORY = ROOT / "examples/repository-presentation.inventory.json"
SPEC = importlib.util.spec_from_file_location("plan_repository_presentation", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


def inventory() -> dict[str, object]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


class RepositoryPresentationRolloutTests(unittest.TestCase):
    """Protect the no-write review gate and privacy-safe fleet state."""

    def test_complete_public_inventory_is_valid_and_explicit(self) -> None:
        document = inventory()
        self.assertEqual(planner.validate_inventory(document), [])
        self.assertEqual(len(document["repositories"]), 29)
        self.assertEqual(
            [record["repository"] for record in document["repositories"]],
            sorted(record["repository"] for record in document["repositories"]),
        )
        self.assertTrue(
            all(record["adoptionState"] in planner.ADOPTION_STATES for record in document["repositories"])
        )

    def test_private_repository_observation_is_redacted(self) -> None:
        record = next(
            item for item in inventory()["repositories"]
            if item["repository"] == "egohygiene/egohygiene"
        )
        self.assertEqual(record["adoptionState"], "deferred")
        self.assertIsNone(record["observed"]["representedCommit"])
        self.assertIsNone(record["observed"]["readme"]["gitBlobSha"])
        self.assertEqual(record["customization"], "redacted")

    def test_canary_wave_covers_three_required_shapes(self) -> None:
        document = inventory()
        self.assertEqual(
            {item["role"] for item in document["canaryWave"]},
            planner.EXPECTED_CANARY_ROLES,
        )
        self.assertEqual(
            {item["repository"] for item in document["canaryWave"]},
            {"egohygiene/mantle", "egohygiene/identity", "egohygiene/antidote"},
        )

    def test_plan_is_deterministic_no_write_and_observatory_safe(self) -> None:
        document = inventory()
        first = planner.build_plan(document)
        second = planner.build_plan(document)
        self.assertEqual(first, second)
        self.assertEqual(planner.validate_plan(first), [])
        self.assertFalse(first["review"]["approved"])
        self.assertTrue(first["review"]["requiredBeforeFleetWrite"])
        self.assertEqual(first["summary"]["total"], 29)
        self.assertGreater(first["summary"]["blocked"], 0)
        self.assertIsNone(first["observatory"]["healthScore"])
        self.assertEqual(
            first["waves"][0]["repositories"],
            ["egohygiene/mantle", "egohygiene/identity", "egohygiene/antidote"],
        )

    def test_missing_assets_facts_and_egolint_block_canary(self) -> None:
        plan = planner.build_plan(inventory())
        mantle = next(
            record for record in plan["repositories"]
            if record["repository"] == "egohygiene/mantle"
        )
        self.assertEqual(mantle["disposition"], "blocked")
        self.assertTrue(any("Identity" in blocker for blocker in mantle["blockers"]))
        self.assertTrue(any("facts" in blocker for blocker in mantle["blockers"]))
        self.assertTrue(any("Egolint" in blocker for blocker in mantle["blockers"]))

    def test_proposal_is_refused_before_review_and_while_blocked(self) -> None:
        plan = planner.build_plan(inventory())
        review = {
            "schema": planner.REVIEW_SCHEMA,
            "planDigest": plan["planDigest"],
            "reviewer": "szmyty",
            "reviewedAt": "2026-08-31T16:00:00Z",
            "decision": "approved",
        }
        with self.assertRaisesRegex(ValueError, "not eligible"):
            planner.build_proposal(plan, review, "egohygiene/mantle")

        bad_review = copy.deepcopy(review)
        bad_review["planDigest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact plan digest"):
            planner.build_proposal(plan, bad_review, "egohygiene/mantle")

    def test_reviewed_eligible_repository_yields_one_credential_free_proposal(self) -> None:
        document = inventory()
        mantle = next(
            record for record in document["repositories"]
            if record["repository"] == "egohygiene/mantle"
        )
        mantle["adoptionState"] = "eligible"
        mantle["reasons"] = []
        mantle["observed"]["identityPackage"]["status"] = "present"
        mantle["observed"]["facts"]["status"] = "complete"
        mantle["observed"]["egolint"]["status"] = "valid"
        mantle["observed"]["egolint"]["reportDigest"] = "a" * 64
        self.assertEqual(planner.validate_inventory(document), [])

        plan = planner.build_plan(document)
        review = {
            "schema": planner.REVIEW_SCHEMA,
            "planDigest": plan["planDigest"],
            "reviewer": "szmyty",
            "reviewedAt": "2026-08-31T16:00:00Z",
            "decision": "approved",
        }
        proposal = planner.build_proposal(plan, review, "egohygiene/mantle")
        self.assertEqual(proposal["repository"], "egohygiene/mantle")
        self.assertTrue(proposal["preconditions"]["reviewed"])
        self.assertEqual(proposal["preconditions"]["egolintStatus"], "valid")
        self.assertFalse(proposal["preconditions"]["credentialsEmbedded"])
        self.assertTrue(proposal["materialization"]["oneRepositoryOnly"])
        self.assertEqual(
            proposal["rollback"]["readmeGitBlobSha"],
            mantle["observed"]["readme"]["gitBlobSha"],
        )
        self.assertRegex(proposal["proposalDigest"], r"^[0-9a-f]{64}$")
        self.assertNotIn("token", json.dumps(proposal).casefold())

    def test_tampered_and_superseded_plans_fail_closed(self) -> None:
        plan = planner.build_plan(inventory())
        plan["summary"]["total"] = 30
        self.assertIn("planDigest", " ".join(planner.validate_plan(plan)))

        document = inventory()
        original = planner.build_plan(document)
        mantle = next(
            record for record in document["repositories"]
            if record["repository"] == "egohygiene/mantle"
        )
        mantle["observed"]["representedCommit"] = "f" * 40
        superseding = planner.build_plan(document)
        self.assertNotEqual(original["inventoryDigest"], superseding["inventoryDigest"])
        self.assertNotEqual(original["planDigest"], superseding["planDigest"])

    def test_cli_generates_and_verifies_exact_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pace-presentation-") as temporary:
            output = Path(temporary) / "plan.json"
            create = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "plan",
                    "--inventory",
                    str(INVENTORY),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            verify = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "verify-plan",
                    "--plan",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)


if __name__ == "__main__":
    unittest.main()

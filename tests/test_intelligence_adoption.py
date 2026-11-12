# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Focused offline conformance for the exact-public adoption projection."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "project_intelligence_adoption", ROOT / "scripts/project_intelligence_adoption.py"
)
assert SPEC is not None and SPEC.loader is not None
projector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projector)


class IntelligenceAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = (ROOT / "vendor/intelligence-adoption/repositories.source.json").read_bytes()
        cls.catalog = (ROOT / "vendor/intelligence-adoption/public-repositories.json").read_bytes()
        cls.ledger_bytes = (ROOT / "docs/evidence/intelligence-adoption/2026-11-11.ledger.json").read_bytes()
        cls.ledger = json.loads(cls.ledger_bytes)

    def test_dated_ledger_is_the_exact_canonical_source_projection(self) -> None:
        value = deepcopy(self.ledger)
        self.assertIs(projector.validate_ledger(value, self.inventory, self.catalog), value)
        projected = projector.project(
            self.inventory, self.catalog, as_of=value["projection_as_of"]
        )
        self.assertEqual(projector.canonical_bytes(projected), self.ledger_bytes)

    def test_numeric_zero_cannot_replace_a_boolean_contract_field(self) -> None:
        value = deepcopy(self.ledger)
        value["scope"]["organization_total_claim"] = 0
        with self.assertRaisesRegex(ValueError, "Ledger does not match"):
            projector.validate_ledger(value, self.inventory, self.catalog)

    def test_source_observations_cannot_be_promoted_to_completed_artifacts(self) -> None:
        value = deepcopy(self.ledger)
        value["repositories"][0]["model_artifact"]["state"] = "complete"
        with self.assertRaisesRegex(ValueError, "Ledger does not match"):
            projector.validate_ledger(value, self.inventory, self.catalog)

    def test_projection_clock_does_not_refresh_roster_observations_or_holds(self) -> None:
        projected = projector.project(
            self.inventory, self.catalog, as_of="2026-11-12T00:00:00Z"
        )
        self.assertFalse(projected["scope"]["organization_total_claim"])
        self.assertEqual(projected["source_inputs"], self.ledger["source_inputs"])
        self.assertEqual(projected["repositories"], self.ledger["repositories"])
        self.assertEqual(len(projected["repositories"]), 28)

    def test_unreviewed_bytes_are_denied_before_payload_interpretation(self) -> None:
        for raw in (b"not-json", b'{"unreviewed":"synthetic input"}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(
                ValueError, "^Input does not match the reviewed public source pin$"
            ):
                projector.project(raw, self.catalog, as_of=self.ledger["projection_as_of"])


if __name__ == "__main__":
    unittest.main()

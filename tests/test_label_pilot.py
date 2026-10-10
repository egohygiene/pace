"""Bounded evidence for the read-only label pilot; requires the exact Relay source."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/preview_repository_labels.py"
SPEC = importlib.util.spec_from_file_location("pilot", SCRIPT)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
OBSERVATION = ROOT / "docs/evidence/label-rollout/aether-observation-2026-10-10.json"


@unittest.skipUnless(os.environ.get("PACE_LABEL_RELAY_SOURCE"), "Set PACE_LABEL_RELAY_SOURCE to the pinned Relay checkout")
class LabelPilot(unittest.TestCase):
    def setUp(self):
        self.source = Path(os.environ["PACE_LABEL_RELAY_SOURCE"])

    def test_enrollment_produces_native_additive_plan_without_provider_writes(self):
        result = pilot.preview(self.source, OBSERVATION)
        self.assertEqual(result["status"], "ready-for-review")
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["canonical_assignment"], {
            "repository": "egohygiene/aether", "include_universal": True,
            "overlays": [], "additional_labels": [],
        })
        native = result["native_sync_plan"]
        self.assertEqual(native["summary"], {"create": 18, "update": 0, "delete": 0, "unchanged": 0})
        self.assertEqual(native["contract"]["catalog_version"], "1.1.0")
        self.assertEqual(native["operations"]["create"], result["universal_preview"]["create"])
        self.assertEqual(native["operations"]["update"], [])
        self.assertEqual(native["operations"]["delete"], [])
        self.assertRegex(native["plan_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(result["summary"]["missing_universal"], 18)
        self.assertEqual(len(result["preserved_observed_labels"]), 41)
        self.assertEqual(result["summary"]["proposed_deletions"], 0)
        self.assertEqual(result["provider_writes"], "forbidden")
        self.assertIn("Review the native synchronization plan", result["next"])

    def test_cli_repeat_is_identical_and_existing_output_is_preserved(self):
        before = OBSERVATION.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            outputs = [Path(directory) / "one.json", Path(directory) / "two.json"]
            command = [sys.executable, str(SCRIPT), "--relay", str(self.source), "--observation", str(OBSERVATION)]
            for output in outputs:
                run = subprocess.run([*command, "--output", str(output)], capture_output=True)
                self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            retained = outputs[0].read_bytes()
            rerun = subprocess.run([*command, "--output", str(outputs[0])], capture_output=True)
            self.assertEqual(rerun.returncode, 3)
            self.assertEqual(outputs[0].read_bytes(), retained)
        self.assertEqual(OBSERVATION.read_bytes(), before)

    def test_partial_or_unterminated_capture_is_rejected(self):
        for change in (lambda v: v["coverage"].update(status="partial", error="PAGE_LIMIT"),
                       lambda v: v["coverage"]["pages"][0].update(records=100)):
            value = pilot.load(OBSERVATION)
            change(value)
            with self.assertRaises(ValueError):
                pilot.validate_observation(value, "egohygiene/aether")

    def test_other_repository_duplicate_id_and_unknown_configuration_are_rejected(self):
        for change in (lambda v: v["repository"].update(name="egohygiene/pace"),
                       lambda v: v["labels"][1].update(id=v["labels"][0]["id"]),
                       lambda v: v["configuration"].update(status="present")):
            value = pilot.load(OBSERVATION)
            change(value)
            with self.assertRaises(ValueError):
                pilot.validate_observation(value, "egohygiene/aether")

    def test_changed_relay_tree_or_code_digest_is_rejected(self):
        for key in ("tree", "files"):
            value = pilot.load(pilot.LOCK)
            if key == "tree":
                value["relay"][key] = "0" * 40
            else:
                value["relay"][key]["actions/repository-labels/scripts/repository_labels.py"] = "0" * 64
            with tempfile.TemporaryDirectory() as directory:
                lock = Path(directory) / "lock.json"
                lock.write_bytes(pilot.encoded(value))
                with patch.object(pilot, "LOCK", lock), self.assertRaises(ValueError):
                    pilot.preview(self.source, OBSERVATION)

    def test_changed_organization_digest_is_rejected(self):
        value = pilot.load(pilot.LOCK)
        value["organization"]["files"][".github/labels/catalog.v1.json"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "lock.json"
            lock.write_bytes(pilot.encoded(value))
            with patch.object(pilot, "LOCK", lock), self.assertRaises(ValueError):
                pilot.preview(self.source, OBSERVATION)

    def test_symlink_output_does_not_replace_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence.txt"
            target.write_text("retain")
            link = Path(directory) / "out.json"
            link.symlink_to(target)
            run = subprocess.run([sys.executable, str(SCRIPT), "--relay", str(self.source),
                "--observation", str(OBSERVATION), "--output", str(link)], capture_output=True)
            self.assertEqual(run.returncode, 3)
            self.assertEqual(target.read_text(), "retain")


if __name__ == "__main__":
    unittest.main()

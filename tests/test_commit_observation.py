from copy import deepcopy
import json
import os
import stat
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from observation_inputs import digest, load_pinned
from observe_commit_authoring import main, observe
from test_release_observation import captured, fixture as release_fixture


def fixture():
    snapshot, lock = release_fixture()
    snapshot["kind"] = lock["kind"] = "commit-authoring"
    lock["target"]["schema_version"] = "egohygiene.commit-authoring/v1"
    row = snapshot["repositories"][0]
    row["files"] = {
        "package.json": captured(json.dumps({"scripts": {"commit": "never execute me", "prepare": "never execute hooks"},
                                              "config": {"commitizen": {"path": "cz-conventional-changelog"}}})),
        "commitlint.config.js": captured("throw new Error('CONFIG_EXECUTION_CANARY');"),
        ".czrc": captured('{"path":"cz-customizable"}'),
        "lefthook.yml": captured("pre-commit:\n  commands:\n    canary:\n      run: never-run\n"),
        ".github/workflows/pr-title.yml": captured("name: captured-not-run\n"),
        "Taskfile.yml": {"state": "missing"},
        "Taskfile.yaml": {"state": "missing"},
    }
    row["merge_policy"] = {"state": "observed", "allow_merge_commit": True, "allow_squash_merge": True,
                           "allow_rebase_merge": False, "source": "https://api.github.com/repos/fictional/tool"}
    return snapshot, lock


class CommitObservationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def save(self, snapshot, lock):
        raw = json.dumps(snapshot, sort_keys=True).encode()
        lock = deepcopy(lock); lock["snapshot_sha256"] = digest(raw)
        a, b = self.root / "snapshot.json", self.root / "lock.json"
        a.write_bytes(raw); b.write_text(json.dumps(lock))
        return a, b

    def report(self, snapshot=None, lock=None):
        if snapshot is None:
            snapshot, lock = fixture()
        a, b = self.save(snapshot, lock)
        return observe(*load_pinned(a, b, "commit-authoring"), as_of="2026-11-14T00:00:00Z")

    def test_conflicting_cz_sources_and_all_concerns_are_preserved_without_execution(self):
        row = self.report()["repositories"][0]
        self.assertEqual(row["scopes"]["commitizen"]["configuration"]["state"], "conflicting")
        self.assertEqual(row["scopes"]["commitlint"]["state"], "observed-unparsed")
        self.assertEqual(row["scopes"]["taskfile"]["state"], "missing")
        self.assertEqual(row["scopes"]["package_scripts"]["names"], ["commit", "prepare"])
        self.assertNotIn("CONFIG_EXECUTION_CANARY", json.dumps(row))
        self.assertNotIn("never execute", json.dumps(row))
        for field in ("compatibility", "adoption", "enforcement"):
            self.assertEqual(row[field], "not-assessed")

    def test_matching_adapter_sources_are_not_declared_canonical(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["files"][".czrc"] = captured('{"path":"cz-conventional-changelog"}')
        row = self.report(snapshot, lock)["repositories"][0]
        self.assertEqual(row["scopes"]["commitizen"]["configuration"]["state"], "observed")
        self.assertEqual(row["compatibility"], "not-assessed")

    def test_unknown_captured_sources_do_not_become_missing(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["files"] = {}
        row = self.report(snapshot, lock)["repositories"][0]
        self.assertEqual(row["scopes"]["commitlint"]["state"], "unknown")
        self.assertEqual(row["scopes"]["hooks"]["state"], "unknown")

    def test_extra_hook_paths_are_inventoried_but_never_executed(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["files"][".husky/pre-commit"] = captured("exit 99\n")
        paths = [file["path"] for file in self.report(snapshot, lock)["repositories"][0]["scopes"]["hooks"]["files"]]
        self.assertIn(".husky/pre-commit", paths)

    def test_malformed_config_is_explicit_and_does_not_echo_content(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["files"][".czrc"] = captured("PRIVATE_INVALID_JSON_CANARY")
        report = self.report(snapshot, lock)
        self.assertEqual(report["repositories"][0]["scopes"]["commitizen"]["configuration"]["state"], "invalid")
        self.assertNotIn("PRIVATE_INVALID_JSON_CANARY", json.dumps(report))

    def test_merge_policy_observations_are_strict_boolean_provider_assertions(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["merge_policy"]["allow_merge_commit"] = 1
        a, b = self.save(snapshot, lock)
        with self.assertRaises(ValueError):
            load_pinned(a, b, "commit-authoring")

    def test_cli_receipt_is_repeatable_and_never_overwritten(self):
        a, b = self.save(*fixture())
        target = self.root / "report.json"
        args = ["--snapshot", str(a), "--lock", str(b), "--as-of", "2026-11-14T00:00:00Z", "--output", str(target)]
        self.assertEqual(main(args), 0)
        first = target.read_bytes()
        self.assertEqual(main(args), 1)
        self.assertEqual(target.read_bytes(), first)

    def test_private_receipt_is_owner_only_under_permissive_umask(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0].update(visibility="private", lifecycle="internal")
        a, b = self.save(snapshot, lock)
        target = self.root / "private-report.json"
        previous_umask = os.umask(0o022)
        try:
            self.assertEqual(main(["--snapshot", str(a), "--lock", str(b), "--as-of", "2026-11-14T00:00:00Z", "--audience", "private", "--output", str(target)]), 0)
        finally:
            os.umask(previous_umask)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        report = json.loads(target.read_text())
        self.assertEqual(report["repositories"][0]["lifecycle"], "internal")


if __name__ == "__main__":
    unittest.main()

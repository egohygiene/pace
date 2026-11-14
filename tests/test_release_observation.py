"""Offline source observations never imply conformance, adoption or publication."""
from copy import deepcopy
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from observation_inputs import digest, load_pinned, output, read
from observe_release_adoption import main, observe


def captured(text):
    return {"state": "present", "text": text, "sha256": digest(text.encode())}


def fixture():
    declaration = {"schema_version": "egohygiene.repository-release/v1",
                   "repository": {"id": "fictional/tool", "release_profile": "python-package"},
                   "changelog": {"path": "CHANGELOG.md"},
                   "components": [{"version_authority": {"kind": "pyproject-project", "path": "pyproject.toml"}}],
                   "delivery": {"channels": [{"kind": "github-release", "state": "configured"}]}}
    row = {"repository": "fictional/tool", "revision": "1" * 40, "visibility": "public", "lifecycle": "active",
           "files": {".egohygiene/release.json": captured(json.dumps(declaration)),
                     "CHANGELOG.md": captured("# Changes\n\n## [Unreleased]\n"),
                     "pyproject.toml": captured('[project]\nversion = "0.2.0"\n')},
           "tags": {"current": None, "latest": "v0.1.0"}}
    snapshot = {"schema_version": "egohygiene.pace.observation-input/v1", "kind": "release",
                "observed_at": "2026-11-13T00:00:00Z", "repositories": [row]}
    lock = {"schema_version": "egohygiene.pace.observation-lock/v1", "kind": "release", "snapshot_sha256": "",
            "target": {"schema_version": "egohygiene.repository-release/v1", "authority": "proposed",
                       "repository": "egohygiene/aether", "revision": None}}
    return snapshot, lock


class ReleaseObservationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def save(self, snapshot=None, lock=None):
        if snapshot is None:
            snapshot, lock = fixture()
        text = json.dumps(snapshot, sort_keys=True).encode()
        lock = deepcopy(lock)
        lock["snapshot_sha256"] = digest(text)
        source = self.root / "snapshot.json"
        pinned = self.root / "lock.json"
        source.write_bytes(text)
        pinned.write_text(json.dumps(lock))
        return source, pinned

    def report(self, snapshot=None, lock=None, **options):
        source, pinned = self.save(snapshot, lock)
        return observe(*load_pinned(source, pinned, "release", audience=options.get("audience", "public")),
                       as_of="2026-11-14T00:00:00Z", **options)

    def test_declared_channels_versions_and_tags_are_distinct_from_publication(self):
        report = self.report()
        row = report["repositories"][0]
        self.assertEqual(row["components"][0]["value"], "0.2.0")
        self.assertTrue(row["changelog"]["unreleased_heading"])
        self.assertEqual(row["channels"][0]["declared_state"], "configured")
        for key in ("adoption", "publication", "migration"):
            self.assertEqual(row[key], "not-assessed")
        self.assertEqual(row["conformance"]["state"], "unknown")
        self.assertEqual(row["drift"]["state"], "not-assessed")
        self.assertEqual(report["qualification"], "source-observation-only")

    def test_accepted_target_only_allows_schema_comparison(self):
        snapshot, lock = fixture()
        lock["target"]["authority"] = "accepted"
        lock["target"]["revision"] = "2" * 40
        self.assertEqual(self.report(snapshot, lock)["repositories"][0]["drift"]["state"], "schema-matches")
        lock["target"]["schema_version"] = "egohygiene.repository-release/v2"
        self.assertEqual(self.report(snapshot, lock)["repositories"][0]["drift"]["state"], "schema-differs")

    def test_profile_names_are_observed_without_reinventing_owner_taxonomy(self):
        for profile in ("cli-library", "internal-only", "contract", "future-profile"):
            snapshot, lock = fixture()
            file = snapshot["repositories"][0]["files"][".egohygiene/release.json"]
            declaration = json.loads(file["text"])
            declaration["repository"]["release_profile"] = profile
            snapshot["repositories"][0]["files"][".egohygiene/release.json"] = captured(json.dumps(declaration))
            row = self.report(snapshot, lock)["repositories"][0]
            self.assertEqual(row["profile"], profile)
            self.assertEqual(row["conformance"]["state"], "unknown")

    def test_missing_unavailable_and_unknown_remain_distinct(self):
        for state in ("missing", "unavailable", "unknown"):
            snapshot, lock = fixture()
            snapshot["repositories"][0]["files"][".egohygiene/release.json"] = {"state": state}
            self.assertEqual(self.report(snapshot, lock)["repositories"][0]["declaration"]["state"], state)

    def test_invalid_declaration_does_not_leak_partial_claims(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["files"][".egohygiene/release.json"] = captured('{"schema_version":"private/path"}')
        row = self.report(snapshot, lock)["repositories"][0]
        self.assertEqual(row["declaration"]["state"], "invalid")
        self.assertEqual(row["profile"], "unknown")
        self.assertNotIn("private/path", json.dumps(row))

    def test_tampered_snapshot_is_rejected_before_parsing(self):
        source, pinned = self.save()
        source.write_text("not valid JSON")
        with self.assertRaisesRegex(ValueError, "digest"):
            load_pinned(source, pinned, "release")

    def test_captured_file_digest_and_duplicate_repository_are_rejected(self):
        for mutate in (lambda s: s["repositories"][0]["files"]["CHANGELOG.md"].update(text="changed"),
                       lambda s: s["repositories"].append(deepcopy(s["repositories"][0]))):
            snapshot, lock = fixture()
            mutate(snapshot)
            source, pinned = self.save(snapshot, lock)
            with self.assertRaises(ValueError):
                load_pinned(source, pinned, "release")

    def test_private_inventory_requires_explicit_private_output(self):
        snapshot, lock = fixture()
        snapshot["repositories"][0]["visibility"] = "private"
        with self.assertRaisesRegex(ValueError, "private report"):
            self.report(snapshot, lock)
        self.assertEqual(self.report(snapshot, lock, audience="private")["audience"], "private")

    def test_staleness_and_future_observation_clock_are_explicit(self):
        snapshot, lock = fixture()
        self.assertEqual(self.report(snapshot, lock, max_age_days=0)["freshness"], "stale")
        source, pinned = self.save(snapshot, lock)
        with self.assertRaises(ValueError):
            observe(*load_pinned(source, pinned, "release"), as_of="2026-11-12T00:00:00Z")

    def test_existing_receipt_symlinks_and_special_inputs_are_refused(self):
        target = self.root / "report.json"
        output(self.report(), target)
        with self.assertRaises(FileExistsError):
            output(self.report(), target)
        linked = self.root / "link"
        linked.symlink_to(target)
        with self.assertRaises(OSError):
            read(linked)
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            read(fifo)

    def test_cli_errors_are_bounded_and_do_not_echo_private_source_paths(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            code = main(["--snapshot", "/home/fictional/private.json", "--lock", str(self.root / "absent"),
                         "--as-of", "2026-11-14T00:00:00Z"])
        self.assertEqual(code, 1)
        self.assertNotIn("/home/fictional", errors.getvalue())

    def test_output_order_is_independent_of_roster_order(self):
        snapshot, lock = fixture()
        second = deepcopy(snapshot["repositories"][0])
        second.update(repository="fictional/another", files={})
        snapshot["repositories"].append(second)
        first = self.report(snapshot, lock)["repositories"]
        snapshot["repositories"].reverse()
        self.assertEqual(first, self.report(snapshot, lock)["repositories"])


if __name__ == "__main__":
    unittest.main()

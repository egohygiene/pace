# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Adversarial evidence for reviewed fleet convergence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_fleet_convergence.py"
EXAMPLES = ROOT / "examples" / "convergence"
SPEC = importlib.util.spec_from_file_location("plan_fleet_convergence", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


def fixture_plan() -> dict[str, object]:
    return planner.build_plan(
        EXAMPLES / "fleet.manifest.json",
        EXAMPLES / "catalog.json",
        EXAMPLES / "observatory.snapshot.json",
    )


def review(
    plan: dict[str, object], *, approved: list[str] | None = None
) -> dict[str, object]:
    unit_id = plan["units"][0]["unit_id"]
    return {
        "schema": planner.REVIEW_SCHEMA,
        "plan_digest": plan["plan_digest"],
        "reviewer": "fixture-reviewer",
        "reviewed_at": "2026-09-02T13:00:00Z",
        "decision": "approved",
        "approved_units": approved if approved is not None else [unit_id],
        "completed_units": [],
    }


def run_git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class FakeGitHubClient:
    """Record the exact GitHub write boundary without network access."""

    def __init__(self, base_commit: str) -> None:
        self.base_commit = base_commit
        self.branch_commit: str | None = None
        self.branch_tree: str | None = None
        self.pull: dict[str, object] | None = None
        self.calls: list[tuple[str, str, object | None]] = []

    def request(self, method: str, path: str, payload: object | None = None):
        self.calls.append((method, path, payload))
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return 200, {"object": {"sha": self.base_commit}}
        if method == "GET" and f"/git/commits/{self.base_commit}" in path:
            return 200, {"tree": {"sha": "base-tree"}}
        if method == "POST" and path.endswith("/git/blobs"):
            return 201, {"sha": f"blob-{len(self.calls)}"}
        if method == "POST" and path.endswith("/git/trees"):
            self.branch_tree = "candidate-tree"
            return 201, {"sha": self.branch_tree}
        if method == "GET" and "/git/ref/heads/pace/" in path:
            if self.branch_commit is None:
                return 404, {"message": "Not Found"}
            return 200, {"object": {"sha": self.branch_commit}}
        if (
            method == "GET"
            and self.branch_commit
            and path.endswith(f"/git/commits/{self.branch_commit}")
        ):
            return 200, {
                "tree": {"sha": self.branch_tree},
                "parents": [{"sha": self.base_commit}],
            }
        if method == "POST" and path.endswith("/git/commits"):
            self.branch_commit = "1" * 40
            return 201, {"sha": self.branch_commit}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {"ref": payload["ref"]}
        if method == "GET" and "/pulls?" in path:
            return 200, [self.pull] if self.pull else []
        if method == "POST" and path.endswith("/pulls"):
            self.pull = {
                "number": 42,
                "html_url": "https://github.com/egohygiene/example-tool/pull/42",
            }
            return 201, self.pull
        raise AssertionError(f"unexpected fake GitHub call: {method} {path}")


class FleetConvergenceTests(unittest.TestCase):
    """Protect determinism, review, bounded writes, and recovery controls."""

    def test_fixture_plan_is_deterministic_and_explainable(self) -> None:
        first = fixture_plan()
        second = fixture_plan()

        self.assertEqual(first, second)
        self.assertEqual(planner.validate_plan(first), [])
        self.assertFalse(first["review"]["approved"])
        self.assertEqual(first["summary"]["dispositions"], {"ready_for_review": 1})
        unit = first["units"][0]
        self.assertEqual(unit["risk"], "medium")
        self.assertEqual(unit["represented_commit"], "f" * 40)
        self.assertEqual(unit["changes"][0]["type"], "update")
        self.assertIn("immutable source provenance", unit["changes"][0]["reasons"][0])

    def test_observatory_stale_or_ambiguous_state_blocks_instead_of_guessing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="pace-observation-") as temporary:
            target = Path(temporary)
            for source in EXAMPLES.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            observation_path = target / "observatory.snapshot.json"
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
            evidence = observation["repositories"][0]["evidence"]
            evidence["freshness"] = "stale"
            evidence["represented_commits"].append("0" * 40)
            observation_path.write_text(json.dumps(observation), encoding="utf-8")

            plan = planner.build_plan(
                target / "fleet.manifest.json",
                target / "catalog.json",
                observation_path,
            )

        unit = plan["units"][0]
        self.assertEqual(unit["disposition"], "blocked")
        self.assertIsNone(unit["represented_commit"])
        self.assertTrue(any("freshness is stale" in item for item in unit["blockers"]))
        self.assertTrue(any("exactly one" in item for item in unit["blockers"]))

    def test_pause_is_manifest_state_and_supersedes_the_plan(self) -> None:
        original = fixture_plan()
        with tempfile.TemporaryDirectory(prefix="pace-pause-") as temporary:
            target = Path(temporary)
            for source in EXAMPLES.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            manifest_path = target / "fleet.manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["repositories"][0]["state"] = "paused"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            paused = planner.build_plan(
                manifest_path,
                target / "catalog.json",
                target / "observatory.snapshot.json",
            )

        self.assertEqual(paused["units"][0]["disposition"], "paused")
        self.assertNotEqual(paused["plan_digest"], original["plan_digest"])

    def test_dependency_order_is_explicit_and_cycles_fail(self) -> None:
        records = [
            {"repository": "egohygiene/b", "depends_on": ["egohygiene/a"]},
            {"repository": "egohygiene/a", "depends_on": []},
        ]
        self.assertEqual(
            planner._topological_repositories(records),
            ["egohygiene/a", "egohygiene/b"],
        )
        records[1]["depends_on"] = ["egohygiene/b"]
        with self.assertRaisesRegex(planner.ContractError, "dependency cycle"):
            planner._topological_repositories(records)

    def test_generated_target_drift_requires_exact_holon_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pace-holon-") as temporary:
            target = Path(temporary)
            for source in EXAMPLES.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            for name in (
                "example-tool.current.lock.json",
                "example-tool.desired.lock.json",
            ):
                path = target / name
                document = json.loads(path.read_text(encoding="utf-8"))
                lock = document["locks"][0]
                lock["target"]["management"] = "generated"
                lock["target"]["generator"] = "egohygiene/holon"
                lock["compatibility"]["rollback"] = "restore-lock-and-generated-targets"
                path.write_text(json.dumps(document), encoding="utf-8")
            plan = planner.build_plan(
                target / "fleet.manifest.json",
                target / "catalog.json",
                target / "observatory.snapshot.json",
            )

        unit = plan["units"][0]
        self.assertEqual(unit["disposition"], "blocked")
        self.assertTrue(any("exact Holon" in item for item in unit["blockers"]))

    def test_exact_holon_plan_unblocks_only_the_generated_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pace-holon-ready-") as temporary:
            target = Path(temporary)
            for source in EXAMPLES.iterdir():
                if source.is_file():
                    (target / source.name).write_bytes(source.read_bytes())
            for name in (
                "example-tool.current.lock.json",
                "example-tool.desired.lock.json",
            ):
                path = target / name
                document = json.loads(path.read_text(encoding="utf-8"))
                lock = document["locks"][0]
                lock["target"]["management"] = "generated"
                lock["target"]["generator"] = "egohygiene/holon"
                lock["compatibility"]["rollback"] = "restore-lock-and-generated-targets"
                path.write_text(json.dumps(document), encoding="utf-8")
            old_bytes = b"old schema\n"
            new_bytes = b"new schema\n"
            holon_plan = {
                "schema_version": planner.HOLON_PLAN_SCHEMA,
                "engine_version": "1.0.0",
                "repository": "egohygiene/example-tool",
                "resolved_manifest_sha256": "1" * 64,
                "resolved_manifest": {},
                "inputs": {"render_source": None, "aether": None},
                "capability_adapters": [],
                "operations": [
                    {
                        "action": "update",
                        "path": "schemas/repository-report.schema.json",
                        "owner": "egohygiene/holon",
                        "source": "fixture",
                        "desired_sha256": hashlib.sha256(new_bytes).hexdigest(),
                        "previous_sha256": hashlib.sha256(old_bytes).hexdigest(),
                        "reason": "rendered source changed",
                    }
                ],
                "summary": {"update": 1},
            }
            holon_plan["plan_id"] = planner.digest(holon_plan)
            (target / "example-tool.holon.plan.json").write_text(
                json.dumps(holon_plan), encoding="utf-8"
            )
            manifest_path = target / "fleet.manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["repositories"][0]["holon_plan"] = "example-tool.holon.plan.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            plan = planner.build_plan(
                manifest_path,
                target / "catalog.json",
                target / "observatory.snapshot.json",
            )
            unit = plan["units"][0]
            proposal = planner.build_proposal(plan, review(plan), unit["unit_id"])

        self.assertEqual(unit["disposition"], "ready_for_review")
        self.assertEqual(
            [item["path"] for item in proposal["expected_candidate_changes"]],
            [
                ".config/pace.lock.json",
                ".holon/materialization-state.v1.json",
                "schemas/repository-report.schema.json",
            ],
        )

    def test_lock_policy_drift_is_not_mistaken_for_no_change(self) -> None:
        current = json.loads(
            (EXAMPLES / "example-tool.current.lock.json").read_text(encoding="utf-8")
        )
        desired = copy.deepcopy(current)
        desired["policy"]["max_exception_days"] = 14

        changes = planner._lock_changes(current, desired)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["id"], "lock-policy")
        self.assertEqual(changes[0]["risk"], "medium")

    def test_review_can_approve_only_a_partial_fleet_subset(self) -> None:
        plan = fixture_plan()
        unit_id = plan["units"][0]["unit_id"]
        denied = review(plan, approved=[])
        with self.assertRaisesRegex(planner.ContractError, "does not approve"):
            planner.build_proposal(plan, denied, unit_id)

        proposal = planner.build_proposal(plan, review(plan), unit_id)
        self.assertEqual(planner.validate_proposal(proposal), [])
        self.assertEqual(proposal["unit_id"], unit_id)
        self.assertEqual(len(proposal["expected_candidate_changes"]), 1)
        self.assertEqual(
            proposal["rollback"]["previous_lock"], plan["units"][0]["current_lock"]
        )
        self.assertFalse(proposal["rollback"]["force"])

    def test_tampered_plan_and_review_are_rejected(self) -> None:
        plan = fixture_plan()
        plan["units"][0]["risk"] = "low"
        self.assertIn("plan_digest", " ".join(planner.validate_plan(plan)))

        clean = fixture_plan()
        bad_review = review(clean)
        bad_review["plan_digest"] = "0" * 64
        with self.assertRaisesRegex(planner.ContractError, "exact plan digest"):
            planner.build_proposal(clean, bad_review, clean["units"][0]["unit_id"])

    def _candidate(self, proposal: dict[str, object], directory: Path) -> None:
        run_git(directory, "init", "--initial-branch=main")
        run_git(directory, "config", "user.name", "Pace Tests")
        run_git(directory, "config", "user.email", "pace-tests@example.invalid")
        lock_path = directory / ".config" / "pace.lock.json"
        lock_path.parent.mkdir(parents=True)
        lock_path.write_text(
            json.dumps(proposal["rollback"]["previous_lock"], indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        run_git(directory, "add", ".config/pace.lock.json")
        run_git(directory, "commit", "-m", "base")
        proposal["base_commit"] = run_git(directory, "rev-parse", "HEAD")
        unit_seed = {
            "repository": proposal["repository"],
            "current_lock": planner.digest(proposal["rollback"]["previous_lock"]),
            "desired_lock": planner.digest(proposal["desired_lock"]),
            "represented_commit": proposal["base_commit"],
        }
        proposal["unit_id"] = (
            f"upgrade:{proposal['repository']}:{planner.digest(unit_seed)[:12]}"
        )
        proposal["review"]["approved_units"] = [proposal["unit_id"]]
        proposal["proposal_id"] = "pull-request:" + planner.digest(
            {"plan": proposal["plan_digest"], "unit": proposal["unit_id"]}
        )
        proposal["proposal_digest"] = planner.digest(
            planner._proposal_without_digest(proposal)
        )
        lock_path.write_text(
            json.dumps(proposal["desired_lock"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_candidate_tree_is_exactly_bounded(self) -> None:
        plan = fixture_plan()
        proposal = planner.build_proposal(
            plan, review(plan), plan["units"][0]["unit_id"]
        )
        with tempfile.TemporaryDirectory(prefix="pace-candidate-") as temporary:
            candidate = Path(temporary)
            self._candidate(proposal, candidate)
            changes = planner._verify_candidate(proposal, candidate)
            self.assertEqual(changes, {".config/pace.lock.json": "M"})
            (candidate / "README.md").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(planner.ContractError, "unexpected README.md"):
                planner._verify_candidate(proposal, candidate)

    def test_github_adapter_opens_one_pr_and_retry_is_idempotent(self) -> None:
        plan = fixture_plan()
        proposal = planner.build_proposal(
            plan, review(plan), plan["units"][0]["unit_id"]
        )
        with tempfile.TemporaryDirectory(prefix="pace-open-pr-") as temporary:
            candidate = Path(temporary)
            self._candidate(proposal, candidate)
            client = FakeGitHubClient(proposal["base_commit"])
            first = planner.open_pull_request(proposal, candidate, client)
            second = planner.open_pull_request(proposal, candidate, client)

        self.assertEqual(first, second)
        self.assertEqual(first["number"], 42)
        pull_creates = [
            call
            for call in client.calls
            if call[0] == "POST" and call[1].endswith("/pulls")
        ]
        ref_creates = [
            call
            for call in client.calls
            if call[0] == "POST" and call[1].endswith("/git/refs")
        ]
        self.assertEqual(len(pull_creates), 1)
        self.assertEqual(len(ref_creates), 1)
        self.assertTrue(
            all(
                "git/refs/heads/main" not in call[1]
                for call in client.calls
                if call[0] == "POST"
            )
        )

    def test_github_adapter_never_sends_tokens_to_an_unsafe_origin(self) -> None:
        for url in (
            "http://api.github.com",
            "https://token@example.invalid",
            "https://example.invalid/unexpected/path",
        ):
            with (
                self.subTest(url=url),
                self.assertRaisesRegex(planner.ContractError, "HTTPS origin"),
            ):
                planner.GitHubClient("secret", url)

    def test_cli_plans_verifies_and_proposes_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pace-cli-") as temporary:
            target = Path(temporary)
            plan_path = target / "plan.json"
            create = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "plan",
                    "--manifest",
                    str(EXAMPLES / "fleet.manifest.json"),
                    "--catalog",
                    str(EXAMPLES / "catalog.json"),
                    "--observatory",
                    str(EXAMPLES / "observatory.snapshot.json"),
                    "--output",
                    str(plan_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            verify = subprocess.run(
                [sys.executable, str(SCRIPT), "verify-plan", "--plan", str(plan_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            review_path = target / "review.json"
            review_path.write_text(json.dumps(review(plan)), encoding="utf-8")
            proposal_path = target / "proposal.json"
            propose = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "propose",
                    "--plan",
                    str(plan_path),
                    "--review",
                    str(review_path),
                    "--unit",
                    plan["units"][0]["unit_id"],
                    "--output",
                    str(proposal_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(propose.returncode, 0, propose.stderr)
            self.assertTrue(proposal_path.is_file())


if __name__ == "__main__":
    unittest.main()

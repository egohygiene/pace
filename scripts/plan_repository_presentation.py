#!/usr/bin/env python3
"""Build and authorize no-write repository-presentation fleet plans."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INVENTORY = ROOT / "examples/repository-presentation.inventory.json"
INVENTORY_SCHEMA = "egohygiene.pace.repository-presentation-inventory/v1"
PLAN_SCHEMA = "egohygiene.pace.repository-presentation-plan/v1"
REVIEW_SCHEMA = "egohygiene.pace.repository-presentation-review/v1"
PROPOSAL_SCHEMA = "egohygiene.pace.repository-presentation-proposal/v1"
ADOPTION_STATES = {"eligible", "deferred", "exempt", "blocked", "not_applicable"}
PROFILES = {"minimal", "library", "cli", "application", "publication", "private", "archived", "incubating"}
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_PINS = {
    "hygiene": {
        "version": "1.0.0-alpha.1",
        "status": "proposed",
        "revision": "cb2ed63425d29abada2d2bbb43a3b3e59d11aeb8",
        "digest": "44e0881519350e6747723995939c79c6fb4659e38a74b2c32e409866e7a186ba",
    },
    "identity": {
        "version": "1.0.0",
        "revision": "3c2fd3141371b355628e81f66f63159f19d63338",
    },
    "holon": {
        "version": "1.0.0",
        "revision": "4d436b631ea82c463d3a6a04b5664633f3c64b4c",
        "blueprintGitBlobSha": "f16349494be8d917253dfffa3b942698fa0cbcf5",
    },
    "egolint": {
        "version": "0.1.0-alpha.1",
        "revision": "4efe92a2609b3384fcf3b5cda343a4f64d108824",
    },
}
EXPECTED_CANARY_ROLES = {"small-tool", "customized", "publication-product"}


class DuplicateKeyError(ValueError):
    """Raised when strict JSON input repeats a key."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest(value: object) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unknown_keys(value: object, allowed: set[str], location: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return True
    unknown = set(value) - allowed
    if unknown:
        errors.append(f"{location} has unknown keys: {', '.join(sorted(unknown))}")
    return False


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def repository_blockers(record: dict[str, Any]) -> list[str]:
    """Resolve proposal blockers without changing the declared adoption state."""

    blockers: list[str] = []
    observed = record.get("observed", {})
    if not isinstance(observed, dict):
        return ["Observed repository state is malformed."]
    represented = observed.get("representedCommit")
    if record.get("visibility") == "public" and (
        not isinstance(represented, str) or COMMIT_RE.fullmatch(represented) is None
    ):
        blockers.append("A public repository requires a full represented commit.")
    readme = observed.get("readme", {})
    if not isinstance(readme, dict) or readme.get("status") != "present":
        blockers.append("README content is unavailable.")
    identity = observed.get("identityPackage", {})
    if not isinstance(identity, dict) or identity.get("status") != "present":
        blockers.append("Identity repository-presentation package is missing.")
    facts = observed.get("facts", {})
    if not isinstance(facts, dict) or facts.get("status") != "complete":
        blockers.append("Canonical repository-owned presentation facts are incomplete.")
    egolint = observed.get("egolint", {})
    if not isinstance(egolint, dict) or egolint.get("status") != "valid":
        blockers.append("Pinned Egolint repository-presentation validation is not valid.")
    elif not isinstance(egolint.get("reportDigest"), str) or DIGEST_RE.fullmatch(
        egolint["reportDigest"]
    ) is None:
        blockers.append("Pinned Egolint validation report digest is missing.")
    return blockers


def validate_inventory(document: object) -> list[str]:
    errors: list[str] = []
    top_keys = {
        "$schema", "schema", "organization", "observedAt", "collection",
        "contracts", "policy", "canaryWave", "repositories",
    }
    if _unknown_keys(document, top_keys, "inventory", errors):
        return errors
    assert isinstance(document, dict)
    if document.get("schema") != INVENTORY_SCHEMA:
        errors.append(f"inventory.schema must be {INVENTORY_SCHEMA}")
    if document.get("organization") != "egohygiene":
        errors.append("inventory.organization must be egohygiene")
    if not _valid_timestamp(document.get("observedAt")):
        errors.append("inventory.observedAt must be an RFC 3339 UTC timestamp")
    if document.get("contracts") != EXPECTED_PINS:
        errors.append("inventory contracts do not match the reviewed immutable pins")
    collection = document.get("collection")
    if not isinstance(collection, dict) or collection != {
        "mode": "read-only",
        "networkRequired": True,
        "credentialsEmbedded": False,
        "privateDetailsPublished": False,
    }:
        errors.append("inventory collection boundary must be read-only and credential-free")
    policy = document.get("policy")
    expected_policy = {
        "unknownRepository": "fail-closed",
        "writesBeforeReview": False,
        "proposalMode": "one-repository-per-reviewed-proposal",
        "missingFacts": "block",
        "missingAssets": "block",
        "egolintBeforeProposal": True,
    }
    if policy != expected_policy:
        errors.append("inventory policy does not preserve the reviewed fail-closed rollout boundary")

    repositories = document.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        errors.append("inventory.repositories must be a non-empty array")
        return errors
    names: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    record_keys = {
        "repository", "visibility", "archived", "defaultBranch", "profile",
        "lifecycle", "customization", "adoptionState", "reasons", "canaryRole",
        "observed", "exception",
    }
    for index, record in enumerate(repositories):
        location = f"repositories[{index}]"
        if _unknown_keys(record, record_keys, location, errors):
            continue
        assert isinstance(record, dict)
        name = record.get("repository")
        if not isinstance(name, str) or re.fullmatch(r"egohygiene/[A-Za-z0-9_.-]+", name) is None:
            errors.append(f"{location}.repository must be an egohygiene repository")
            continue
        names.append(name)
        if name in records:
            errors.append(f"duplicate repository: {name}")
        records[name] = record
        state = record.get("adoptionState")
        if state not in ADOPTION_STATES:
            errors.append(f"{location}.adoptionState is unsupported")
        if record.get("profile") not in PROFILES:
            errors.append(f"{location}.profile is unsupported")
        reasons = record.get("reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(reason, str) and reason.strip() for reason in reasons
        ):
            errors.append(f"{location}.reasons must contain durable explanations")
        if state != "eligible" and not reasons:
            errors.append(f"{location} requires a reason for {state}")
        if record.get("visibility") == "private":
            observed = record.get("observed", {})
            readme = observed.get("readme", {}) if isinstance(observed, dict) else {}
            if observed.get("representedCommit") is not None or readme.get("gitBlobSha") is not None:
                errors.append(f"{location} leaks private represented state into the public inventory")
        if state == "eligible":
            blockers = repository_blockers(record)
            if blockers:
                errors.append(f"{location} is eligible but blocked: {'; '.join(blockers)}")
        if state == "blocked" and not repository_blockers(record):
            errors.append(f"{location} is blocked without a mechanical blocker")
        if record.get("archived") and record.get("profile") != "archived":
            errors.append(f"{location} archived repositories must use the archived profile")
        egolint = record.get("observed", {}).get("egolint", {})
        if isinstance(egolint, dict) and egolint.get("validatorRevision") != EXPECTED_PINS["egolint"]["revision"]:
            errors.append(f"{location} Egolint revision is not pinned")

    if names != sorted(names):
        errors.append("repositories must be sorted by repository for deterministic review")

    canaries = document.get("canaryWave")
    if not isinstance(canaries, list) or len(canaries) != 3:
        errors.append("canaryWave must contain exactly three representative roles")
    else:
        roles: set[str] = set()
        targets: set[str] = set()
        for index, canary in enumerate(canaries):
            if not isinstance(canary, dict) or set(canary) != {"repository", "role"}:
                errors.append(f"canaryWave[{index}] must contain repository and role")
                continue
            name = canary.get("repository")
            role = canary.get("role")
            if name not in records:
                errors.append(f"canaryWave[{index}] names an unknown repository")
                continue
            if role not in EXPECTED_CANARY_ROLES:
                errors.append(f"canaryWave[{index}] role is unsupported")
            if records[name].get("canaryRole") != role:
                errors.append(f"canaryWave[{index}] does not match repository canaryRole")
            roles.add(str(role))
            targets.add(str(name))
        if roles != EXPECTED_CANARY_ROLES or len(targets) != 3:
            errors.append("canaryWave must cover small-tool, customized, and publication-product once")
    return sorted(set(errors))


def _plan_without_digest(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != "planDigest"}


def build_plan(inventory: dict[str, Any]) -> dict[str, Any]:
    errors = validate_inventory(inventory)
    if errors:
        raise ValueError("invalid inventory: " + "; ".join(errors))
    canary_names = [item["repository"] for item in inventory["canaryWave"]]
    plan_records: list[dict[str, Any]] = []
    for record in inventory["repositories"]:
        blockers = repository_blockers(record)
        state = record["adoptionState"]
        if state == "eligible":
            disposition = "ready_for_review"
        elif state == "blocked":
            disposition = "blocked"
        else:
            disposition = "held"
        plan_records.append({
            "repository": record["repository"],
            "profile": record["profile"],
            "lifecycle": record["lifecycle"],
            "visibility": record["visibility"],
            "representedCommit": record["observed"]["representedCommit"],
            "adoptionState": state,
            "disposition": disposition,
            "canaryRole": record["canaryRole"],
            "blockers": blockers,
            "reasons": record["reasons"],
            "egolint": copy.deepcopy(record["observed"]["egolint"]),
            "drift": {
                "managedRegion": record["observed"]["readme"]["managedRegion"],
                "identityPackage": record["observed"]["identityPackage"]["status"],
                "facts": record["observed"]["facts"]["status"],
            },
            "rollback": {
                "mode": "restore-reviewed-readme-and-holon-state",
                "readmeGitBlobSha": record["observed"]["readme"]["gitBlobSha"],
                "representedCommit": record["observed"]["representedCommit"],
            },
        })
    counts = Counter(record["adoptionState"] for record in plan_records)
    plan = {
        "schema": PLAN_SCHEMA,
        "inventoryDigest": digest(inventory),
        "contracts": copy.deepcopy(inventory["contracts"]),
        "review": {
            "requiredBeforeProposal": True,
            "requiredBeforeFleetWrite": True,
            "approved": False,
            "reviewRecord": None,
        },
        "summary": {
            "total": len(plan_records),
            "states": {state: counts.get(state, 0) for state in sorted(ADOPTION_STATES)},
            "proposalReady": sum(record["disposition"] == "ready_for_review" for record in plan_records),
            "blocked": sum(record["disposition"] == "blocked" for record in plan_records),
        },
        "waves": [
            {
                "id": "canary",
                "order": 1,
                "repositories": canary_names,
                "rule": "All three representative roles must be independently unblocked, reviewed, and proposed.",
            },
            {
                "id": "eligible-public",
                "order": 2,
                "repositories": [
                    record["repository"] for record in plan_records
                    if record["adoptionState"] == "eligible"
                    and record["repository"] not in canary_names
                    and record["visibility"] == "public"
                ],
                "rule": "One repository per reviewed proposal after canary verification.",
            },
            {
                "id": "held",
                "order": 3,
                "repositories": [
                    record["repository"] for record in plan_records
                    if record["adoptionState"] != "eligible"
                ],
                "rule": "No proposal until the explicit state or blockers change in a superseding inventory.",
            },
        ],
        "repositories": plan_records,
        "observatory": {
            "schema": "egohygiene.pace.repository-presentation-observatory/v1",
            "healthScore": None,
            "records": [
                {
                    "repository": record["repository"],
                    "adoptionState": record["adoptionState"],
                    "profile": record["profile"],
                    "representedCommit": record["representedCommit"],
                    "drift": record["drift"],
                    "exception": next(
                        item["exception"] for item in inventory["repositories"]
                        if item["repository"] == record["repository"]
                    ),
                    "freshnessObservedAt": inventory["observedAt"],
                }
                for record in plan_records
            ],
        },
    }
    plan["planDigest"] = digest(_plan_without_digest(plan))
    return plan


def validate_plan(plan: object) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    errors: list[str] = []
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append(f"plan.schema must be {PLAN_SCHEMA}")
    expected = digest(_plan_without_digest(plan))
    if plan.get("planDigest") != expected:
        errors.append("planDigest does not match the canonical plan")
    if plan.get("contracts") != EXPECTED_PINS:
        errors.append("plan contract pins are stale")
    review = plan.get("review")
    if not isinstance(review, dict) or review.get("requiredBeforeProposal") is not True or review.get("approved") is not False:
        errors.append("unreviewed dry-run plan must preserve the review gate")
    records = plan.get("repositories")
    if not isinstance(records, list):
        errors.append("plan.repositories must be an array")
    elif [item.get("repository") for item in records if isinstance(item, dict)] != sorted(
        item.get("repository") for item in records if isinstance(item, dict)
    ):
        errors.append("plan repositories must be deterministically sorted")
    observatory = plan.get("observatory")
    if not isinstance(observatory, dict) or observatory.get("healthScore") is not None:
        errors.append("Observatory projection must not invent a universal health score")
    return errors


def validate_review(review: object, plan: dict[str, Any]) -> list[str]:
    if not isinstance(review, dict):
        return ["review must be an object"]
    errors: list[str] = []
    if set(review) != {"schema", "planDigest", "reviewer", "reviewedAt", "decision"}:
        errors.append("review contains unsupported or missing fields")
    if review.get("schema") != REVIEW_SCHEMA:
        errors.append(f"review.schema must be {REVIEW_SCHEMA}")
    if review.get("planDigest") != plan.get("planDigest"):
        errors.append("review does not authorize this exact plan digest")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        errors.append("reviewer is required")
    if not _valid_timestamp(review.get("reviewedAt")):
        errors.append("reviewedAt must be an RFC 3339 UTC timestamp")
    if review.get("decision") != "approved":
        errors.append("review decision must be approved")
    return errors


def build_proposal(
    plan: dict[str, Any], review: dict[str, Any], repository: str
) -> dict[str, Any]:
    errors = validate_plan(plan) + validate_review(review, plan)
    records = {
        item["repository"]: item
        for item in plan.get("repositories", [])
        if isinstance(item, dict) and isinstance(item.get("repository"), str)
    }
    record = records.get(repository)
    if record is None:
        errors.append(f"repository is absent from the reviewed plan: {repository}")
    else:
        if record.get("adoptionState") != "eligible":
            errors.append(f"{repository} is {record.get('adoptionState')}, not eligible")
        if record.get("blockers"):
            errors.append(f"{repository} still has blockers")
        egolint = record.get("egolint", {})
        if not isinstance(egolint, dict) or egolint.get("status") != "valid":
            errors.append(f"{repository} lacks valid pinned Egolint evidence")
    if errors:
        raise ValueError("proposal refused: " + "; ".join(errors))
    assert record is not None
    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "proposalId": f"repository-presentation:{repository}:{record['representedCommit']}",
        "planDigest": plan["planDigest"],
        "inventoryDigest": plan["inventoryDigest"],
        "repository": repository,
        "representedCommit": record["representedCommit"],
        "profile": record["profile"],
        "contracts": copy.deepcopy(plan["contracts"]),
        "preconditions": {
            "reviewed": True,
            "egolintStatus": record["egolint"]["status"],
            "egolintReportDigest": record["egolint"]["reportDigest"],
            "readmeMustMatchGitBlobSha": record["rollback"]["readmeGitBlobSha"],
            "holonMode": "exact-preview-plan",
            "credentialsEmbedded": False,
        },
        "materialization": {
            "generator": "egohygiene/holon",
            "sourcePath": ".config/holon/repository-presentation.json",
            "readmePath": "README.md",
            "statePath": ".holon/repository-presentation.state.json",
            "oneRepositoryOnly": True,
        },
        "rollback": copy.deepcopy(record["rollback"]),
        "supersession": {
            "requiresNewInventoryOnRepresentedCommitChange": True,
            "previousProposalId": None,
        },
    }
    proposal["proposalDigest"] = digest(
        {key: value for key, value in proposal.items() if key != "proposalDigest"}
    )
    return proposal


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate-inventory")
    validate.add_argument("--inventory", type=Path, default=EXAMPLE_INVENTORY)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--inventory", type=Path, default=EXAMPLE_INVENTORY)
    plan.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify-plan")
    verify.add_argument("--plan", type=Path, required=True)

    propose = subparsers.add_parser("propose")
    propose.add_argument("--plan", type=Path, required=True)
    propose.add_argument("--review", type=Path, required=True)
    propose.add_argument("--repository", required=True)
    propose.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    command = arguments.command or "validate-inventory"
    try:
        if command == "validate-inventory":
            errors = validate_inventory(load_json(getattr(arguments, "inventory", EXAMPLE_INVENTORY)))
            if errors:
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print("VALID repository-presentation fleet inventory")
            return 0
        if command == "plan":
            plan = build_plan(load_json(arguments.inventory))
            write_json(arguments.output, plan)
            print(f"WROTE no-write plan {arguments.output} ({plan['planDigest']})")
            return 0
        if command == "verify-plan":
            errors = validate_plan(load_json(arguments.plan))
            if errors:
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print(f"VALID reviewed-plan candidate {arguments.plan}")
            return 0
        if command == "propose":
            proposal = build_proposal(
                load_json(arguments.plan),
                load_json(arguments.review),
                arguments.repository,
            )
            write_json(arguments.output, proposal)
            print(f"WROTE credential-free proposal {arguments.output}")
            return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, DuplicateKeyError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

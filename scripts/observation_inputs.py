"""Bounded, offline, digest-bound source observations; never an apply adapter."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

LIMIT = 1024 * 1024
INPUT_SCHEMA = "egohygiene.pace.observation-input/v1"
LOCK_SCHEMA = "egohygiene.pace.observation-lock/v1"


def require(ok, message="Unsupported observation input"):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def parse(text):
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, "Invalid JSON constant"))


def closed(value, required, optional=()):
    require(type(value) is dict and set(required) <= value.keys()
            and value.keys() <= set(required) | set(optional))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def revision(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value))


def instant(value):
    require(isinstance(value, str))
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None)
    return parsed.astimezone(timezone.utc)


def read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "Expected a regular snapshot file")
        value = handle.read(LIMIT + 1)
    require(len(value) <= LIMIT, "Observation input exceeds byte budget")
    return value


def portable(path):
    return (isinstance(path, str) and path not in {"", "."} and "\\" not in path
            and not any(ord(char) < 32 for char in path)
            and not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts
            and str(PurePosixPath(path)) == path)


def load_pinned(snapshot_path, lock_path, kind, *, audience="public"):
    lock = parse(read(lock_path))
    closed(lock, ("schema_version", "kind", "snapshot_sha256", "target"))
    require(lock["schema_version"] == LOCK_SCHEMA and lock["kind"] == kind)
    require(isinstance(lock["snapshot_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", lock["snapshot_sha256"]))
    closed(lock["target"], ("schema_version", "authority", "repository", "revision"))
    require(lock["target"]["authority"] in {"proposed", "accepted", "unknown"})
    require(isinstance(lock["target"]["schema_version"], str)
            and re.fullmatch(r"[a-z][a-z0-9.-]+/v[0-9]+", lock["target"]["schema_version"]))
    require(isinstance(lock["target"]["repository"], str)
            and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", lock["target"]["repository"]))
    if lock["target"]["revision"] is not None:
        revision(lock["target"]["revision"])
    require(lock["target"]["authority"] != "accepted" or lock["target"]["revision"] is not None,
            "Accepted target requires an immutable source revision")
    raw = read(snapshot_path)
    require(digest(raw) == lock["snapshot_sha256"], "Snapshot digest does not match reviewed lock")
    snapshot = parse(raw)
    closed(snapshot, ("schema_version", "kind", "observed_at", "repositories"))
    require(snapshot["schema_version"] == INPUT_SCHEMA and snapshot["kind"] == kind)
    instant(snapshot["observed_at"])
    require(type(snapshot["repositories"]) is list and len(snapshot["repositories"]) <= 1000)
    seen = set()
    for row in snapshot["repositories"]:
        closed(row, ("repository", "revision", "visibility", "lifecycle", "files"), ("tags", "merge_policy"))
        name = row["repository"]
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name))
        require(name.casefold() not in seen, "Duplicate repository identity")
        seen.add(name.casefold())
        revision(row["revision"])
        require(row["visibility"] in {"public", "private", "internal"})
        require(row["lifecycle"] in {"active", "incubating", "internal", "archived", "unknown"})
        require(audience == "private" or row["visibility"] == "public",
                "Restricted inventory requires an explicit private report")
        require(type(row["files"]) is dict and len(row["files"]) <= 100)
        for path, file in row["files"].items():
            require(portable(path))
            closed(file, ("state",), ("text", "sha256"))
            require(file["state"] in {"present", "missing", "unavailable", "unknown"})
            if file["state"] == "present":
                require(set(file) == {"state", "text", "sha256"} and isinstance(file["text"], str))
                require(digest(file["text"].encode()) == file["sha256"], "Captured file digest mismatch")
            else:
                require(set(file) == {"state"})
        if "tags" in row:
            closed(row["tags"], ("current", "latest"))
            require(all(value is None or (isinstance(value, str)
                        and re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", value))
                        for value in row["tags"].values()))
        if "merge_policy" in row:
            policy = row["merge_policy"]
            closed(policy, ("state",), ("allow_merge_commit", "allow_squash_merge", "allow_rebase_merge", "source"))
            require(policy["state"] in {"observed", "unknown", "unavailable"})
            if policy["state"] == "observed":
                require(set(policy) == {"state", "allow_merge_commit", "allow_squash_merge", "allow_rebase_merge", "source"})
                require(all(type(policy[key]) is bool for key in
                            ("allow_merge_commit", "allow_squash_merge", "allow_rebase_merge")))
                require(policy["source"] == f"https://api.github.com/repos/{name}")
            else:
                require(set(policy) == {"state"})
    return snapshot, lock


def captured(row, path):
    return row["files"].get(path, {"state": "unknown"})


def output(report, path):
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path is None:
        print(text, end="")
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)

#!/usr/bin/env python3
"""Verify immutable historical evidence without freezing maintained code or documentation."""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PREFIXES = ("article/assets/", "companion/results/", "companion/models/",
                     "companion/notebook/outputs/", "companion/examples/", "downloads/")
EVIDENCE_FILES = {"article/published-original.md"}


class IntegrityError(RuntimeError):
    """Raised when a repository evidence input or archive does not match its recorded baseline digest."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def is_historical_evidence(path: str) -> bool:
    return path in EVIDENCE_FILES or path.startswith(EVIDENCE_PREFIXES)


def load_manifest() -> dict[str, str]:
    data = json.loads((ROOT / "evidence/import-manifest.json").read_text())
    return {f["path"]: f["sha256"] for f in data["files"]}


def load_audited_files() -> dict[str, str]:
    """Byte-identical preserved evidence files, keyed by current repository path."""
    data = json.loads((ROOT / "evidence/migration-audit.json").read_text())
    return {f["destination"]: f["sha256"] for f in data["files"] if f.get("byte_identical")}


def load_archive_audits() -> dict[str, dict]:
    data = json.loads((ROOT / "evidence/migration-audit.json").read_text())
    return {a["path"]: a for a in data["archives"]}


def verify_repository_evidence(audited: dict[str, str] | None = None) -> list[str]:
    """Check selected immutable, byte-identical audited evidence against its current on-disk digest."""
    audited = load_audited_files() if audited is None else audited
    mismatches = []
    for path, expected in audited.items():
        if not is_historical_evidence(path):
            continue
        full = ROOT / path
        if not full.is_file():
            mismatches.append(f"missing evidence file: {path} (expected {expected})")
            continue
        actual = sha256_file(full)
        if actual != expected:
            mismatches.append(f"evidence digest mismatch: {path} (expected {expected}, actual {actual})")
    return mismatches


def verify_all_archives() -> list[str]:
    """Verify every archive's own digest, plus every audited member's digest, for all
    manifest-recorded archives (currently both downloads/*.tar.gz bundles)."""
    manifest = load_manifest()
    audits = load_archive_audits()
    mismatches = []
    for path, expected in manifest.items():
        if not path.endswith(".tar.gz"):
            continue
        full = ROOT / path
        if not full.is_file():
            mismatches.append(f"missing archive: {path}")
            continue
        raw = full.read_bytes()
        actual = sha256_bytes(raw)
        if actual != expected:
            mismatches.append(f"archive digest mismatch: {path} (expected {expected}, actual {actual})")
            continue
        audit = audits.get(path)
        if audit is None:
            continue
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
            for member in audit["members"]:
                try:
                    extracted = tf.extractfile(member["path"])
                    data = extracted.read() if extracted is not None else None
                except KeyError:
                    data = None
                if data is None:
                    mismatches.append(f"archive member missing: {path}!{member['path']}")
                    continue
                actual_member = sha256_bytes(data)
                if actual_member != member["sha256"]:
                    mismatches.append(f"archive member digest mismatch: {path}!{member['path']} "
                                       f"(expected {member['sha256']}, actual {actual_member})")
    return mismatches


def verify_historical_protocol() -> list[str]:
    archive = "downloads/msms-shortlist-results.tar.gz"
    members = {m["path"]: m["sha256"] for m in load_archive_audits()[archive]["members"]}
    copies = {
        "protocol-frozen-original.md": "protocol-frozen-original.md",
        "protocol-with-amendments.md": "protocol.md",
        "protocol-freeze-receipt.txt": "protocol-freeze-receipt.txt",
    }
    errors = []
    for copy, source in copies.items():
        path = ROOT / "protocol/historical" / copy
        expected = members["msms-shortlist-results/protocol/" + source]
        if not path.is_file() or sha256_file(path) != expected:
            errors.append(f"historical protocol digest mismatch or missing file: {path.relative_to(ROOT)}")
    return errors


def verify_or_fail(label: str) -> None:
    """Verify all repository evidence and archives; raise IntegrityError with every
    mismatch found (not just the first), actionable by path, if any do not match."""
    mismatches = verify_repository_evidence() + verify_all_archives() + verify_historical_protocol()
    if mismatches:
        raise IntegrityError(f"{label}: repository evidence does not match recorded baseline digests:\n  "
                              + "\n  ".join(mismatches))


if __name__ == "__main__":
    import sys
    try:
        verify_or_fail("evidence_integrity")
    except IntegrityError as exc:
        sys.exit(str(exc))
    print("evidence integrity: all repository evidence and archives match recorded baseline digests")

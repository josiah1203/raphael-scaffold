#!/usr/bin/env python3
"""Scan Raphael service src/ trees for production stub patterns.

Rules (non-test src/ only):
  stub_planner          — stub_planner import or call in service code
  not_implemented_error — raise NotImplementedError (excludes abstract SDK bases)
  in_memory_event_sink  — InMemoryEventSink() instantiation in routes modules
  module_state_dict     — module-level _state = {...} without persistence layer
  stub_backend_default  — RAPHAEL_MODEL_BACKEND defaulting to stub in production code
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RULE_STUB_PLANNER = "stub_planner"
RULE_NOT_IMPLEMENTED = "not_implemented_error"
RULE_IN_MEMORY_SINK = "in_memory_event_sink"
RULE_MODULE_STATE = "module_state_dict"
RULE_STUB_BACKEND = "stub_backend_default"

RE_STUB_PLANNER = re.compile(r"\bstub_planner\b")
RE_NOT_IMPLEMENTED = re.compile(r"raise\s+NotImplementedError")
RE_IN_MEMORY_SINK = re.compile(r"InMemoryEventSink\s*\(\s*\)")
RE_MODULE_STATE = re.compile(r"^_[a-z_]+\s*=\s*\{", re.MULTILINE)
RE_STUB_BACKEND = re.compile(
    r'RAPHAEL_MODEL_BACKEND["\']?\s*,\s*["\']stub["\']|'
    r'get\s*\(\s*["\']RAPHAEL_MODEL_BACKEND["\']\s*,\s*["\']stub["\']',
)

# Abstract/protocol NotImplementedError in SDK base classes is allowed.
_SDK_BASE_SUFFIXES = ("sdk/base.py", "sdk\\base.py")


@dataclass(frozen=True)
class Violation:
    repo: str
    file: str
    rule: str
    line: int
    snippet: str

    def key(self) -> tuple[str, str, str, int]:
        return (self.repo, self.file, self.rule, self.line)


def _load_manifest_repos(scaffold_root: Path) -> list[str]:
    manifest_path = scaffold_root / "polyrepo-manifest.json"
    if not manifest_path.is_file():
        return []
    data = json.loads(manifest_path.read_text())
    deprecated = set(data.get("deprecated", []))
    return [r["name"] for r in data.get("repos", []) if r["name"] not in deprecated and r["name"] != "raphael-scaffold"]


def _is_routes_module(path: Path) -> bool:
    return path.name == "routes.py" or path.stem == "routes"


def _skip_not_implemented(path: Path, line: str) -> bool:
    normalized = str(path).replace("\\", "/")
    if any(normalized.endswith(suffix) for suffix in _SDK_BASE_SUFFIXES):
        return True
    if "class " in line and "NotImplementedError" not in line:
        return False
    return False


def scan_file(repo: str, rel_path: str, text: str) -> list[Violation]:
    path = Path(rel_path)
    violations: list[Violation] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if RE_STUB_PLANNER.search(line):
            violations.append(
                Violation(repo, rel_path, RULE_STUB_PLANNER, idx, stripped[:120])
            )

        if RE_NOT_IMPLEMENTED.search(line) and not _skip_not_implemented(path, line):
            violations.append(
                Violation(repo, rel_path, RULE_NOT_IMPLEMENTED, idx, stripped[:120])
            )

        if RE_IN_MEMORY_SINK.search(line) and _is_routes_module(path):
            violations.append(
                Violation(repo, rel_path, RULE_IN_MEMORY_SINK, idx, stripped[:120])
            )

        if RE_STUB_BACKEND.search(line):
            violations.append(
                Violation(repo, rel_path, RULE_STUB_BACKEND, idx, stripped[:120])
            )

    for match in RE_MODULE_STATE.finditer(text):
        line_no = text[: match.start()].count("\n") + 1
        snippet = lines[line_no - 1].strip()[:120]
        if "_state" in match.group(0):
            violations.append(
                Violation(repo, rel_path, RULE_MODULE_STATE, line_no, snippet)
            )

    return violations


def scan_repo(projects_root: Path, repo: str) -> list[Violation]:
    src_dir = projects_root / repo / "src"
    if not src_dir.is_dir():
        return []
    found: list[Violation] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        rel = py_file.relative_to(projects_root / repo).as_posix()
        text = py_file.read_text(encoding="utf-8", errors="replace")
        found.extend(scan_file(repo, rel, text))
    return found


def scan_all(projects_root: Path, scaffold_root: Path, repos: list[str] | None = None) -> list[Violation]:
    target_repos = repos or _load_manifest_repos(scaffold_root)
    violations: list[Violation] = []
    for repo in target_repos:
        violations.extend(scan_repo(projects_root, repo))
    return sorted(violations, key=lambda v: (v.repo, v.file, v.line, v.rule))


def load_allowlist(path: Path) -> set[tuple[str, str, str, int]]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text())
    allowed: set[tuple[str, str, str, int]] = set()
    for entry in data.get("violations", []):
        allowed.add((entry["repo"], entry["file"], entry["rule"], int(entry["line"])))
    return allowed


def partition_violations(
    violations: list[Violation], allowlist: set[tuple[str, str, str, int]]
) -> tuple[list[Violation], list[Violation]]:
    known: list[Violation] = []
    new: list[Violation] = []
    for v in violations:
        if v.key() in allowlist:
            known.append(v)
        else:
            new.append(v)
    return known, new


def format_violation(v: Violation) -> str:
    return f"{v.repo}:{v.file}:{v.line} [{v.rule}] {v.snippet}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate production stub patterns in Raphael src/ trees.")
    parser.add_argument(
        "--projects-root",
        default=os.environ.get("RAPHAEL_PROJECTS_ROOT", os.path.expanduser("~/Projects")),
        help="Root directory containing sibling Raphael repos",
    )
    parser.add_argument(
        "--scaffold-root",
        default=Path(__file__).resolve().parent.parent,
        help="raphael-scaffold directory (for manifest + allowlist)",
    )
    parser.add_argument(
        "--allowlist",
        default=None,
        help="JSON allowlist path (default: scripts/stub-gate-allowlist.json)",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit 1 when violations exist outside the allowlist",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report",
    )
    args = parser.parse_args(argv)

    projects_root = Path(args.projects_root).expanduser()
    scaffold_root = Path(args.scaffold_root).resolve()
    allowlist_path = Path(args.allowlist) if args.allowlist else scaffold_root / "scripts" / "stub-gate-allowlist.json"

    violations = scan_all(projects_root, scaffold_root)
    allowlist = load_allowlist(allowlist_path)
    known, new = partition_violations(violations, allowlist)

    if args.json:
        payload = {
            "total": len(violations),
            "known": [asdict(v) for v in known],
            "new": [asdict(v) for v in new],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"stub-gate: {len(violations)} total, {len(known)} allowlisted, {len(new)} new")
        for v in violations:
            tag = "KNOWN" if v.key() in allowlist else "NEW"
            print(f"  [{tag}] {format_violation(v)}")

    if args.fail and new:
        print(f"\nstub-gate FAILED: {len(new)} new violation(s) outside allowlist", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

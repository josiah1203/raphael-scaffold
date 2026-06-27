"""Tests for scripts/stub-gate.py production stub scanner."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

SCAFFOLD_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SCAFFOLD_ROOT / "scripts"
_STUB_GATE_PATH = SCRIPTS / "stub-gate.py"


def _load_stub_gate():
    spec = importlib.util.spec_from_file_location("stub_gate", _STUB_GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys

    sys.modules["stub_gate"] = module
    spec.loader.exec_module(module)
    return module


stub_gate = _load_stub_gate()


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "raphael-sample"
    src = repo / "src" / "raphael_sample"
    src.mkdir(parents=True)
    (src / "routes.py").write_text(
        "from sdk import InMemoryEventSink\n\n"
        "_state = {'status': 'synced'}\n"
        "_sink = InMemoryEventSink()\n"
    )
    (src / "service.py").write_text(
        "from planner import stub_planner\n\n"
        "def plan(q: str) -> None:\n"
        "    stub_planner(q)\n"
    )
    (src / "handlers.py").write_text(
        'def enroll() -> None:\n    raise NotImplementedError("deferred")\n'
    )
    (src / "runtime.py").write_text(
        'import os\n\n'
        'backend = os.environ.get("RAPHAEL_MODEL_BACKEND", "stub")\n'
    )
    return repo


def test_scan_repo_detects_all_rules(sample_repo: Path) -> None:
    hits = stub_gate.scan_repo(sample_repo.parent, "raphael-sample")
    rules = {v.rule for v in hits}
    assert stub_gate.RULE_STUB_PLANNER in rules
    assert stub_gate.RULE_NOT_IMPLEMENTED in rules
    assert stub_gate.RULE_IN_MEMORY_SINK in rules
    assert stub_gate.RULE_MODULE_STATE in rules
    assert stub_gate.RULE_STUB_BACKEND in rules


def test_abstract_sdk_not_implemented_excluded(tmp_path: Path) -> None:
    repo = tmp_path / "raphael-sdk"
    base = repo / "src" / "raphael_sdk" / "sdk"
    base.mkdir(parents=True)
    (base / "base.py").write_text(
        "class Adapter:\n    def run(self):\n        raise NotImplementedError\n"
    )
    hits = stub_gate.scan_repo(tmp_path, "raphael-sdk")
    assert hits == []


def test_allowlist_partitions_new_violations(sample_repo: Path) -> None:
    hits = stub_gate.scan_repo(sample_repo.parent, "raphael-sample")
    allowlist = {hits[0].key()}
    known, new = stub_gate.partition_violations(hits, allowlist)
    assert len(known) == 1
    assert len(new) == len(hits) - 1


def test_main_fail_on_new_violation(sample_repo: Path, tmp_path: Path) -> None:
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(json.dumps({"violations": []}))
    manifest = tmp_path / "polyrepo-manifest.json"
    manifest.write_text(
        json.dumps({"repos": [{"name": "raphael-sample"}], "deprecated": []})
    )
    code = stub_gate.main(
        [
            "--projects-root",
            str(sample_repo.parent),
            "--scaffold-root",
            str(tmp_path),
            "--allowlist",
            str(allowlist),
            "--fail",
        ]
    )
    assert code == 1


def test_main_passes_when_fully_allowlisted(sample_repo: Path, tmp_path: Path) -> None:
    hits = stub_gate.scan_repo(sample_repo.parent, "raphael-sample")
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(
        json.dumps(
            {
                "violations": [
                    {"repo": v.repo, "file": v.file, "rule": v.rule, "line": v.line}
                    for v in hits
                ]
            }
        )
    )
    manifest = tmp_path / "polyrepo-manifest.json"
    manifest.write_text(
        json.dumps({"repos": [{"name": "raphael-sample"}], "deprecated": []})
    )
    code = stub_gate.main(
        [
            "--projects-root",
            str(sample_repo.parent),
            "--scaffold-root",
            str(tmp_path),
            "--allowlist",
            str(allowlist),
            "--fail",
        ]
    )
    assert code == 0


def test_baseline_allowlist_covers_current_platform() -> None:
    """Regression: allowlist must exactly match current known stub inventory."""
    projects_root = Path(os.environ.get("RAPHAEL_PROJECTS_ROOT", Path.home() / "Projects"))
    allowlist_path = SCRIPTS / "stub-gate-allowlist.json"
    allowlist = stub_gate.load_allowlist(allowlist_path)
    hits = stub_gate.scan_all(projects_root, SCAFFOLD_ROOT)
    keys = {v.key() for v in hits}
    assert keys == allowlist, f"allowlist drift: missing={keys - allowlist} extra={allowlist - keys}"

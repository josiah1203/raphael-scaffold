#!/usr/bin/env python3
"""Copy Calliope package trees into Raphael services with import rewrites."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

CALLIOPE = Path.home() / "calliope" / "packages"
PROJECTS = Path.home() / "Projects"


@dataclass(frozen=True)
class PortEntry:
    key: str
    src: Path
    dst: Path
    rewrites: tuple[tuple[str, str], ...] = ()


BASE_REWRITES: tuple[tuple[str, str], ...] = (
    (r"\bcalliope_vcs\b", "raphael_workspaces.vcs"),
    (r"\bcalliope_delta\b", "raphael_workspaces.delta"),
    (r"\bcalliope_adapters\b", "raphael_connectors.adapters"),
    (r"\bcalliope_adapter_sdk\b", "raphael_connectors.sdk"),
    (r"\bcalliope_core\.graph\b", "raphael_graph.calliope_graph"),
    (r"\bcalliope_core\.ai\b", "raphael_ai.calliope_ai"),
    (r"\bcalliope_core\.ops\b", "raphael_ops.calliope_ops"),
    (r"\bcalliope_core\.compliance\b", "raphael_admin.compliance"),
    (r"\bcalliope_core\b", "raphael_audit.core"),
    (r"\bcalliope_agent\b", "raphael_sync.calliope_agent"),
    (r"\bplane_agent\b", "raphael_sync.plane_agent"),
    (r"\bcalliope_schema\b", "raphael_artifacts.calliope_schema"),
    (r"\bcalliope_silver\b", "raphael_artifacts.calliope_silver"),
    (r"\bhblabs_platform\.auth\b", "raphael_identity.hblabs.auth"),
    (r"\bhblabs_platform\.rbac\b", "raphael_orgs.hblabs.rbac"),
    (r"\bhblabs_platform\b", "raphael_identity.hblabs"),
)

PACKAGE_MAP: tuple[PortEntry, ...] = (
    PortEntry(
        "raphael-workspaces:vcs",
        CALLIOPE / "calliope-vcs" / "src" / "calliope_vcs",
        PROJECTS / "raphael-workspaces" / "src" / "raphael_workspaces" / "vcs",
        rewrites=((r"\bcalliope_core\.paths\b", "raphael_workspaces.paths"),),
    ),
    PortEntry(
        "raphael-workspaces:delta",
        CALLIOPE / "calliope-delta" / "src" / "calliope_delta",
        PROJECTS / "raphael-workspaces" / "src" / "raphael_workspaces" / "delta",
        rewrites=((r"\bcalliope_schema\.common_mapper\b", "raphael_workspaces.delta.mapper"),),
    ),
    PortEntry(
        "raphael-connectors:adapters",
        CALLIOPE / "calliope-adapters" / "src" / "calliope_adapters",
        PROJECTS / "raphael-connectors" / "src" / "raphael_connectors" / "adapters",
    ),
    PortEntry(
        "raphael-connectors:sdk",
        CALLIOPE / "calliope-adapter-sdk" / "src" / "calliope_adapter_sdk",
        PROJECTS / "raphael-connectors" / "src" / "raphael_connectors" / "sdk",
    ),
    PortEntry(
        "raphael-audit:core",
        CALLIOPE / "calliope-core" / "src" / "calliope_core",
        PROJECTS / "raphael-audit" / "src" / "raphael_audit" / "core",
    ),
    PortEntry(
        "raphael-graph",
        CALLIOPE / "calliope-core" / "src" / "calliope_core" / "graph",
        PROJECTS / "raphael-graph" / "src" / "raphael_graph" / "calliope_graph",
    ),
    PortEntry(
        "raphael-ai",
        CALLIOPE / "calliope-core" / "src" / "calliope_core" / "ai",
        PROJECTS / "raphael-ai" / "src" / "raphael_ai" / "calliope_ai",
    ),
    PortEntry(
        "raphael-admin:compliance",
        CALLIOPE / "calliope-core" / "src" / "calliope_core" / "compliance",
        PROJECTS / "raphael-admin" / "src" / "raphael_admin" / "compliance",
    ),
    PortEntry(
        "raphael-ops",
        CALLIOPE / "calliope-core" / "src" / "calliope_core" / "ops",
        PROJECTS / "raphael-ops" / "src" / "raphael_ops" / "calliope_ops",
    ),
    PortEntry(
        "raphael-artifacts:silver",
        CALLIOPE / "calliope-silver" / "src" / "calliope_silver",
        PROJECTS / "raphael-artifacts" / "src" / "raphael_artifacts" / "calliope_silver",
    ),
    PortEntry(
        "raphael-artifacts:schema",
        CALLIOPE / "calliope-schema" / "src" / "calliope_schema",
        PROJECTS / "raphael-artifacts" / "src" / "raphael_artifacts" / "calliope_schema",
    ),
    PortEntry(
        "raphael-sync:calliope-agent",
        CALLIOPE / "calliope-agent" / "src" / "calliope_agent",
        PROJECTS / "raphael-sync" / "src" / "raphael_sync" / "calliope_agent",
    ),
    PortEntry(
        "raphael-sync:plane-agent",
        CALLIOPE / "plane-agent" / "src" / "plane_agent",
        PROJECTS / "raphael-sync" / "src" / "raphael_sync" / "plane_agent",
    ),
    PortEntry(
        "raphael-identity:hblabs-auth",
        CALLIOPE / "hblabs-platform" / "src" / "hblabs_platform" / "auth",
        PROJECTS / "raphael-identity" / "src" / "raphael_identity" / "hblabs" / "auth",
    ),
    PortEntry(
        "raphael-orgs:hblabs-rbac",
        CALLIOPE / "hblabs-platform" / "src" / "hblabs_platform" / "rbac",
        PROJECTS / "raphael-orgs" / "src" / "raphael_orgs" / "hblabs" / "rbac",
    ),
    PortEntry(
        "raphael-orgs:hblabs-db",
        CALLIOPE / "hblabs-platform" / "src" / "hblabs_platform" / "db.py",
        PROJECTS / "raphael-orgs" / "src" / "raphael_orgs" / "hblabs" / "db.py",
    ),
)


def _apply_rewrites(dst: Path, rewrites: tuple[tuple[str, str], ...]) -> None:
    for py in dst.rglob("*.py"):
        text = py.read_text()
        for old, new in rewrites:
            text = re.sub(old, new, text)
        py.write_text(text)


def _copy_entry(entry: PortEntry, dry_run: bool = False) -> None:
    if not entry.src.exists():
        print(f"SKIP missing source: {entry.key} <- {entry.src}")
        return
    print(f"PORT {entry.key}: {entry.src} -> {entry.dst}")
    if dry_run:
        return

    if entry.src.is_dir():
        if entry.dst.exists():
            shutil.rmtree(entry.dst)
        shutil.copytree(entry.src, entry.dst)
        _apply_rewrites(entry.dst, BASE_REWRITES + entry.rewrites)
    else:
        entry.dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.src, entry.dst)
        text = entry.dst.read_text()
        for old, new in BASE_REWRITES + entry.rewrites:
            text = re.sub(old, new, text)
        entry.dst.write_text(text)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Filter by package key prefix (repeatable, comma-separated supported).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned copy operations without writing files.",
    )
    return parser.parse_args()


def _normalize_only(raw_values: list[str]) -> set[str]:
    selected: set[str] = set()
    for raw in raw_values:
        for part in raw.split(","):
            part = part.strip()
            if part:
                selected.add(part)
    return selected


def main() -> int:
    args = _parse_args()
    selected = _normalize_only(args.only)

    if not CALLIOPE.exists():
        print(f"Calliope packages not found at {CALLIOPE}", file=sys.stderr)
        return 1

    entries = PACKAGE_MAP
    if selected:
        entries = tuple(
            entry
            for entry in PACKAGE_MAP
            if any(
                entry.key == name
                or entry.key.startswith(f"{name}:")
                or entry.key.startswith(name)
                for name in selected
            )
        )
        if not entries:
            print(f"No package map entries matched --only={','.join(sorted(selected))}", file=sys.stderr)
            return 2

    for entry in entries:
        _copy_entry(entry, dry_run=args.dry_run)

    print(f"Completed {len(entries)} package mapping(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

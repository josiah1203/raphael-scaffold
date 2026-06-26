#!/usr/bin/env python3
"""Copy Calliope package trees into Raphael services with import rewrites."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

CALLOPE = Path.home() / "calliope" / "packages"
PROJECTS = Path.home() / "Projects"

REWRITES = [
    (r"from calliope_vcs", "from raphael_workspaces.vcs"),
    (r"import calliope_vcs", "import raphael_workspaces.vcs"),
    (r"from calliope_delta", "from raphael_workspaces.delta"),
    (r"import calliope_delta", "import raphael_workspaces.delta"),
    (r"from calliope_adapters", "from raphael_connectors.adapters"),
    (r"from calliope_adapter_sdk", "from raphael_connectors.sdk"),
    (r"from calliope_core", "from raphael_audit.calliope_core"),
    (r"from hblabs_platform", "from raphael_identity.hblabs"),
]


def copy_tree(src: Path, dst: Path, rewrites: list[tuple[str, str]] | None = None) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for py in dst.rglob("*.py"):
        text = py.read_text()
        for old, new in rewrites or REWRITES:
            text = re.sub(old, new, text)
        py.write_text(text)


def port_vcs() -> None:
    ws = PROJECTS / "raphael-workspaces" / "src" / "raphael_workspaces"
    copy_tree(CALLOPE / "calliope-vcs" / "src" / "calliope_vcs", ws / "vcs", [])
    copy_tree(CALLOPE / "calliope-delta" / "src" / "calliope_delta", ws / "delta", [])
    # fix internal imports
    for py in (ws / "vcs").rglob("*.py"):
        t = py.read_text()
        t = t.replace("from calliope_delta", "from raphael_workspaces.delta")
        t = t.replace("from calliope_core.paths import calliope_home", "from raphael_workspaces.paths import raphael_home")
        py.write_text(t)
    for py in (ws / "delta").rglob("*.py"):
        t = py.read_text()
        t = t.replace("from calliope_schema.common_mapper", "from raphael_workspaces.delta.mapper")
        py.write_text(t)


def port_adapters() -> None:
    conn = PROJECTS / "raphael-connectors" / "src" / "raphael_connectors"
    copy_tree(CALLOPE / "calliope-adapters" / "src" / "calliope_adapters", conn / "adapters")
    sdk_src = CALLOPE / "calliope-adapter-sdk" / "src" / "calliope_adapter_sdk"
    if sdk_src.exists():
        copy_tree(sdk_src, conn / "sdk")


def main() -> int:
    if not CALLOPE.exists():
        print(f"Calliope not found at {CALLOPE}", file=sys.stderr)
        return 1
    port_vcs()
    port_adapters()
    print("Ported VCS/delta -> raphael-workspaces, adapters -> raphael-connectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())

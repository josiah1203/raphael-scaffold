#!/usr/bin/env python3
"""Checkout sibling Raphael repos for CI (manifest-driven)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    manifest_path = Path(__file__).resolve().parent / "polyrepo-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    root = Path(os.environ.get(manifest["projects_root_env"], manifest["default_projects_root"])).expanduser()
    org = os.environ.get("RAPHAEL_GITHUB_ORG", "hummingbird-labs")
    missing: list[str] = []

    for repo in manifest["repos"]:
        name = repo["name"]
        path = root / name
        if path.is_dir():
            continue
        if not repo.get("required", True):
            continue
        missing.append(name)
        url = f"https://github.com/{org}/{name}.git"
        subprocess.run(["git", "clone", "--depth", "1", url, str(path)], check=False)

    still_missing = [n for n in missing if not (root / n).is_dir()]
    if still_missing:
        print("Missing required repos (set RAPHAEL_PROJECTS_ROOT or pre-clone siblings):", ", ".join(still_missing))
        return 1
    print(f"Polyrepo ready under {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

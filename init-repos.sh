#!/usr/bin/env python3
"""Initialize git repos and create GitHub repos via gh CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECTS = Path.home() / "Projects"
REPOS = sorted(PROJECTS.glob("raphael-*"))

ORG = "hummingbird-labs"  # ponytail: falls back to user account if org missing


def git_init_commit(path: Path) -> None:
    if not (path / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True)
    if status.stdout.strip():
        subprocess.run(
            ["git", "commit", "-m", "chore: initial Raphael polyrepo scaffold"],
            cwd=path,
            check=True,
            capture_output=True,
        )


def gh_create(name: str, path: Path) -> None:
    desc = f"Raphael Platform — {name}"
    result = subprocess.run(
        ["gh", "repo", "create", f"{ORG}/{name}", "--private", "--source", str(path), "--remote", "origin", "--description", desc, "--push"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        # try without org prefix (user account)
        subprocess.run(
            ["gh", "repo", "create", name, "--private", "--source", str(path), "--remote", "origin", "--description", desc, "--push"],
            capture_output=True,
        )


def main() -> None:
    for path in REPOS:
        if not path.is_dir():
            continue
        print(f"init {path.name}")
        git_init_commit(path)
    print(f"initialized {len(REPOS)} repos")


if __name__ == "__main__":
    main()

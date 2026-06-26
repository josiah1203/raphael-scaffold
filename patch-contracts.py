#!/usr/bin/env python3
"""Add local raphael-contracts path source to all service pyprojects."""

from pathlib import Path

PROJECTS = Path.home() / "Projects"
SNIPPET = """
[tool.uv.sources]
raphael-contracts = { path = "../raphael-contracts", editable = true }
"""

for pyproject in PROJECTS.glob("raphael-*/pyproject.toml"):
    if pyproject.parent.name in ("raphael-contracts", "raphael-infra", "raphael-devplatform", "raphael-ui"):
        continue
    text = pyproject.read_text()
    if "[tool.uv.sources]" in text:
        continue
    if "[tool.ruff]" in text:
        text = text.replace("[tool.ruff]", SNIPPET + "\n[tool.ruff]")
    else:
        text += SNIPPET
    pyproject.write_text(text)
    print(f"patched {pyproject.parent.name}")

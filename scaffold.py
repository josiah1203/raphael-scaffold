#!/usr/bin/env python3
"""Scaffold all @hummingbird/raphael-* polyrepo services."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECTS = Path(os.environ.get("RAPHAEL_PROJECTS_ROOT", Path.home() / "Projects"))

SERVICES: list[dict] = [
    {"name": "raphael-contracts", "kind": "contracts", "api_prefix": None, "port": None,
     "description": "Shared OpenAPI schemas, event envelopes, auth context, error contracts"},
    {"name": "raphael-core", "kind": "gateway", "api_prefix": "/v1", "port": 8080,
     "description": "API gateway — routing, auth middleware, rate limiting, compat shims"},
    {"name": "raphael-identity", "kind": "service", "api_prefix": "/v1/identity", "port": 8081,
     "description": "Login, SSO, MFA, sessions, devices, API keys"},
    {"name": "raphael-orgs", "kind": "service", "api_prefix": "/v1/orgs", "port": 8082,
     "description": "Organizations, memberships, invites, billing hierarchy"},
    {"name": "raphael-workspaces", "kind": "service", "api_prefix": "/v1/workspaces", "port": 8083,
     "description": "Workspaces, modules, commits, diffs, branching, history"},
    {"name": "raphael-artifacts", "kind": "service", "api_prefix": "/v1/artifacts", "port": 8084,
     "description": "Artifact CRUD, metadata, lifecycle, snapshots"},
    {"name": "raphael-slice", "kind": "service", "api_prefix": "/v1/slice", "port": 8085,
     "description": "Forking, slicing, lineage, attribution"},
    {"name": "raphael-licensing", "kind": "service", "api_prefix": "/v1/licensing", "port": 8086,
     "description": "License templates, propagation, royalties"},
    {"name": "raphael-reviews", "kind": "service", "api_prefix": "/v1/reviews", "port": 8087,
     "description": "Review requests, gates, threads, merge workflows"},
    {"name": "raphael-comments", "kind": "service", "api_prefix": "/v1/comments", "port": 8088,
     "description": "Inline comments, threads, mentions, tagging"},
    {"name": "raphael-messaging", "kind": "service", "api_prefix": "/v1/messaging", "port": 8089,
     "description": "DMs, group channels, workspace channels"},
    {"name": "raphael-notifications", "kind": "service", "api_prefix": "/v1/notifications", "port": 8090,
     "description": "In-app inbox, preferences, email/push routing via external providers"},
    {"name": "raphael-links", "kind": "service", "api_prefix": "/v1/links", "port": 8091,
     "description": "Share links, expiring links, external access"},
    {"name": "raphael-search", "kind": "service", "api_prefix": "/v1/search", "port": 8092,
     "description": "Global and scoped search, semantic search"},
    {"name": "raphael-audit", "kind": "service", "api_prefix": "/v1/audit", "port": 8093,
     "description": "Activity feed, audit logs, event replay"},
    {"name": "raphael-workflows", "kind": "service", "api_prefix": "/v1/workflows", "port": 8094,
     "description": "Approval/review/publish workflow engine"},
    {"name": "raphael-automation", "kind": "service", "api_prefix": "/v1/automations", "port": 8095,
     "description": "Triggers, actions, scheduling, cron jobs"},
    {"name": "raphael-connectors", "kind": "service", "api_prefix": "/v1/connectors", "port": 8096,
     "description": "Native connectors, sync jobs, credentials"},
    {"name": "raphael-registry", "kind": "service", "api_prefix": "/v1/registry", "port": 8097,
     "description": "Open publish/install for adapters, workflows, agents, templates"},
    {"name": "raphael-sync", "kind": "service", "api_prefix": "/v1/sync", "port": 8098,
     "description": "Desktop file monitoring, offline sync, conflict resolution"},
    {"name": "raphael-ai", "kind": "service", "api_prefix": "/v1/ai", "port": 8099,
     "description": "AI understanding, copilot, agents, workflow generation"},
    {"name": "raphael-graph", "kind": "service", "api_prefix": "/v1/graph", "port": 8100,
     "description": "Knowledge graph — relationships, dependencies, visualization"},
    {"name": "raphael-rwu", "kind": "service", "api_prefix": "/v1/rwu", "port": 8101,
     "description": "Raphael Work Unit execution accounting, banking, allocation"},
    {"name": "raphael-environments", "kind": "service", "api_prefix": "/v1/environments", "port": 8102,
     "description": "Dev/test/staging/prod sandbox environments"},
    {"name": "raphael-devplatform", "kind": "sdk", "api_prefix": None, "port": None,
     "description": "REST/GraphQL SDKs, webhooks, OAuth client libraries"},
    {"name": "raphael-infra", "kind": "infra", "api_prefix": None, "port": None,
     "description": "Event bus, storage, compute, Terraform, docker-compose"},
    {"name": "raphael-ops", "kind": "service", "api_prefix": "/v1/ops", "port": 8103,
     "description": "Observability, reliability, release operations"},
    {"name": "raphael-admin", "kind": "service", "api_prefix": "/v1/admin", "port": 8104,
     "description": "User/policy/billing/security/compliance administration"},
    {"name": "raphael-ui", "kind": "ui", "api_prefix": None, "port": 5173,
     "description": "Frontend shell — theme engine, navigation, command palette"},
    {"name": "raphael-analytics", "kind": "service", "api_prefix": "/v1/analytics", "port": 8105,
     "description": "Usage, business, and organizational intelligence"},
]

CI_YML = """name: ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run pytest -q
"""

DOCKERFILE = """FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system -e .
ENV RAPHAEL_SERVICE_PORT={port}
EXPOSE {port}
CMD ["uvicorn", "{module}.app:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

PYPROJECT = '''[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn>=0.27",
    "httpx>=0.27",
    "raphael-contracts>=0.1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{pkg}"]

[tool.ruff]
line-length = 100
target-version = "py311"
'''

APP_PY = '''"""Raphael service: {name}."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from raphael_contracts.errors import ErrorResponse
from {pkg}.routes import router

app = FastAPI(
    title="{title}",
    description="{description}",
    version="0.1.0",
    openapi_url="{api_prefix}/openapi.json" if "{api_prefix}" else "/openapi.json",
)

app.include_router(router, prefix="{api_prefix}" if "{api_prefix}" else "")


@app.get("/health")
def health() -> dict[str, str]:
    return {{"status": "ok", "service": "{name}"}}


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception) -> JSONResponse:
    err = ErrorResponse(code="internal_error", message=str(exc))
    return JSONResponse(status_code=500, content=err.model_dump())
'''

ROUTES_PY = '''"""API routes for {name}."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["{name}"])


@router.get("")
def list_root() -> dict[str, str]:
  return {{"service": "{name}", "status": "stub"}}
'''

OPENAPI_STUB = """openapi: 3.1.0
info:
  title: {title}
  version: 0.1.0
  description: {description}
paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: OK
"""

README = """# {title}

{description}

## API

- Prefix: `{api_prefix_display}`
- Port: `{port_display}`
- Health: `GET /health`

## Events

_Published and consumed events documented in `openapi.yaml` and raphael-contracts._

## Development

```bash
uv sync
uv run uvicorn {pkg}.app:app --reload --port {dev_port}
```

Part of the [Raphael Platform](https://github.com/hummingbird-labs) by HummingBird Labs.
"""

TEST_HEALTH = '''"""Health check tests."""

from fastapi.testclient import TestClient

from {pkg}.app import app


def test_health() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "{name}"
'''


def pkg_name(name: str) -> str:
    return name.replace("-", "_")


def git_init(path: Path) -> None:
    if (path / ".git").exists():
        return
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)


def write_service(svc: dict) -> Path:
    name = svc["name"]
    kind = svc["kind"]
    root = PROJECTS / name
    root.mkdir(parents=True, exist_ok=True)

    if kind in ("service", "gateway"):
        pkg = pkg_name(name)
        port = svc["port"]
        api_prefix = svc["api_prefix"] or ""
        (root / "src" / pkg).mkdir(parents=True, exist_ok=True)
        (root / "tests").mkdir(exist_ok=True)
        (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)

        (root / "pyproject.toml").write_text(
            PYPROJECT.format(name=name, description=svc["description"], pkg=pkg)
        )
        (root / "Dockerfile").write_text(DOCKERFILE.format(port=port, module=pkg))
        (root / ".github/workflows/ci.yml").write_text(CI_YML)
        (root / "README.md").write_text(
            README.format(
                title=name,
                description=svc["description"],
                api_prefix_display=api_prefix or "N/A",
                port_display=str(port) if port else "N/A",
                port=port or 8080,
                dev_port=port or 8080,
                pkg=pkg,
            )
        )
        (root / "openapi.yaml").write_text(
            OPENAPI_STUB.format(title=name, description=svc["description"])
        )
        (root / "src" / pkg / "__init__.py").write_text(f'"""{name} package."""\n')
        (root / "src" / pkg / "app.py").write_text(
            APP_PY.format(
                name=name,
                pkg=pkg,
                title=name,
                description=svc["description"],
                api_prefix=api_prefix,
            )
        )
        (root / "src" / pkg / "routes.py").write_text(ROUTES_PY.format(name=name))
        (root / "src" / pkg / "events").mkdir(exist_ok=True)
        (root / "src" / pkg / "events" / "__init__.py").write_text("")
        (root / "tests" / "test_health.py").write_text(TEST_HEALTH.format(pkg=pkg, name=name))
        (root / ".gitignore").write_text("__pycache__/\n.venv/\n*.pyc\n.pytest_cache/\n")

    elif kind == "contracts":
        # handled separately in contracts scaffold
        pass
    elif kind == "infra":
        pass
    elif kind == "sdk":
        pass
    elif kind == "ui":
        pass

    git_init(root)
    return root


def main() -> None:
    PROJECTS.mkdir(parents=True, exist_ok=True)
    for svc in SERVICES:
        if svc["kind"] in ("service", "gateway"):
            path = write_service(svc)
            print(f"scaffolded {path}")
    print(f"done: {len([s for s in SERVICES if s['kind'] in ('service', 'gateway')])} services")


if __name__ == "__main__":
    main()

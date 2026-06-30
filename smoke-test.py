#!/usr/bin/env python3
"""Integration smoke test with response body assertions.

Per-service gateway check targets (current → Wave 2 goal ≥80 total, ≥1 body
assertion per active service):

  Service              Port  Current checks (via gateway unless noted)
  -------------------  ----  ------------------------------------------
  raphael-core         8080  config×3, health, metrics, request-id echo
  raphael-identity     8081  login, register (+ direct /health)
  raphael-orgs         8082  list orgs, members/invites/keys/join (flow)
  raphael-workspaces   8083  modules list, repos, projects, module files×11
  raphael-reviews      8087  GET /v1/reviews
  raphael-comments     8088  GET /v1/comments, POST /v1/comments
  raphael-messaging    8089  GET /v1/messaging, POST /v1/messaging
  raphael-notifications 8090  POST /v1/notifications/events, GET /v1/notifications
  raphael-links        8091  GET /v1/links
  raphael-audit        8093  timeline×3, verify, POST event (+ direct /health)
  raphael-automation   8095  GET /v1/automations (+ direct /health)
  raphael-connectors   8096  GET /v1/connectors, POST webhook ingest
  raphael-registry     8097  GET /v1/registry, POST /v1/registry
  raphael-sync         8098  GET /v1/sync
  raphael-graph        8100  GET edges, POST dedup×2
  raphael-rwu          8101  GET /v1/rwu/balance, POST /v1/rwu/consume
  raphael-environments 8102  GET /v1/environments, POST /v1/environments
  raphael-ops          8103  GET /v1/ops, replay, verify-integrity, backup
  raphael-ai           8104  intelligence ask/draft/memory/status×3, jobs
  raphael-analytics    8105  GET /v1/analytics/overview
  raphael-admin        8106  GET billing, GET iam/holds
  raphael-artifacts    8107  GET /v1/artifacts

Runs ~50 platform/gateway checks, 11 module files/settings checks, and up to 5
org-admin checks when the org bootstrap flow succeeds (66 total baseline).
Wave 2 target: 80+ checks with POST/create coverage for tier-2 holes above.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import uuid

import httpx
from pathlib import Path

SERVICES = [
    ("raphael-identity", 8081, "raphael_identity.app:app"),
    ("raphael-orgs", 8082, "raphael_orgs.app:app"),
    ("raphael-workspaces", 8083, "raphael_workspaces.app:app"),
    ("raphael-reviews", 8087, "raphael_reviews.app:app"),
    ("raphael-notifications", 8090, "raphael_notifications.app:app"),
    ("raphael-automation", 8095, "raphael_automation.app:app"),
    ("raphael-connectors", 8096, "raphael_connectors.app:app"),
    ("raphael-audit", 8093, "raphael_audit.app:app"),
    ("raphael-artifacts", 8107, "raphael_artifacts.app:app"),
    ("raphael-graph", 8100, "raphael_graph.app:app"),
    ("raphael-ai", 8104, "raphael_ai.app:app"),
    ("raphael-sync", 8098, "raphael_sync.app:app"),
    ("raphael-ops", 8103, "raphael_ops.app:app"),
    ("raphael-admin", 8106, "raphael_admin.app:app"),
    ("raphael-rwu", 8101, "raphael_rwu.app:app"),
    ("raphael-comments", 8088, "raphael_comments.app:app"),
    ("raphael-messaging", 8089, "raphael_messaging.app:app"),
    ("raphael-links", 8091, "raphael_links.app:app"),
    ("raphael-registry", 8097, "raphael_registry.app:app"),
    ("raphael-environments", 8102, "raphael_environments.app:app"),
    ("raphael-analytics", 8105, "raphael_analytics.app:app"),
]

PROJECTS_ROOT = Path(os.environ.get("RAPHAEL_PROJECTS_ROOT", os.path.expanduser("~/Projects")))

SMOKE_PORTS = sorted({port for _, port, _ in SERVICES} | {8080})


def free_smoke_ports() -> None:
    """Release Raphael service ports so subprocess stack is consistent (avoids Docker split-brain)."""
    if os.environ.get("RAPHAEL_SMOKE_KEEP_PORTS"):
        return
    for port in SMOKE_PORTS:
        subprocess.run(
            ["sh", "-c", f"lsof -ti tcp:{port} -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true"],
            check=False,
        )
    time.sleep(1)


procs: list[subprocess.Popen] = []
_access_token: str | None = None
_smoke_org_id: str | None = None
_join_key: str | None = None
_smoke_module_id: str | None = None


def start(name: str, port: int, app: str) -> None:
    path = PROJECTS_ROOT / name
    env = os.environ.copy()
    env.update(
        {
            "RAPHAEL_IDENTITY_URL": "http://127.0.0.1:8081",
            "RAPHAEL_ORGS_URL": "http://127.0.0.1:8082",
            "RAPHAEL_WORKSPACES_URL": "http://127.0.0.1:8083",
            "RAPHAEL_REVIEWS_URL": "http://127.0.0.1:8087",
            "RAPHAEL_NOTIFICATIONS_URL": "http://127.0.0.1:8090",
            "RAPHAEL_AUTOMATION_URL": "http://127.0.0.1:8095",
            "RAPHAEL_CONNECTORS_URL": "http://127.0.0.1:8096",
            "RAPHAEL_AUDIT_URL": "http://127.0.0.1:8093",
            "RAPHAEL_GRAPH_URL": "http://127.0.0.1:8100",
            "RAPHAEL_AI_URL": "http://127.0.0.1:8104",
            "RAPHAEL_ADMIN_URL": "http://127.0.0.1:8106",
            "RAPHAEL_ARTIFACTS_URL": "http://127.0.0.1:8107",
            "RAPHAEL_SYNC_URL": "http://127.0.0.1:8098",
            "RAPHAEL_OPS_URL": "http://127.0.0.1:8103",
            "RAPHAEL_RWU_URL": "http://127.0.0.1:8101",
            "RAPHAEL_COMMENTS_URL": "http://127.0.0.1:8088",
            "RAPHAEL_MESSAGING_URL": "http://127.0.0.1:8089",
            "RAPHAEL_LINKS_URL": "http://127.0.0.1:8091",
            "RAPHAEL_REGISTRY_URL": "http://127.0.0.1:8097",
            "RAPHAEL_ENVIRONMENTS_URL": "http://127.0.0.1:8102",
            "RAPHAEL_ANALYTICS_URL": "http://127.0.0.1:8105",
            "RAPHAEL_MODEL_BACKEND": os.environ.get("RAPHAEL_MODEL_BACKEND", "stub"),
            "RAPHAEL_OLLAMA_URL": os.environ.get("RAPHAEL_OLLAMA_URL", "http://127.0.0.1:11434"),
            "RAPHAEL_GEMMA_MODEL": os.environ.get("RAPHAEL_GEMMA_MODEL", "gemma2:2b"),
            "RAPHAEL_JWT_SECRET": "dev-secret-with-32-byte-minimum-length!!",
            "RAPHAEL_LOG_FORMAT": "json",
            "RAPHAEL_KAFKA_DISABLED": os.environ.get("RAPHAEL_KAFKA_DISABLED", "1"),
        }
    )
    db_url = os.environ.get("RAPHAEL_DATABASE_URL")
    if db_url:
        env["RAPHAEL_DATABASE_URL"] = db_url
    procs.append(
        subprocess.Popen(
            ["uv", "run", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(path),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )


def auth_headers(client: httpx.Client) -> dict[str, str]:
    global _access_token
    if _access_token is None:
        res = client.post(
            "http://127.0.0.1:8080/v1/identity/login",
            json={"email": "dev@raphael.app", "password": "raphaeldev1"},
        )
        if res.status_code == 200:
            _access_token = res.json().get("access_token")
    if _access_token:
        return {"Authorization": f"Bearer {_access_token}"}
    return {}


def jwt_user_id(token: str | None) -> str:
    if not token:
        return f"usr_smoke_{uuid.uuid4().hex[:8]}"
    payload = token.split(".")[1]
    padding = "=" * (-len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload + padding))
    return str(data.get("sub", "usr_default"))


def org_headers(client: httpx.Client) -> dict[str, str]:
    hdrs = dict(auth_headers(client))
    if _smoke_org_id:
        hdrs["X-Raphael-Org-Id"] = _smoke_org_id
    return hdrs


def run_check(
    client: httpx.Client,
    method: str,
    url: str,
    assert_fn,
    body: dict | None = None,
    headers: dict | None = None,
    allow_4xx: bool = False,
) -> bool:
    hdrs = dict(headers or {})
    if "127.0.0.1:8080" in url and url not in (
        "http://127.0.0.1:8080/v1/identity/login",
        "http://127.0.0.1:8080/v1/identity/register",
        "http://127.0.0.1:8080/health",
        "http://127.0.0.1:8080/metrics",
        "http://127.0.0.1:8080/v1/config",
    ):
        hdrs.setdefault("X-Raphael-Request-Id", str(uuid.uuid4()))
    res = client.request(method, url, json=body, headers=hdrs)
    ok = res.status_code < 500
    if not allow_4xx:
        ok = ok and res.status_code < 400
    try:
        ok = ok and assert_fn(res)
    except (json.JSONDecodeError, KeyError, TypeError, AssertionError):
        ok = False
    print(f"{'OK' if ok else 'FAIL'} {method} {url} -> {res.status_code}")
    return ok


def setup_module_files_flow(client: httpx.Client) -> None:
    """Create a disposable module for file tree/blob/settings smoke checks."""
    global _smoke_module_id
    module_id = f"smoke-files-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "http://127.0.0.1:8080/v1/workspaces/default/modules",
        json={"id": module_id, "name": f"Smoke Files {module_id}"},
        headers=auth_headers(client),
    )
    if res.status_code == 200:
        _smoke_module_id = module_id


def module_files_checks(module_id: str, auth: dict[str, str]) -> list[tuple]:
    """Smoke checks aligned with raphael-workspaces files/settings API paths."""
    base = f"http://127.0.0.1:8080/v1/workspaces/default/modules/{module_id}"
    readme = "# Smoke README\n"
    return [
        (
            "GET",
            f"{base}/files/tree?branch=main&path=",
            lambda r: r.json().get("branch") == "main" and r.json().get("entries") == [],
            None,
            auth,
            False,
        ),
        (
            "PUT",
            f"{base}/files/blob",
            lambda r: r.json().get("path") == "README.md",
            {
                "branch": "main",
                "path": "README.md",
                "content": readme,
                "content_type": "text/markdown",
                "message": "smoke add readme",
            },
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/files/blob?branch=main&path=README.md",
            lambda r: r.json().get("content") == readme and r.json().get("is_binary") is False,
            None,
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/files/tree?branch=main&path=",
            lambda r: any(e.get("name") == "README.md" for e in r.json().get("entries", [])),
            None,
            auth,
            False,
        ),
        (
            "PUT",
            f"{base}/files/blob",
            lambda r: r.json().get("path") == "src/main.py",
            {
                "branch": "main",
                "path": "src/main.py",
                "content": "print('smoke')\n",
                "content_type": "text/x-python",
            },
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/files/tree?branch=main&path=src",
            lambda r: any(
                e.get("name") == "main.py" and e.get("kind") == "file"
                for e in r.json().get("entries", [])
            ),
            None,
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/settings",
            lambda r: r.json().get("visibility") == "private"
            and r.json().get("default_branch") == "main",
            None,
            auth,
            False,
        ),
        (
            "PATCH",
            f"{base}/settings",
            lambda r: r.json().get("description") == "Smoke test module"
            and r.json().get("artifact_type") == "design",
            {"description": "Smoke test module", "artifact_type": "design", "license": "mit"},
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/settings/collaborators",
            lambda r: isinstance(r.json().get("collaborators"), list),
            None,
            auth,
            False,
        ),
        (
            "GET",
            f"{base}/settings/webhooks",
            lambda r: isinstance(r.json().get("webhooks"), list),
            None,
            auth,
            False,
        ),
        (
            "POST",
            f"{base}/settings/branch-protection",
            lambda r: r.json().get("branch_pattern") == "main",
            {"branch_pattern": "main", "require_pr": True},
            auth,
            False,
        ),
    ]


def setup_org_flow(client: httpx.Client) -> None:
    global _access_token, _smoke_org_id, _join_key
    email = f"smoke-{uuid.uuid4().hex[:8]}@raphael.app"
    reg = client.post(
        "http://127.0.0.1:8080/v1/identity/register",
        json={"email": email, "password": "smokepass1234"},
    )
    if reg.status_code == 200:
        _access_token = reg.json().get("access_token")
    org = client.post(
        "http://127.0.0.1:8080/v1/orgs",
        json={"name": f"Smoke Org {uuid.uuid4().hex[:6]}"},
        headers=auth_headers(client),
    )
    if org.status_code == 200:
        _smoke_org_id = org.json().get("id")
    if _smoke_org_id:
        key_res = client.post(
            f"http://127.0.0.1:8080/v1/orgs/{_smoke_org_id}/connection-keys",
            json={"type": "join"},
            headers={**auth_headers(client), "X-Raphael-Org-Id": _smoke_org_id},
        )
        if key_res.status_code == 200:
            _join_key = key_res.json().get("key")


def main() -> int:
    free_smoke_ports()
    for name, port, app in SERVICES:
        start(name, port, app)
    start("raphael-core", 8080, "raphael_core.app:app")
    time.sleep(10)

    client = httpx.Client(timeout=15.0)
    setup_org_flow(client)
    auth = auth_headers(client)
    setup_module_files_flow(client)
    org_hdrs = org_headers(client)
    ollama_mode = os.environ.get("RAPHAEL_MODEL_BACKEND", "stub") == "ollama"
    notify_user = jwt_user_id(_access_token)
    notify_hdrs = auth

    checks: list[tuple] = [
        # Gateway + observability
        ("GET", "http://127.0.0.1:8080/v1/config", lambda r: r.json().get("platform_name") == "Raphael", None, None, False),
        ("GET", "http://127.0.0.1:8080/health", lambda r: r.json().get("service") == "raphael-core", None, None, False),
        ("GET", "http://127.0.0.1:8080/metrics", lambda r: b"raphael_gateway_requests_total" in r.content, None, None, False),
        ("GET", "http://127.0.0.1:8080/v1/config", lambda r: r.json().get("features", {}).get("intelligence") is True, None, None, False),
        ("GET", "http://127.0.0.1:8080/v1/config", lambda r: r.json().get("features", {}).get("automations") is True, None, None, False),
        (
            "GET",
            "http://127.0.0.1:8080/v1/workspaces/default/modules",
            lambda r: "modules" in r.json(),
            None,
            {"X-Raphael-Request-Id": "smoke-req-1"},
            False,
        ),
        (
            "GET",
            "http://127.0.0.1:8080/v1/workspaces/default/modules",
            lambda r: r.headers.get("x-raphael-request-id") == "smoke-req-1",
            None,
            {"X-Raphael-Request-Id": "smoke-req-1"},
            False,
        ),
        # Workspaces + compat
        ("GET", "http://127.0.0.1:8080/v1/repos", lambda r: "repos" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/projects", lambda r: "projects" in r.json(), None, auth, False),
        # Reviews + design workflow
        ("GET", "http://127.0.0.1:8080/v1/reviews", lambda r: isinstance(r.json().get("reviews"), list), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/automations", lambda r: "automations" in r.json(), None, auth, False),
        (
            "GET",
            "http://127.0.0.1:8080/v1/automations/runs",
            lambda r: isinstance(r.json().get("runs"), list) and len(r.json()["runs"]) >= 1,
            None,
            auth,
            False,
        ),
        ("GET", "http://127.0.0.1:8080/v1/connectors", lambda r: "connected" in r.json(), None, auth, False),
        (
            "POST",
            "http://127.0.0.1:8080/v1/connectors/webhooks/github",
            lambda r: r.status_code == 200 and r.json().get("status") == "accepted",
            {"event": "push", "repo": "smoke-test"},
            auth,
            False,
        ),
        (
            "GET",
            "http://127.0.0.1:8080/v1/connectors",
            lambda r: any(c.get("tool") == "github" for c in r.json().get("connected", [])),
            None,
            auth,
            False,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/notifications/events",
            lambda r: r.status_code == 200 and r.json().get("status") == "processed",
            {
                "type": "raphael.reviews.created",
                "data": {"title": "Smoke review", "assignee": notify_user, "email": "smoke@raphael.app"},
            },
            auth,
            False,
        ),
        (
            "GET",
            "http://127.0.0.1:8080/v1/notifications",
            lambda r: isinstance(r.json().get("notifications"), list)
            and any(n.get("type") == "raphael.reviews.created" for n in r.json().get("notifications", [])),
            None,
            notify_hdrs,
            False,
        ),
        (
            "GET",
            "http://127.0.0.1:8080/v1/notifications/preferences",
            lambda r: r.status_code == 200 and isinstance(r.json().get("reviewAlerts"), bool),
            None,
            notify_hdrs,
            False,
        ),
        ("GET", "http://127.0.0.1:8080/v1/artifacts", lambda r: "artifacts" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/graph/edges", lambda r: "edges" in r.json(), None, auth, False),
        # Events + audit pagination
        ("GET", "http://127.0.0.1:8080/v1/audit/timeline", lambda r: "events" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/audit/timeline?limit=2", lambda r: isinstance(r.json().get("events"), list), None, auth, False),
        (
            "GET",
            "http://127.0.0.1:8080/v1/audit/timeline?limit=2",
            lambda r: "next_cursor" in r.json() or r.json().get("has_more") is not None,
            None,
            auth,
            False,
        ),
        ("GET", "http://127.0.0.1:8080/v1/timeline", lambda r: "events" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/audit/verify", lambda r: "valid" in r.json() or "chain_valid" in r.json(), None, auth, True),
        (
            "POST",
            "http://127.0.0.1:8080/v1/audit/events",
            lambda r: r.status_code in (200, 201) and "event_id" in r.json(),
            {"event_type": "smoke.test", "payload": {"source": "smoke-test"}},
            auth,
            True,
        ),
        # Intelligence
        (
            "POST",
            "http://127.0.0.1:8080/v1/intelligence/ask",
            lambda r: "plan_id" in r.json() and len(r.json().get("citations", [])) > 0,
            {"question": "list modules"},
            auth,
            False,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/intelligence/workflows/draft",
            lambda r: r.json().get("draft", {}).get("trigger_type") is not None,
            {"description": "When a commit lands run DRC"},
            auth,
            False,
        ),
        ("GET", "http://127.0.0.1:8080/v1/intelligence/memory", lambda r: r.json().get("workspace_id") == "default", None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/intelligence/status", lambda r: "model_version" in r.json(), None, auth, False),
        (
            "GET",
            "http://127.0.0.1:8080/v1/intelligence/status",
            lambda r: r.json().get("model_tier") in ("stub", "live", "cached", "rule_stub", None) or "degradation" in r.json(),
            None,
            auth,
            False,
        ),
        (
            "GET",
            "http://127.0.0.1:8080/v1/intelligence/status",
            lambda r: (not ollama_mode) or r.json().get("model_tier") != "rule_stub",
            None,
            auth,
            ollama_mode,
        ),
        ("GET", "http://127.0.0.1:8080/v1/ai/jobs", lambda r: "jobs" in r.json(), None, auth, False),
        # Platform admin + orgs
        ("GET", "http://127.0.0.1:8080/v1/orgs", lambda r: "orgs" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/admin/billing", lambda r: "plan" in r.json(), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/admin/iam/holds", lambda r: "holds" in r.json(), None, auth, False),
        # Ops
        ("GET", "http://127.0.0.1:8080/v1/ops", lambda r: r.status_code == 200 and r.json().get("service") == "raphael-ops", None, auth, False),
        ("POST", "http://127.0.0.1:8080/v1/ops/replay", lambda r: r.status_code in (200, 422) and "replayed_at" in r.json(), {"event_ids": []}, auth, True),
        ("GET", "http://127.0.0.1:8080/v1/ops/verify-integrity", lambda r: "chain_valid" in r.json() or "status" in r.json(), None, auth, True),
        ("POST", "http://127.0.0.1:8080/v1/ops/backup", lambda r: "id" in r.json(), {"label": "smoke"}, auth, True),
        # RWU + sync
        ("GET", "http://127.0.0.1:8080/v1/rwu/balance", lambda r: r.status_code == 200, None, auth, True),
        ("GET", "http://127.0.0.1:8080/v1/sync", lambda r: r.json().get("service") == "raphael-sync", None, auth, False),
        ("POST", "http://127.0.0.1:8080/v1/sync/push", lambda r: r.status_code == 200 and r.json().get("accepted", 0) >= 0 and r.json().get("status") == "synced", {"events": []}, auth, True),
        (
            "POST",
            f"http://127.0.0.1:8080/v1/sync/sessions/smoke-{uuid.uuid4().hex[:8]}/commit",
            lambda r: r.status_code == 200 and r.json().get("status") == "committed",
            {"events": [{"type": "smoke.test"}]},
            auth,
            True,
        ),
        # Tier-2 domains
        ("GET", "http://127.0.0.1:8080/v1/comments", lambda r: "comments" in r.json(), None, auth, False),
        (
            "POST",
            "http://127.0.0.1:8080/v1/comments",
            lambda r: r.status_code == 200 and "id" in r.json() and r.json().get("body") == "Smoke comment",
            {
                "target_type": "review",
                "target_id": f"smoke-rev-{uuid.uuid4().hex[:8]}",
                "body": "Smoke comment",
            },
            auth,
            False,
        ),
        ("GET", "http://127.0.0.1:8080/v1/messaging", lambda r: r.status_code == 200, None, auth, True),
        (
            "POST",
            "http://127.0.0.1:8080/v1/messaging",
            lambda r: r.status_code == 200 and "id" in r.json() and r.json().get("workspace_id") == "default",
            {
                "workspace_id": "default",
                "target_type": "review",
                "target_id": f"smoke-msg-{uuid.uuid4().hex[:8]}",
                "name": "Smoke conversation",
            },
            auth,
            True,
        ),
        ("GET", "http://127.0.0.1:8080/v1/links", lambda r: r.status_code == 200, None, auth, True),
        ("GET", "http://127.0.0.1:8080/v1/registry", lambda r: r.status_code == 200, None, auth, True),
        (
            "POST",
            "http://127.0.0.1:8080/v1/registry",
            lambda r: r.status_code == 200 and r.json().get("version") == "1.0.0",
            {
                "name": f"smoke-pkg-{uuid.uuid4().hex[:8]}",
                "version": "1.0.0",
                "manifest": {"schema": "module-v1"},
            },
            auth,
            True,
        ),
        ("GET", "http://127.0.0.1:8080/v1/environments", lambda r: r.status_code == 200, None, auth, True),
        (
            "POST",
            "http://127.0.0.1:8080/v1/environments",
            lambda r: r.status_code == 200 and r.json().get("stage") == "dev",
            {
                "name": f"smoke-env-{uuid.uuid4().hex[:8]}",
                "stage": "dev",
                "config": {"region": "us-east-1"},
            },
            auth,
            True,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/rwu/consume",
            lambda r: r.status_code == 200 and "balance" in r.json(),
            {"amount": 1, "reason": "smoke"},
            org_hdrs if _smoke_org_id else {**auth, "X-Raphael-Org-Id": "org_default"},
            True,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/rwu/reserve",
            lambda r: r.status_code == 200 and r.json().get("status") == "reserved",
            {"amount": 1},
            org_hdrs if _smoke_org_id else {**auth, "X-Raphael-Org-Id": "org_default"},
            True,
        ),
        ("GET", "http://127.0.0.1:8080/v1/analytics/overview", lambda r: (
            r.status_code == 200
            and r.json().get("workspace_id")
            and "events_total" in r.json()
            and "event_types_top" in r.json()
            and r.json().get("health") == "ok"
        ), None, auth, False),
        ("GET", "http://127.0.0.1:8080/v1/analytics", lambda r: (
            r.status_code == 200
            and r.json().get("service") == "raphael-analytics"
            and isinstance(r.json().get("metrics"), list)
            and len(r.json().get("metrics", [])) >= 1
        ), None, auth, False),
        # Auth
        (
            "POST",
            "http://127.0.0.1:8080/v1/identity/login",
            lambda r: r.status_code == 200 and "access_token" in r.json(),
            {"email": "dev@raphael.app", "password": "raphaeldev1"},
            None,
            False,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/identity/register",
            lambda r: r.status_code in (200, 400),
            {"email": f"dup-{uuid.uuid4().hex}@raphael.app", "password": "smokepass1234"},
            None,
            True,
        ),
        # Direct service health (native ports)
        ("GET", "http://127.0.0.1:8081/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8090/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8101/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8106/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8093/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8104/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8082/health", lambda r: r.status_code == 200, None, None, False),
        ("GET", "http://127.0.0.1:8095/health", lambda r: r.status_code == 200, None, None, False),
        # Graph dedup
        (
            "POST",
            "http://127.0.0.1:8080/v1/graph/edges",
            lambda r: r.json().get("status") in ("created", "exists"),
            {"from_id": "smoke-a", "to_id": "smoke-b", "edge_type": "related"},
            auth,
            False,
        ),
        (
            "POST",
            "http://127.0.0.1:8080/v1/graph/edges",
            lambda r: r.json().get("status") == "exists",
            {"from_id": "smoke-a", "to_id": "smoke-b", "edge_type": "related"},
            auth,
            False,
        ),
    ]

    if _smoke_org_id:
        checks.extend(
            [
                (
                    "GET",
                    f"http://127.0.0.1:8080/v1/orgs/{_smoke_org_id}/members",
                    lambda r: isinstance(r.json().get("members"), list),
                    None,
                    org_hdrs,
                    False,
                ),
                (
                    "POST",
                    f"http://127.0.0.1:8080/v1/orgs/{_smoke_org_id}/invites",
                    lambda r: r.json().get("status") == "invite_sent",
                    {"email": "invitee@raphael.app", "role": "member"},
                    org_hdrs,
                    False,
                ),
                (
                    "GET",
                    f"http://127.0.0.1:8080/v1/orgs/{_smoke_org_id}/invites",
                    lambda r: len(r.json().get("invites", [])) >= 1,
                    None,
                    org_hdrs,
                    False,
                ),
                (
                    "GET",
                    f"http://127.0.0.1:8080/v1/orgs/{_smoke_org_id}/connection-keys",
                    lambda r: len(r.json().get("keys", [])) >= 1,
                    None,
                    org_hdrs,
                    False,
                ),
            ]
        )
    if _join_key:
        checks.append(
            (
                "POST",
                "http://127.0.0.1:8080/v1/orgs/join",
                lambda r: r.json().get("status") in ("joined", "already_member"),
                {"key": _join_key},
                auth,
                False,
            )
        )
    if _smoke_module_id:
        checks.extend(module_files_checks(_smoke_module_id, auth))

    failed = sum(
        1
        for method, url, assert_fn, body, headers, allow_4xx in checks
        if not run_check(client, method, url, assert_fn, body, headers, allow_4xx)
    )
    print(f"\n{len(checks) - failed}/{len(checks)} assertions passed")

    for p in procs:
        p.terminate()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Integration smoke test with response body assertions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import httpx

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
]

procs: list[subprocess.Popen] = []


def start(name: str, port: int, app: str) -> None:
    path = os.path.expanduser(f"~/Projects/{name}")
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
            "RAPHAEL_JWT_SECRET": "dev-secret-with-32-byte-minimum-length!!",
        }
    )
    procs.append(
        subprocess.Popen(
            ["uv", "run", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)],
            cwd=path,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )


def main() -> int:
    for name, port, app in SERVICES:
        start(name, port, app)
    start("raphael-core", 8080, "raphael_core.app:app")
    time.sleep(8)

    client = httpx.Client(timeout=10.0)
    checks: list[tuple[str, str, callable]] = [
        ("GET", "http://127.0.0.1:8080/v1/config", lambda r: r.json().get("platform_name") == "Raphael"),
        ("GET", "http://127.0.0.1:8080/v1/workspaces/default/modules", lambda r: "modules" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/repos", lambda r: "repos" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/reviews", lambda r: isinstance(r.json().get("reviews"), list)),
        ("GET", "http://127.0.0.1:8080/v1/connectors", lambda r: "connected" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/audit/timeline", lambda r: "events" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/artifacts", lambda r: "artifacts" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/ai/suggestions", lambda r: "suggestions" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/admin/billing", lambda r: "plan" in r.json()),
        ("GET", "http://127.0.0.1:8080/v1/sync", lambda r: r.status_code == 200),
        ("GET", "http://127.0.0.1:8080/v1/ops", lambda r: r.status_code == 200),
        ("GET", "http://127.0.0.1:8080/v1/rwu/balance", lambda r: r.status_code == 200),
    ]
    failed = 0
    for method, url, assert_fn in checks:
        res = client.request(method, url)
        ok = res.status_code < 500 and (res.status_code < 400 or url.endswith("/rwu/balance"))
        try:
            ok = ok and assert_fn(res)
        except (json.JSONDecodeError, KeyError):
            ok = False
        print(f"{'OK' if ok else 'FAIL'} {method} {url} -> {res.status_code}")
        if not ok:
            failed += 1

    for p in procs:
        p.terminate()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

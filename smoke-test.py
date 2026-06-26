#!/usr/bin/env python3
"""Smoke test: gateway proxies to domain services."""

from __future__ import annotations

import os
import subprocess
import sys
import time

import httpx

SERVICES = [
    ("raphael-identity", 8081, "raphael_identity.app:app"),
    ("raphael-workspaces", 8083, "raphael_workspaces.app:app"),
    ("raphael-reviews", 8087, "raphael_reviews.app:app"),
    ("raphael-notifications", 8090, "raphael_notifications.app:app"),
    ("raphael-automation", 8095, "raphael_automation.app:app"),
    ("raphael-connectors", 8096, "raphael_connectors.app:app"),
    ("raphael-audit", 8093, "raphael_audit.app:app"),
]

procs: list[subprocess.Popen] = []


def start(name: str, port: int, app: str) -> None:
    path = os.path.expanduser(f"~/Projects/{name}")
    env = os.environ.copy()
    env.update(
        {
            "RAPHAEL_IDENTITY_URL": "http://127.0.0.1:8081",
            "RAPHAEL_WORKSPACES_URL": "http://127.0.0.1:8083",
            "RAPHAEL_REVIEWS_URL": "http://127.0.0.1:8087",
            "RAPHAEL_NOTIFICATIONS_URL": "http://127.0.0.1:8090",
            "RAPHAEL_AUTOMATION_URL": "http://127.0.0.1:8095",
            "RAPHAEL_CONNECTORS_URL": "http://127.0.0.1:8096",
            "RAPHAEL_AUDIT_URL": "http://127.0.0.1:8093",
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
    time.sleep(3)

    client = httpx.Client(timeout=10.0)
    checks = [
        ("GET", "http://127.0.0.1:8080/v1/config"),
        ("GET", "http://127.0.0.1:8080/v1/workspaces/default/modules"),
        ("GET", "http://127.0.0.1:8080/v1/repos"),  # compat
        ("GET", "http://127.0.0.1:8080/v1/reviews"),
        ("GET", "http://127.0.0.1:8080/v1/connectors"),
    ]
    failed = 0
    for method, url in checks:
        res = client.request(method, url)
        ok = res.status_code < 500
        print(f"{'OK' if ok else 'FAIL'} {method} {url} -> {res.status_code}")
        if not ok:
            failed += 1

    for p in procs:
        p.terminate()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

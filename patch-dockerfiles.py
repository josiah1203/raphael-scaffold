#!/usr/bin/env python3
"""Regenerate per-service Dockerfiles for parent-context builds."""

from pathlib import Path

PROJECTS = Path.home() / "Projects"

SERVICES = [
    ("raphael-core", 8080, "raphael_core.app:app"),
    ("raphael-identity", 8081, "raphael_identity.app:app"),
    ("raphael-orgs", 8082, "raphael_orgs.app:app"),
    ("raphael-workspaces", 8083, "raphael_workspaces.app:app"),
    ("raphael-artifacts", 8084, "raphael_artifacts.app:app"),
    ("raphael-slice", 8085, "raphael_slice.app:app"),
    ("raphael-licensing", 8086, "raphael_licensing.app:app"),
    ("raphael-reviews", 8087, "raphael_reviews.app:app"),
    ("raphael-comments", 8088, "raphael_comments.app:app"),
    ("raphael-messaging", 8089, "raphael_messaging.app:app"),
    ("raphael-notifications", 8090, "raphael_notifications.app:app"),
    ("raphael-links", 8091, "raphael_links.app:app"),
    ("raphael-search", 8092, "raphael_search.app:app"),
    ("raphael-audit", 8093, "raphael_audit.app:app"),
    ("raphael-workflows", 8094, "raphael_workflows.app:app"),
    ("raphael-automation", 8095, "raphael_automation.app:app"),
    ("raphael-connectors", 8096, "raphael_connectors.app:app"),
    ("raphael-registry", 8097, "raphael_registry.app:app"),
    ("raphael-sync", 8098, "raphael_sync.app:app"),
    ("raphael-ai", 8099, "raphael_ai.app:app"),
    ("raphael-graph", 8100, "raphael_graph.app:app"),
    ("raphael-rwu", 8101, "raphael_rwu.app:app"),
    ("raphael-environments", 8102, "raphael_environments.app:app"),
    ("raphael-ops", 8103, "raphael_ops.app:app"),
    ("raphael-admin", 8104, "raphael_admin.app:app"),
    ("raphael-analytics", 8105, "raphael_analytics.app:app"),
]

TEMPLATE = """# Build from ~/Projects:
#   docker build -f {name}/Dockerfile .
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY raphael-contracts /deps/raphael-contracts
RUN uv pip install --system /deps/raphael-contracts
COPY {name}/pyproject.toml {name}/README.md ./
COPY {name}/src ./src
RUN python3 -c "import re; from pathlib import Path; p=Path('pyproject.toml'); p.write_text(re.sub(r'\\n\\[tool\\.uv\\.sources\\][^\\[]*','\\n',p.read_text(),flags=re.S))"
RUN uv pip install --system -e .
ENV RAPHAEL_SERVICE_PORT={port}
EXPOSE {port}
CMD ["uvicorn", "{module}", "--host", "0.0.0.0", "--port", "{port}"]
"""


def main() -> None:
    for name, port, module in SERVICES:
        path = PROJECTS / name / "Dockerfile"
        if path.parent.exists():
            path.write_text(TEMPLATE.format(name=name, port=port, module=module))
            print(f"updated {path}")


if __name__ == "__main__":
    main()

# Route Parity Checklist

Gateway routes in `raphael-core` vs domain services. Updated after Platform Depth Phases 0–6.

| Route Prefix | Owning Repo | Status |
|---|---|---|
| `/v1/adapters` | `raphael-connectors` (compat rewrite) | OK |
| `/v1/ai/bundles/export` | `raphael-ai` | TODO (future) |
| `/v1/ai/jobs` | `raphael-ai` | OK |
| `/v1/analytics` | `raphael-analytics` | OK |
| `/v1/audit` | `raphael-audit` | OK |
| `/v1/audit/verify` | `raphael-audit` | OK |
| `/v1/automations` | `raphael-automation` | OK |
| `/v1/comments` | `raphael-comments` | OK |
| `/v1/config` | `raphael-core` | OK |
| `/v1/environments` | `raphael-environments` | OK |
| `/v1/events/` | `raphael-audit` (gateway rewrite) | OK |
| `/v1/graph/` | `raphael-graph` | OK |
| `/v1/health` | `raphael-core` | OK |
| `/v1/iam/` | `raphael-admin` (gateway rewrite) | OK |
| `/v1/identity` | `raphael-identity` | OK |
| `/v1/ingest/` | `raphael-artifacts` (gateway rewrite) | OK |
| `/v1/intelligence` | `raphael-ai` | OK |
| `/v1/links` | `raphael-links` | OK |
| `/v1/messaging` | `raphael-messaging` | OK |
| `/v1/notifications` | `raphael-notifications` | OK |
| `/v1/objects/` | `raphael-artifacts` (gateway rewrite) | OK |
| `/v1/ops` | `raphael-ops` | OK |
| `/v1/ops/backup` | `raphael-ops` | OK |
| `/v1/ops/replay` | `raphael-ops` | OK |
| `/v1/ops/verify-integrity` | `raphael-ops` | OK |
| `/v1/orgs` | `raphael-orgs` | OK |
| `/v1/projects` | `raphael-workspaces` | OK |
| `/v1/registry` | `raphael-registry` | OK |
| `/v1/repos` | `raphael-workspaces` (compat rewrite) | OK |
| `/v1/reviews` | `raphael-reviews` | OK |
| `/v1/rwu` | `raphael-rwu` | OK |
| `/v1/sessions/` | `raphael-sync` (gateway rewrite) | OK |
| `/v1/sync` | `raphael-sync` | OK |
| `/v1/suggestions` | `raphael-ai` (compat rewrite) | OK |
| `/v1/timeline` | `raphael-audit` (compat rewrite) | OK |
| `/v1/webhooks/` | `raphael-connectors` | OK |
| `/v1/workspaces` | `raphael-workspaces` | OK |
| `/metrics` | `raphael-core` (Prometheus) | OK |

## Deprecated / folded routes

| Legacy | Replacement |
|--------|-------------|
| `/v1/search` | `/v1/intelligence/ask` |
| `/v1/workflows` | `/v1/automations` |
| `/api/v1/auth` | `/v1/identity` |

## Verification

```bash
python3 raphael-scaffold/smoke-test.py   # 40+ gateway assertions
uv run pytest -q                       # per-repo unit tests
```

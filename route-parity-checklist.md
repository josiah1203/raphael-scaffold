# Route Parity Checklist (generated from calliope server.py)

Source: `/Users/josiah/calliope/packages/calliope-platform/src/calliope_platform/server.py`

| Route Prefix | Owning Repo | Status |
|---|---|---|
| `/v1/adapters` | `raphael-connectors (compat)` | OK |
| `/v1/adapters/` | `raphael-connectors (compat)` | OK |
| `/v1/ai/bundles/export` | `raphael-ai` | TODO |
| `/v1/ai/jobs` | `raphael-ai` | OK |
| `/v1/ai/jobs/` | `raphael-ai` | OK |
| `/v1/audit` | `raphael-audit` | OK |
| `/v1/audit/verify` | `raphael-audit` | TODO |
| `/v1/automations` | `raphael-automation` | OK |
| `/v1/automations/` | `raphael-automation` | OK |
| `/v1/automations/runs` | `raphael-automation` | OK |
| `/v1/config` | `raphael-core` | OK |
| `/v1/events/` | `raphael-audit (via gateway rewrite)` | OK |
| `/v1/graph/edges` | `raphael-graph` | OK |
| `/v1/graph/impact/` | `raphael-graph` | OK |
| `/v1/graph/nodes/` | `raphael-graph` | OK |
| `/v1/health` | `raphael-core` | OK |
| `/v1/iam/gdpr-delete` | `raphael-admin (via gateway rewrite)` | OK |
| `/v1/iam/holds` | `raphael-admin (via gateway rewrite)` | TODO |
| `/v1/iam/subjects/` | `raphael-admin (via gateway rewrite)` | OK |
| `/v1/ingest/altium` | `raphael-artifacts (connector split TODO)` | TODO |
| `/v1/ingest/events` | `raphael-artifacts` | TODO |
| `/v1/ingest/kicad` | `raphael-connectors (split TODO)` | TODO |
| `/v1/ingest/simulation` | `raphael-artifacts` | TODO |
| `/v1/ingest/snapshot` | `raphael-artifacts (via gateway rewrite)` | OK |
| `/v1/ingest/solidworks` | `raphael-artifacts` | TODO |
| `/v1/objects/` | `raphael-artifacts (via gateway rewrite)` | OK |
| `/v1/openapi.json` | `raphael-core` | OK |
| `/v1/ops/backup` | `raphael-ops` | TODO |
| `/v1/ops/replay` | `raphael-ops` | OK |
| `/v1/ops/verify-integrity` | `raphael-ops` | TODO |
| `/v1/projects` | `raphael-workspaces` | OK |
| `/v1/projects/` | `raphael-workspaces` | OK |
| `/v1/repos` | `raphael-workspaces (compat via raphael-core)` | OK |
| `/v1/repos/` | `raphael-workspaces (compat via raphael-core)` | OK |
| `/v1/reviews` | `raphael-reviews` | OK |
| `/v1/reviews/` | `raphael-reviews` | OK |
| `/v1/sessions/` | `raphael-sync (via gateway rewrite)` | OK |
| `/v1/suggestions` | `raphael-ai (compat alias TODO)` | TODO |
| `/v1/suggestions/feedback` | `raphael-ai` | TODO |
| `/v1/timeline` | `raphael-audit (compat via raphael-core)` | OK |
| `/v1/webhooks/` | `raphael-connectors` | OK |
| `/v1/webhooks/github` | `raphael-connectors` | OK |

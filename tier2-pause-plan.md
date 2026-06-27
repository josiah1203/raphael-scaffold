# Tier-2 Domain Services — Complete

Phase 4 removed the gateway **501 pause**. Tier-2 services are live with domain models, Kafka events, SDK methods, and UI detail routes.

| Service | Repo | Depth |
|---------|------|-------|
| **comments** | `raphael-comments` | Threading, anchors, target ACLs, `raphael.comments.created` |
| **messaging** | `raphael-messaging` | Review/module binding, Twilio optional, review event consumer |
| **links** | `raphael-links` | Typed source/target refs, graph edge on create |
| **registry** | `raphael-registry` | Semver manifests, module pins |
| **environments** | `raphael-environments` | Named configs, promotion stages, automation triggers |

## Folded elsewhere

| Capability | Owner |
|------------|-------|
| Search / ask | `raphael-ai` intelligence |
| Workflows | `raphael-automation` |
| Analytics overview | `raphael-analytics` |

## Deprecated repos

See `ARCHIVED.md` in each:

- `raphael-slice` → `raphael-workspaces`
- `raphael-licensing` → `raphael-admin` / `raphael-orgs`
- `raphael-search` → audit/graph/intelligence
- `raphael-workflows` → `raphael-automation`

## Tests

Each tier-2 repo has domain tests (`tests/test_*.py`). The integration smoke test in `raphael-scaffold/smoke-test.py` covers gateway routes for all five services.

**This document supersedes the original tier-2 pause plan.** No further 501 stubs are planned.

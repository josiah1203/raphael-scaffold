# Raphael Platform — 4-Week Production Roadmap

**Created:** June 28, 2026  
**Horizon:** Weeks 1–4 (July 2026)  
**Baseline:** 85/85 smoke checks · 330 Python tests · 29 UI tests · 23 active services

---

## Goal

Move Raphael from **integrated platform** to **production-expandable**: real enterprise auth, reliable events, live AI runtime, and removal of dev shortcuts (SQLite defaults, UI mock fallbacks, stub email).

---

## Guiding principles

1. **Production blockers first** — SSO, email, and Postgres-as-default before polish.
2. **One vertical slice per week** — ship end-to-end (backend + gateway + SDK + UI + smoke) per theme.
3. **No new services** — deepen existing repos; retire deprecated ones.
4. **Smoke test is the contract** — every week adds checks; never regress below 85.

---

## Week 1 — Identity & enterprise auth

**Theme:** Real auth for production tenants; remove hand-rolled crypto shortcuts.

| Priority | Service | Work | Done when |
|----------|---------|------|-----------|
| P0 | `raphael-identity` | Integrate Auth0 as IdP for enterprise SSO (SAML/OIDC); keep local email/OAuth for dev | Enterprise org can enforce SSO; password login disabled when `enforce_sso=true` |
| P0 | `raphael-identity` | Replace hand-rolled JWT with `PyJWT` (or `python-jose`); same claims (`sub`, `org_id`, `iss`, `exp`) | Identity + gateway tests pass; no custom HMAC encode/decode |
| P1 | `raphael-identity` | Password reset email via Postmark (reuse notifications transport) | Forgot-password flow sends real email in staging |
| P1 | `raphael-core` | Fix org-join: propagate `X-Raphael-User-Id` from JWT consistently | Smoke adds org-join with fresh user assertion |
| P1 | `raphael-ui` | Wire Settings SSO panel to identity/admin APIs (not local state only) | SSO save/load round-trips through gateway |
| P2 | `raphael-orgs` | Persist SSO settings (`sso_url`, `sso_entity`, `enforce_sso`) in Postgres store | Org settings API returns saved SSO config |

**Deliverables**
- [ ] Auth0 tenant configured (staging + prod env vars documented in `raphael-infra/services.env.example`)
- [ ] 5+ new smoke checks: SSO config CRUD, enforce flag, Auth0 callback (or mock IdP in CI)
- [ ] `Guidelines.md` backend handoffs: password reset + org join marked done

**Agents:** `identity-agent` (identity + core auth), `ui-agent` (settings SSO wiring)

---

## Week 2 — Persistence & event spine

**Theme:** Postgres as default in Docker/dev; Kafka events reliable in integration tests.

| Priority | Service | Work | Done when |
|----------|---------|------|-----------|
| P0 | `raphael-contracts` | Document + enforce Postgres-only path for tier-1 in Docker (SQLite = unit-test fallback only) | `docker compose up` uses Postgres for all tier-1 stores |
| P0 | `raphael-infra` | Enable Kafka in smoke-test Docker profile (remove `RAPHAEL_KAFKA_DISABLED=1` in CI integration job) | Integration workflow runs smoke with Redpanda |
| P1 | `raphael-audit` | Verify silver projector consumes published events end-to-end | Event publish → audit timeline shows derived silver row |
| P1 | `raphael-automation` | Wire automation triggers to Kafka consumer (commit landed, review created) | Smoke: create automation + trigger via event |
| P1 | `raphael-notifications` | Implement `POST /v1/notifications/mark-all-read` | UI inbox mark-all-read works against live API |
| P2 | `raphael-messaging` | Review-created event → conversation bootstrap (already partial) | Smoke: review event creates messaging thread |

**Deliverables**
- [ ] `platform-ci.yml` integration job runs smoke with Postgres + Kafka
- [ ] Smoke target: **90+ checks** (event-driven automation + mark-all-read)
- [ ] Migration runbook in `raphael-contracts` README

**Agents:** `persistence-agent`, `events-agent`

---

## Week 3 — Intelligence live & UI mock removal

**Theme:** Ollama/Gemma live in Docker by default; UI reads real APIs.

| Priority | Service | Work | Done when |
|----------|---------|------|-----------|
| P0 | `raphael-ai` | Harden Ollama startup in Docker (pre-pull, health gate, `model_tier=live` in compose) | Intelligence status returns `live` when Ollama healthy |
| P1 | `raphael-ai` | Implement `/v1/ai/bundles/export` (route parity TODO) | Smoke check for bundle export |
| P1 | `raphael-ui` | Remove mock fallbacks on Activity, Explorer, Reviews inbox when backend connected | Pages show empty states, not `localDevData`, when API returns `[]` |
| P1 | `raphael-ui` | Adapters page: live connector status only (drop `MOCK_ADAPTERS_CONNECTED` when API ok) | Connectors smoke + UI aligned |
| P2 | `raphael-devplatform` | SDK methods for notifications mark-all-read, SSO settings, bundle export | SDK types + client updated |
| P2 | `raphael-admin` | `POST /v1/admin/domain/verify` stub → real DNS TXT check or documented defer | Settings domain verify button works or shows clear "coming soon" |

**Deliverables**
- [ ] Docker compose intelligence profile: Gemma pre-pulled, smoke uses `RAPHAEL_MODEL_BACKEND=ollama` in optional CI matrix job
- [ ] UI: `isLocalMode` only when platform unreachable (not when API returns empty)
- [ ] Smoke: **95+ checks**

**Agents:** `intelligence-agent`, `ui-agent`

---

## Week 4 — Production ops & deprecated cleanup

**Theme:** External integrations validated; retire dead repos; ops runbooks.

| Priority | Service | Work | Done when |
|----------|---------|------|-----------|
| P0 | `raphael-scaffold` | Remove deprecated repos from polyrepo manifest CI matrix (keep ARCHIVED.md pointers only) | CI no longer tests `raphael-slice`, `-licensing`, `-search`, `-workflows` |
| P1 | `raphael-admin` | Stripe webhook end-to-end test (test mode keys in CI secret) | Billing plan upgrade reflected in org context |
| P1 | `raphael-ops` | Backup restore drill documented + smoke for restore metadata | Ops page shows last backup; restore API returns job id |
| P1 | `raphael-automation` | `POST /v1/automations/{id}/trigger` manual trigger | UI or SDK can fire automation on demand |
| P2 | `raphael-infra` | Staging deploy manifest (single-host or k8s skeleton) + health check URLs | `DEPLOY.md` with env var checklist |
| P2 | `raphael-notifications` | Postmark integration test in CI (sandbox token) | Password reset + review notification emails in staging |
| P2 | All | Git history migration optional pass (`HISTORY-MIGRATION.md`) or confirm skip | Decision documented |

**Deliverables**
- [ ] Deprecated repos archived on GitHub; local clones optional
- [ ] `DEPLOY.md` in `raphael-infra`
- [ ] Smoke: **100 checks** (stretch goal)
- [ ] Production readiness checklist signed off

**Agents:** `platform-hardening-agent`, `ops-agent`

---

## Service ownership matrix

| Service | W1 | W2 | W3 | W4 |
|---------|----|----|----|----|
| raphael-identity | ●●● | ○ | ○ | ○ |
| raphael-core | ●● | ○ | ○ | ○ |
| raphael-orgs | ● | ○ | ○ | ○ |
| raphael-contracts | ○ | ●● | ○ | ○ |
| raphael-infra | ○ | ●● | ● | ●● |
| raphael-audit | ○ | ●● | ○ | ○ |
| raphael-automation | ○ | ●● | ○ | ● |
| raphael-notifications | ● | ● | ○ | ● |
| raphael-ai | ○ | ○ | ●●● | ○ |
| raphael-ui | ●● | ● | ●●● | ○ |
| raphael-devplatform | ○ | ○ | ● | ○ |
| raphael-admin | ○ | ○ | ● | ●● |
| raphael-ops | ○ | ○ | ○ | ●● |
| raphael-scaffold | ● | ●● | ● | ●●● |

● = active work that week

---

## Parallel agent workstreams

When executing, launch these in parallel per week (max 2–3 concurrent):

```
Week 1:  identity-agent + ui-agent
Week 2:  persistence-agent + events-agent
Week 3:  intelligence-agent + ui-agent
Week 4:  platform-hardening-agent + ops-agent
```

Each agent should:
1. Read this roadmap section only for its week
2. Run `uv run pytest -q` in touched repos
3. Extend `smoke-test.py` with at least 2 new assertions
4. Update `route-parity-checklist.md` if routes change

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Auth0 setup delays | Ship PyJWT + email reset first; Auth0 can slip to W2 without blocking |
| Ollama pull slow in CI | Keep stub backend in default CI; Ollama in optional nightly job |
| Kafka flakiness in smoke | Retry wrapper + `depends_on: redpanda healthy` already in compose |
| UI mock removal breaks demos | Keep `VITE_LOCAL_MOCK=true` escape hatch; document in README |
| Stripe/Postmark secrets missing | Sandbox keys in GitHub secrets; skip integration job if unset |

---

## Success metrics (end of Week 4)

| Metric | Current | Target |
|--------|---------|--------|
| Smoke assertions | 85 | 100 |
| Python tests | 330 | 380+ |
| Stub gate violations | 0 | 0 |
| Services on Postgres in Docker | Partial | All tier-1 + tier-2 |
| UI pages with live-only data | ~60% | ~90% |
| Enterprise SSO | Env vars only | Auth0 E2E |
| Deprecated repos in CI | 4 | 0 |

---

## Out of scope (defer past Week 4)

- Multi-region deployment
- Full SAML implementation without Auth0 (build vs buy — buy wins)
- Python SDK (TypeScript SDK only for now)
- Calliope monolith retirement (`RAPHAEL_LEGACY_CALLIOPE_URL` fallback)
- Mobile / offline-first sync clients

---

## Quick start (execute Week 1)

```bash
cd ~/Projects/raphael-scaffold

# Verify baseline
python3 smoke-test.py          # expect 85/85

# Week 1 first PR scope
# - raphael-identity: PyJWT migration
# - raphael-identity: Postmark password reset
# - raphael-core: org-join header fix
# - raphael-ui: SSO settings API wiring
```

---

*Supersedes ad-hoc depth plans once Week 1 begins. Update checkboxes weekly.*

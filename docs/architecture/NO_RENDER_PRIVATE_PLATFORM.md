# Private Sputnik + Gagarin platform without Render

Status: architecture decision / migration plan (not deployed)
Date: 2026-11-02
Decision: remove Render as a required component. Do not provision paid services.

## Selected target

Use a small JavaScript/TypeScript Cloudflare Worker (Free) as the private application edge, with Worker Static Assets and a D1 binding for the PWA and authenticated APIs. Keep the existing Python market monitors on GitHub Actions initially; let them access D1 through the scoped D1 REST API using server-side GitHub Actions secrets. Do not move the current psycopg-based FastAPI application unchanged to Python Workers: Python package support now uses PyWrangler/PyEmscripten, but compatibility of the existing native database driver and full dependency set must be proven first. D1's Worker Binding API is preferred for requests handled by the Worker; the REST API is for the existing Python runners. Static hosting without a Worker-enforced private login is not acceptable.

Why this is the best first candidate:
- Cloudflare documents first-class Python Workers and support for FastAPI, plus bindings to D1, KV, and other platform services.
- Workers Free currently documents 100,000 requests/day, 10 ms CPU per HTTP request, and five Cron Triggers per account. D1 Free currently documents 5 million rows read/day, 100,000 rows written/day, and 5 GB total storage. Static Asset requests are free and unlimited.
- Static asset requests can be served without a Workers request charge when they do not invoke the Worker. Authenticated routes must invoke the Worker. Keep heavy market/news polling on the existing GitHub Actions runners; do not put it on a Free Cron Trigger with a 10 ms CPU allowance.
- No paid plan is required for the proposed initial footprint, but the free limits are hard constraints, not a service guarantee.

Official references:
- https://developers.cloudflare.com/workers/languages/python/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/
- https://developers.cloudflare.com/workers/runtime-apis/bindings/
- https://developers.cloudflare.com/workers/platform/pricing/\n- https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/\n- https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/\n- https://developers.cloudflare.com/workers/languages/python/packages/

## Required architecture

1. One Cloudflare Worker serves the PWA assets and all private routes. Configure Worker-first routing for every application path; do not expose a Pages/static origin that bypasses authentication.
2. Middleware denies access by default. /login is the only unauthenticated application page; all dashboard HTML, /api/*, bridge routes, and private data require a valid server-verified session.
3. Store password hash and session signing secret only as Worker secrets (APP_PASSWORD_HASH, APP_SESSION_SECRET). Never put secrets in Vite/browser bundles, HTML, localStorage, sessionStorage, service-worker caches, GitHub Pages, or repository files.
4. Keep CLOUD_API_KEY server-side as a Worker secret. Use a separate narrowly scoped bridge credential for Sputnik-to-Gagarin. Compare credentials in constant time where supported; rotate credentials without logging them.
5. Use HttpOnly, Secure, SameSite cookies; short-lived signed sessions; CSRF protection on state-changing requests; rate limiting on login; logout revokes/invalidates the session. Fail closed if required secrets are absent.
6. Service worker caches only versioned static App Shell assets. Never cache /api/*, HTML containing user data, login responses, session endpoints, or bridge payloads. Logout clears client-held transient state and returns to the login screen.
7. Use D1 for platform persistence only after a schema and data migration. Do not assume PostgreSQL/psycopg is compatible with D1: current psycopg access must be replaced behind a repository interface and tested against D1's SQLite semantics. Preserve export/backup capability.
8. Prefer Telegram webhooks over a continuously polling listener. Verify webhook secret/token and require Telegram ok=true plus a real message_id for every claimed successful notification.
9. Keep the existing Python market/news monitor schedules on GitHub Actions during the migration. Use Cloudflare Cron Triggers only for short edge maintenance tasks; Free allows five triggers per account and the 10 ms CPU budget makes the full market/news scan unsuitable without measured proof. Do not claim a five-minute scan is viable until provider rate limits, freshness, runner availability, and D1 quotas are measured.
10. Keep PAPER TRADING only. No exchange/broker order execution is part of this migration.

## Migration sequence (one independently testable step per change)

- [ ] Inventory existing FastAPI routes, static frontend, auth middleware, Postgres schema, background jobs, Telegram webhook/polling, and all Render-only environment assumptions. Record dependencies and route exposure.
- [ ] Add a storage repository interface and tests while retaining the current PostgreSQL adapter. No production behavior change.
- [ ] Implement and test a D1 REST adapter for the existing Python monitor and explicit SQLite-compatible migrations; verify parameter binding, state upsert, journal ordering, JSON validation, timeout/error handling, and no secret leakage.
- [ ] Build the authenticated app entrypoint as a JavaScript/TypeScript Worker with a D1 binding. Add tests for unauthenticated HTML/API denial, login throttle, cookie flags, CSRF, logout, missing-secret fail-closed behavior, and secret non-disclosure. Keep the Python market monitors on GitHub Actions.
- [ ] Attach static PWA assets to the same Worker; test every route for authentication bypass and verify service-worker cache exclusions.
- [ ] Implement authenticated Sputnik-to-Gagarin bridge delivery with idempotent event IDs, replay protection, bounded payload validation, and end-to-end tests.
- [ ] Replace polling with Telegram webhook delivery where feasible; prove successful message IDs in logs without logging tokens.
- [ ] Run shadow-mode monitors and compare outputs with the existing PAPER pipeline. Measure request/CPU quotas and provider freshness before enabling schedules.
- [ ] Deploy to a Cloudflare account only after the owner explicitly creates/configures the account and secrets. Verify login/logout, PWA install on a physical iPhone, bridge delivery, persistence, Telegram, and deployment health before calling it ready.
- [ ] Only after all acceptance tests pass, remove Render-specific runtime references from deployment documentation and operational procedures.

## Acceptance gates

The platform is NOT ready until all are demonstrated:
- Private HTML and API cannot be reached without authentication, including direct asset/API URL attempts.
- Login throttle, secure session cookie, CSRF, logout, and missing-secret fail-closed tests pass.
- No secret appears in repository content, built assets, browser storage, service-worker cache, or logs.
- PWA manifest, Apple icon, install prompt, offline App Shell, and logout behavior are verified on a physical iPhone.
- D1 persists events and paper journal data across deployments from both the Worker binding and Python Actions REST adapter; backup/export and restore are tested.
- Sputnik event reaches Gagarin exactly once (idempotent event ID) and is visible in the platform.
- Telegram delivery is confirmed by Telegram API ok=true and a real message_id.
- Monitor scheduling, data freshness, provider rate limits, and Free-plan CPU/request quotas are measured.
- No paid plan, paid add-on, public database allowlist, public dashboard, or real order execution is enabled.

## Free-tier risk register

- Workers Free is quota-limited and can reject traffic after the daily request limit; design private routes to fail closed.
- Python Workers run on Pyodide. Native packages and existing PostgreSQL drivers may need replacement; compatibility must be proven, not assumed.
- D1 Free has daily row read/write quotas and a 5 GB account storage cap; exceeding quotas blocks queries until reset. Validate expected journal growth and usage before enabling persistence. Python Workers support pure/PyEmscripten packages via PyWrangler, but native psycopg compatibility is not assumed.
- A free plan can change or impose operational constraints. Exportability and a documented rollback path are mandatory.
- Cloudflare account ownership, domain choice (if a custom domain is wanted), and secret configuration require the owner. Do not request secret values in chat.

## GitHub Actions D1 configuration (not yet enabled)\n\nDo not add the secrets or set `GAGARIN_STORAGE_BACKEND` yet: this PR adds the tested adapter, but the current monitor workflows do not pass these variables to the process. A follow-up integration must first migrate the separate paper-trade/feedback journals and stop the existing workflow from pushing CSV journal files into this public GitHub repository. Only after that privacy-safe wiring is reviewed should the owner add repository Actions secrets `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_D1_DATABASE_ID`, and `CLOUDFLARE_API_TOKEN` (never commit or send values in chat), with only D1 Read and D1 Write permissions, and set the non-secret variable `GAGARIN_STORAGE_BACKEND=d1`. Apply the schema once with `npx wrangler d1 execute <DATABASE_NAME> --remote --file=migrations/d1/0001_initial.sql`; runtime startup only verifies the tables/index and never issues DDL on every monitor run. The repository is public; its current workflow has a step that pushes `gagarin_feedback.csv` and `paper_trade_log.csv` to `main`, so those files must not contain private user data.\n\n## Explicit non-goals

- No Render services, deployments, databases, or budget changes.
- No GitHub Pages hosting for private dashboard/data.
- No paid Cloudflare Workers plan or paid database.
- No real trading orders.
- No claim of successful migration or deployment based on repository changes alone.

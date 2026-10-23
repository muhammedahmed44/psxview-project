# PSXviewAI Implementation Roadmap

This roadmap is organized into the six phases described in the planning brief.
Each phase lists dependencies and high-level acceptance criteria.

## Phase 1 – Foundation: repo, tooling, auth, schema (current)

**Goal:** Bootstrap backend/frontend, base auth, core DB schema, and minimal
tooling.

### Work items

- [x] Initialize FastAPI backend with modular-monolith layout.
- [x] Define `User` and `RefreshToken` models with JWT-based auth service.
- [x] Implement `/api/health`, `/api/auth/register`, `/api/auth/login`,
  `/api/auth/me`.
- [x] Design core relational schema via SQLAlchemy models and Alembic
  migration.
- [x] Initialize React + Vite + Tailwind frontend with routing and layouts.
- [ ] Add basic backend unit tests (pytest) and CI job.
- [ ] Add frontend unit test harness and Playwright E2E skeleton.

### Dependencies

- None (initial bootstrap).

### Acceptance criteria

- Repo can be checked out and run locally (`npm run dev` + Alembic migrations).
- A new user can sign up and log in from the UI, receiving a valid JWT.
- Authenticated `/api/auth/me` returns the expected user payload.
- Core tables exist: users, companies, instruments, watchlists, holdings,
  market prices, documents, news, evidence items, valuations, conversations,
  answer claims.

## Phase 2 – Portfolio & market data

**Goal:** Implement watchlist/holdings CRUD and integrate a validated market
snapshot source.

### Work items

- Implement portfolio/watchlist API routes and services; enforce per-user
  isolation.
- Add frontend forms and tables for managing watchlists and holdings.
- Implement `MarketDataProvider` adapter(s) and background job or admin trigger
  to fetch and store timestamped market prices.
- Expose latest market price snapshots via API with explicit source,
  `as_of`, `retrieved_at`, and `is_delayed` flags.
- Display market prices in holdings and company views without portfolio-level
  aggregate performance.

### Dependencies

- Phase 1 auth and core schema.

### Acceptance criteria

- Users can add/edit/remove watchlist entries and holdings only for their own
  accounts.
- API returns latest available price snapshot per instrument and clearly marks
  stale data.
- UI displays holdings with quantities, cost, and latest price plus timestamp
  and source; no aggregate P&L or performance charts.

## Phase 3 – News and documents ingestion

**Goal:** Ingest authentic PSX news/filings, normalize them into documents,
news items, and evidence records.

### Work items

- Implement ingestion adapters for at least one official filings source and one
  reputable news source.
- Design ingestion jobs with explicit logging and idempotency.
- Populate `documents`, `news_articles`, `news_company_links`, and
  `evidence_items`.
- Expose a news feed API suitable for the dashboard and company pages.
- Implement basic UI components for news cards and detail pages with source
  links, timestamps, and affected companies.

### Dependencies

- Phases 1–2.

### Acceptance criteria

- Ingestion can be run in staging with real dated sources and produces
  normalized records with provenance.
- Dashboard and company pages show news cards with publisher, headline,
  publication date, and affected tickers.
- News detail view shows original source link, summary, and evidence items.

## Phase 4 – Valuation engine & company pages

**Goal:** Implement deterministic valuation methods and expose them via company
research views.

### Work items

- Extend `valuation/engine.py` to support at least one appropriate valuation
  method (e.g., simple DCF or earnings-based multiple) with bear/base/bull
  scenarios.
- Store valuation inputs, outputs, and provenance in `valuation_runs` and
  `valuation_scenarios`.
- Implement APIs to fetch company overviews, financial metrics, and valuation
  scenarios.
- Build company pages showing key metrics, historical performance, and
  valuation scenarios without implying guaranteed returns.

### Dependencies

- Phases 1–3.

### Acceptance criteria

- Deterministic unit-tested valuation functions with clear inputs and units.
- Company pages display fair-value ranges and assumptions; numbers match the
  backend outputs.

## Phase 5 – AI assistant & research flows

**Goal:** Deliver an evidence-backed conversational assistant and research
workflows that link claims to stored evidence.

### Work items

- Implement a concrete `AIProvider` adapter to an approved hosted LLM.
- Design RAG-style retrieval over `evidence_items` and structured metrics.
- Implement conversation APIs and UI, including question history and answer
  display.
- Model `AnswerClaim` generation with claim types (fact/calculation/
  interpretation) and verification status.
- Add an evidence panel showing sources, timestamps, and uncertainty.

### Dependencies

- Phases 1–4.

### Acceptance criteria

- Users can ask company/portfolio questions and receive answers annotated with
  claims and citations.
- Unsupported or stale evidence leads to safe "insufficient data" style
  responses instead of fabrication.

## Phase 6 – Hardening, security, and QA

**Goal:** Strengthen security, reliability, and test coverage ahead of any
external users.

### Work items

- Harden authentication (refresh rotation, email verification, password reset,
  optional 2FA) and storage of secrets.
- Implement role-based access for admin/research-curator operations.
- Expand unit/integration tests across backend and frontend; add Playwright E2E
  tests for key flows.
- Review logging, error handling, and data retention policies.
- Conduct a security review focusing on cross-user data leaks, injection risks,
  and protections around untrusted documents/news.

### Dependencies

- Phases 1–5.

### Acceptance criteria

- CI enforces tests and basic static checks.
- E2E tests cover auth, watchlist/holdings CRUD, company page, and AI answers
  with citations.
- Security review items are documented with mitigations or explicit deferrals.

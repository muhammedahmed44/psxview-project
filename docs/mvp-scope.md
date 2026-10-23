# PSXviewAI MVP Scope (Phase 1 focus)

This document narrows `SPEC.md` into a concrete MVP scope for the current
foundation phase. It does **not** change product requirements; it records what
is implemented now versus later.

## 1. Included in Phase 1

### 1.1 Authentication and accounts

- Email + username + password registration.
- Login issuing JWT access + refresh tokens.
- Basic `/api/auth/me` endpoint for profile retrieval.
- Frontend login and sign-up pages using a light theme consistent with
  PSXviewAI branding.

### 1.2 Core schema

Relational schema (via SQLAlchemy + Alembic) for:

- Users and refresh tokens.
- Companies and instruments.
- User watchlist entries and holdings.
- Market price snapshots.
- Documents and news articles.
- Evidence items.
- Valuation runs and scenarios.
- Conversations, answers, and answer claims.

### 1.3 Application shell

- React SPA, React Router + nested layouts.
- Top-level routes and placeholder content for:
  - `/` – dashboard shell (watchlist + news cards, no live data yet).
  - `/companies` – future company pages.
  - `/news` – future news feed.
  - `/assistant` – future conversational assistant.
  - `/login`, `/register` – authentication.

## 2. Explicitly out of scope for Phase 1

These are required for the full PSXviewAI product but will be implemented in
later roadmap phases:

- Real watchlist and holdings CRUD endpoints and UI.
- Displaying any aggregate portfolio value, P&L, sector allocation, or
  performance analytics (per NFRs these may be intentionally omitted even
  later).
- Live or delayed market data ingestion (including `psxdata` integration).
- News/document ingestion, parsing, and evidence extraction.
- Valuation methods beyond the stub in `valuation/engine.py`.
- AI assistant implementation and any LLM provider integration.
- Learning academy content and flows.
- Alerts, briefs, and thesis tracking.

## 3. Acceptance checkpoints for this phase

- The repository installs and runs via `npm install` (root + frontend) and
  `pip install -e .` (backend).
- Alembic migrations succeed against the configured database.
- FastAPI serves `/api/health` and `/api/auth/*` endpoints.
- A user can register and log in via the frontend UI with a working auth
  round-trip.
- JWT-protected `/api/auth/me` rejects unauthenticated calls and returns the
  current user when provided a valid token.

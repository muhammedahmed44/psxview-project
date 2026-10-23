# PSXviewAI Architecture (Phase 1 foundation)

This document describes the agreed architecture for PSXviewAI at the end of the
foundation phase. It aligns with the product scope in `SPEC.md` and the
engineering guidelines in `AGENTS.md` and `skill.md`.

## 1. High-level system

PSXviewAI is a **web application** with:

- A React + TypeScript + Vite + Tailwind frontend (SPA) using React Router.
- A FastAPI backend implemented as a **modular monolith**.
- A PostgreSQL database accessed via SQLAlchemy and managed through Alembic
  migrations (with SQLite allowed as a local dev fallback only).

### Module layout (backend)

```text
backend/app/
  main.py              # FastAPI app wiring
  config.py            # Pydantic-based settings
  db/
    session.py         # Engine, session factory, Base
    models/            # ORM models (users, companies, ...)
  api/
    routes/            # Versioned routers (auth, portfolio, research, ...)
    deps.py            # Shared FastAPI dependencies (auth, DB)
  services/            # Application services (auth, portfolio, research)
  repositories/        # ORM data-access abstractions
  ingestion/           # Source adapters (market data, news, documents)
  valuation/           # Deterministic valuation engine
  ai/                  # AI provider interface (LLM adapter)
  security/            # Password hashing, JWT helpers
```

Responsibilities:

- **API routers** expose HTTP routes, validate payloads via Pydantic, and
  delegate to services.
- **Services** coordinate business rules across repositories, ingestion
  adapters, and valuation/AI components. They are unit-testable and avoid
  direct HTTP or DB details.
- **Repositories** encapsulate read/write patterns to SQLAlchemy models.
- **Ingestion adapters** present a clean interface over untrusted external
  sources (`psxdata`, news APIs, file parsers) and are responsible for
  validation, timestamping, and logging.
- **Valuation engine** contains deterministic calculation functions; the AI
  may *explain* these numbers but never performs the arithmetic itself.
- **AI provider interface** wraps a hosted LLM behind a replaceable `AIProvider`
  contract.

### Frontend layout

```text
frontend/src/
  App.tsx                  # Router and top-level layout
  index.css                # Tailwind base styles
  components/
    layout/                # Auth and dashboard layouts
    common/                # Shared UI primitives (Card, buttons, etc.)
  pages/
    HomePage.tsx           # Dashboard (watchlist + news shell)
    CompaniesPage.tsx      # Company research shell
    NewsPage.tsx           # News feed shell
    AssistantPage.tsx      # AI assistant shell
    LoginPage.tsx          # Auth screens
    RegisterPage.tsx
```

The visual style uses a **light theme** with white backgrounds, dark green
primary accents, muted gray text, and subtle borders, matching the product
requirements.

## 2. Authentication model

- Users register with email, username, password, and optional display name.
- Passwords are hashed using `passlib[bcrypt]` and never stored in plaintext.
- On successful registration or login, the backend issues:
  - A short-lived **access token** (JWT, signed with `JWT_SECRET_KEY`).
  - A long-lived **refresh token**, also a JWT but stored only as a **hash** in
    the `refresh_tokens` table to support revocation and rotation.
- The frontend currently stores the access token in `localStorage` and sends it
  as a `Bearer` token. Later phases can move to httpOnly cookies or a more
  hardened session model.
- The `/api/auth/me` endpoint returns the current user's profile and is the
  canonical way for the frontend to confirm authentication status.

## 3. Core data model

Key entities (see `backend/app/db/models` and Alembic migration):

- **User** – private account; owns watchlist, holdings, conversations,
  valuations.
- **RefreshToken** – hashed refresh token per user for session renewal.
- **Company** – canonical PSX company record (ticker, name, sector).
- **Instrument** – tradeable instruments (e.g. equity shares) linked to
  companies; future-proofed for other instrument types.
- **WatchlistEntry** – link between user and instrument (no portfolio
  aggregates per constraints).
- **Holding** – user-owned position in an instrument with quantity and
  average cost; strictly per-user.
- **MarketPrice** – timestamped price snapshots, including explicit source,
  currency, and `is_delayed` flag.
- **Document** – source documents (filings, annual reports, etc.) with
  provenance, publication and retrieval times, and excerpts.
- **NewsArticle** + **NewsCompanyLink** – news items and their mapping to
  affected companies.
- **EvidenceItem** – normalized evidence chunks, used later to back claims.
- **ValuationRun** + **ValuationScenario** – valuation computations for a
  company with bear/base/bull scenarios and upside/downside.
- **Conversation**, **Answer**, **AnswerClaim** – stored AI conversations and
  claims, each linked to evidence or valuation runs.

SQLite is used as a dev fallback; PostgreSQL is the target database for
production deployments.

## 4. External data and adapters

The backend defines an abstract `MarketDataProvider` interface and an
`InMemoryMarketDataProvider` for tests. A concrete adapter around `psxdata` or
another source will:

- Implement `get_latest_price(symbol)`.
- Return a `MarketPriceSnapshot` with explicit `as_of`, `retrieved_at`,
  `source`, and `is_delayed`.
- Treat the provider as untrusted: validate types, ranges, and timestamps
  before persisting anything.

Similar adapter patterns will be used for:

- News ingestion (PSX announcements, reputable news).
- Document ingestion (filings, reports) and parsing.

## 5. AI and valuation separation

- `app/valuation/engine.py` defines typed `ValuationInputs` and
  `ValuationOutputs` and a `ValuationEngine` entry point. The current
  implementation is intentionally simple and deterministic; future work will
  introduce sector-specific methods while keeping them testable and
  side-effect-free.
- `app/ai/provider.py` defines an `AIProvider` interface. Concrete
  implementations (e.g. calling an LLM API) will live behind this contract so
  they can be swapped or mocked in tests.

## 6. Security and data isolation

- User-specific tables (`holdings`, `watchlist_entries`, `conversations`,
  `valuation_runs`) always carry a `user_id` and will be filtered at the
  service/route level using the authenticated user.
- External data (market quotes, news, documents) is considered untrusted.
  Ingestion layers will validate and sanitize content before storing, and
  evidence will be linked by ID, not raw textual prompts.

## 7. Open questions / to refine later

- Exact JWT refresh flow (dedicated refresh endpoint, rotation and revocation
  semantics).
- Whether to store access tokens in cookies instead of `localStorage`.
- pgvector extension usage for evidence retrieval and how it maps to the
  `EvidenceItem` model.
- Concrete `psxdata` adapter implementation and any licensing constraints.
- Final valuation formulas per sector and how they are exposed in the API.

# PSXviewAI (Phase 1 foundation)

This repository hosts the early foundation for **PSXviewAI**, an evidence-backed
financial research assistant for Pakistan Stock Exchange investors.

This phase focuses on a minimal but real FastAPI backend, a React + Vite +
Tailwind frontend shell, JWT-based authentication, and the core relational
schema for users, companies, instruments, watchlists, holdings, market prices,
news/documents, evidence items, valuations, and research conversations.

## Tech stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL (SQLite fallback for dev)
- Frontend: React, TypeScript, Vite, Tailwind CSS

## Getting started

1. **Install Node dependencies** (from repository root):

   ```bash
   npm install
   ```

2. **Install Python dependencies** for the backend on Windows PowerShell:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. **Configure environment**

   Copy `.env.example` to `.env` (not committed) and fill in at least
   `DATABASE_URL` (for a real PostgreSQL instance) and `JWT_SECRET_KEY`. In the
   preview environment, set them via the Secrets panel.

4. **Run database migrations** (uses SQLite fallback if `DATABASE_URL` is not set):

   ```bash
   cd backend
   alembic upgrade head
   ```

5. **Start dev servers** (from repository root):

   ```bash
   npm run dev
   ```

   - Backend: http://localhost:8000 (FastAPI)
   - Frontend: http://localhost:5173 (Vite, proxied `/api` → backend)

## Notes

- Authentication is JWT-based: the frontend stores the access token in
  `localStorage` for now; later phases can harden this.
- The schema is created via Alembic and modeled in `backend/app/db/models/*`.
- Many application features (portfolio flows, news ingestion, valuation engine,
  AI assistant, and complete testing) are intentionally left for later phases.


## Preview

The root `package.json` is the preview entry point and serves the existing React app from `frontend/src`. Run `npm install`, then `npm run dev`. The Vite proxy forwards `/api` requests to the FastAPI server on port 8000; the frontend also renders safely while that server is offline.

## Frontend regeneration

The first staged frontend pass refreshes the home market dashboard in `frontend/src/components/MarketSnapshot.tsx` and its visual refinements in `frontend/src/index.css`. It also adds a visual market-breadth progress indicator. Existing data hydration, ticker interactions, company cards, modal behavior, and API contracts remain unchanged. Continue to the next page only when requested.

## PSXviewAI backend integration

Start the API from `backend/` with `python -m uvicorn main:app --reload --port 8000`, then start the frontend from the repository root with `npm install` and `npm run dev`. Vite proxies relative `/api` requests to FastAPI. Check `http://localhost:8000/api/health` and `/api/market` to verify connectivity and data provenance. The backend has no required external database for this phase; local SQLite data resets according to its configuration, while market/news caches are in memory.

For dependency verification, run `cd backend; python smoke_test.py` and `python -m pytest`. A missing pipeline snapshot is reported as `news_source: mock`; no mock data is presented as live pipeline data.

## Learning Academy (Phase 9)

The **Learn** navigation opens five beginner modules covering PSX basics, fundamentals, technical analysis, risk, and valuation. Quizzes are graded deterministically in the browser with immediate explanations. Guests can learn temporarily; signed-in users save best progress and quiz scores in the local database, isolated by user. The academy tutor uses the configured existing AI integration and clearly labels interpretation. If no AI key is configured, the existing safe fallback is shown.

Academy progress uses the existing SQLite/dev database and resets if that database is cleared. To persist across machines, enable the workspace Database and configure the backend database URL.

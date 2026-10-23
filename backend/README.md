# PSXviewAI — FastAPI backend

Serves the prototype market data the React frontend consumes. Data + the
seeded PRNG are in `data.py`; endpoints are in `main.py`.

## Setup

```bash
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```bash
python -m uvicorn main:app --reload --port 8000
# or:  python main.py
```

API will be at http://localhost:8000. The Vite dev server proxies `/api/*`
here, so the frontend calls `/api/market` and it just works.

## Endpoints

- `GET /api/health` — `{ "status": "ok" }`
- `GET /api/companies` — company list (symbol, price, volume, 90-point series, eps)
- `GET /api/announcements` — announcement list
- `GET /api/sources` — per-announcement source records + AI confidence
- `GET /api/market` — all of the above in one call (used by the frontend on load)
- `POST /api/research/ask` — source-grounded assistant; works for guests and signed-in users
- `GET/POST /api/research/conversations` — authenticated conversation persistence with ownership checks

Guest answers are temporary by design. Authenticated research is stored in the existing SQLite database and resets if that local file is removed.

## Authentication

- `POST /api/auth/register` creates an account and returns an authenticator setup QR.
- `POST /api/auth/login` validates the password and starts the authenticator challenge.
- `POST /api/auth/verify-totp` accepts an authenticator or one-time recovery code.

Account 2FA uses Google Authenticator-compatible TOTP and does not require an
email provider. On first registration/login, scan the QR and save the recovery
codes shown after confirmation. Keep `JWT_SECRET` stable because it is also used
to protect stored authenticator secrets.

Interactive docs: http://localhost:8000/docs

## Verification

From `backend/`, run the dependency checks (the pytest check uses an in-memory byte buffer and does not need a database):

```powershell
python smoke_test.py
python -m pytest tests/test_dependency_smoke.py
python -m pytest
```

The smoke test imports FastAPI, NumPy, Pandas, psxdata, lxml/BeautifulSoup, and PyArrow, then round-trips a small Pandas frame through Parquet. A failure indicates the environment should be repaired before investigating API or market-data errors.

`/api/health` and `/api/market` expose `market_source` / `news_source` provenance. Market data is fetched through `psxdata` where available; individual fetch failures may use the explicitly logged last-resort fallback in `data.py`. News is marked `pipeline` only when a pipeline snapshot is loaded, otherwise it is marked `mock`.

The frontend uses the Vite proxy at `/api`, so run the backend on port 8000 and the root frontend with `npm run dev`.

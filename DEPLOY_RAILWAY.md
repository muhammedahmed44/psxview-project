# Deploy PSXviewAI on Railway

The production image serves the React build and FastAPI API from one domain.
This preserves the existing relative `/api` calls and HttpOnly login cookies.

## 1. Push the project to a private GitHub repository

The root `.gitignore` excludes `.env`, SQLite databases, virtual environments,
build output, and `node_modules`. Confirm no secrets are staged before pushing:

```powershell
git init
git add .
git status
git commit -m "Prepare Railway deployment"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

## 2. Create the Railway service

1. In Railway, create a project and choose **Deploy from GitHub repo**.
2. Select this repository. Railway detects the root `Dockerfile`.
3. Open **Settings > Networking** and generate a public domain.
4. Set the health-check path to `/api/health`.

## 3. Attach persistent storage

Attach one volume to the application service and mount it at `/data`. Then add:

```env
DATABASE_URL=sqlite:////data/psxviewai.db
```

Keep the service at one replica while it uses SQLite. For multiple replicas,
migrate to PostgreSQL instead of sharing a SQLite volume.

## 4. Add production variables

Add these under the service's **Variables** tab:

```env
DATABASE_URL=sqlite:////data/psxviewai.db
COOKIE_SECURE=1
JWT_SECRET=<generate-a-long-random-value>
GEMINI_API_KEY=<your-gemini-key>
GEMINI_MODEL=gemini-3.5-flash
RESEND_API_KEY=<your-resend-key>
RESEND_FROM=PSXviewAI <onboarding@resend.dev>
```

Generate `JWT_SECRET` locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For Resend testing, `onboarding@resend.dev` can send only under Resend's testing
rules. For real users, verify a sending domain in Resend and set `RESEND_FROM`
to an address on that domain.

Do not add `PORT`; Railway injects it automatically and the container listens on
that value.

## 5. Verify the deployment

Open these URLs, replacing the hostname with the generated Railway domain:

- `https://YOUR-DOMAIN/` — React application
- `https://YOUR-DOMAIN/api/health` — backend health
- `https://YOUR-DOMAIN/docs` — API documentation

Then register a test account, verify the email code, save a valuation, and reload
the app to confirm the `/data` database survives.

## Local production-style check

If Docker Desktop is installed:

```powershell
docker build -t psxviewai .
docker run --rm -p 8000:8000 --env-file backend/.env psxviewai
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/api/health`.

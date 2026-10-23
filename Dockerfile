# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts ./
COPY frontend ./frontend
RUN npm run build


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    FRONTEND_DIST=/app/dist

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend ./
COPY economic-news-intelligence-pipeline /app/economic-news-intelligence-pipeline
COPY --from=frontend-build /build/dist /app/dist

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

heat-chronicle is a Japanese-language web app that visualizes daily maximum temperature data from Japan Meteorological Agency (JMA) weather stations as a heatmap. It scrapes historical data from JMA's public website and caches it in PostgreSQL. The full specification is in SPEC.md (Japanese).

## Development Commands

### Backend (from `backend/`)
```bash
poetry install                                            # Install dependencies
poetry run uvicorn app.main:app --reload --port 8000      # Dev server
poetry run pytest tests/ -v                               # Run all tests
poetry run pytest tests/test_jma_parser.py::test_name -v  # Run a single test
poetry run black . && poetry run isort .                  # Format
poetry run flake8 .                                       # Lint
poetry run mypy .                                         # Type check
poetry run alembic upgrade head                           # Run migrations
```

### Frontend (from `frontend/`)
```bash
npm install       # Install dependencies
npm run dev       # Dev server (port 3000)
npm run build     # Production build
npm run lint      # ESLint
```

### Database & Full Stack
```bash
docker compose up database        # Start PostgreSQL only
docker compose up                 # Start all services (database + backend + frontend)
```

## Architecture

### Backend (Python/FastAPI)

Layered architecture with four layers:

- **presentation/api/** — FastAPI routers (HTTP handlers)
- **application/** — Service layer (ScrapeService for SSE streaming fetch, TemperatureService for cached queries)
- **domain/** — Pydantic response schemas
- **infrastructure/** — Database (async SQLAlchemy + asyncpg), repositories, JMA scraper

Key patterns:
- **Repository pattern**: `StationRepository` and `TemperatureRepository` encapsulate all DB queries
- **DI via FastAPI Depends**: `SessionDep` (auto-commit/rollback) for normal endpoints, `ManualSessionDep` for SSE streaming where the session must outlive the response
- **Async-first**: asyncpg for queries, httpx for HTTP, async SQLAlchemy sessions
- **SSE streaming**: `GET /api/temperature/{id}/stream` emits `progress`, `data`, `complete`, `error` events
- **Rate-limited scraping**: JmaClient enforces 2-second minimum interval between JMA requests with 3 retries + exponential backoff
- **PostgreSQL schema**: All tables live in the `heat` schema (set via `search_path` for `heat_user`)

### Frontend (Next.js / TypeScript)

Single-page client component at `/`. Feature-based organization:

- `src/features/heatmap/` — Heatmap components and utilities (Canvas 2D rendering, color scale, data grid)
- `src/features/shared/libs/` — API client (fetch wrapper) and SSE client
- `src/components/ui/` — shadcn/ui primitives (Radix UI)
- `src/hooks/` — Custom hooks (temperature data fetching with REST + SSE fallback)
- `src/types/` — TypeScript interfaces matching backend schemas

Data flow: fetch stations via REST → user selects station → fetch cached data via REST → if data is missing, open SSE stream to `/api/temperature/{id}/stream` → heatmap re-renders incrementally as records arrive.

### Database

PostgreSQL 17 with three tables in the `heat` schema:
- `stations` — 12 seeded weather observation stations
- `daily_temperature` — Daily records (unique on station_id + date), upserted with ON CONFLICT DO NOTHING
- `fetch_log` — Tracks which (station, year, month) combos have been scraped

### API Endpoints

- `GET /health` — Health check
- `GET /api/stations` — List all stations
- `GET /api/temperature/{station_id}?start_year=&end_year=` — Cached temperature data
- `GET /api/temperature/{station_id}/stream?start_year=&end_year=` — SSE stream for fetching missing data

## Environment

Each service has a `.env.local` file (gitignored):
- `backend/.env.local`: `DATABASE_URL` (asyncpg), `ALEMBIC_DATABASE_URL` (psycopg2)
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `database/.env.local`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

## Code Style

- Backend: black (line-length 88), isort (profile "black"), flake8, mypy (strict)
- Frontend: ESLint (next core-web-vitals + typescript), Tailwind CSS v4, shadcn/ui (new-york style)
- Path alias: `@/*` maps to `./src/*` in frontend

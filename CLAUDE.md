# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

heat-chronicle is a Japanese-language web app that visualizes daily maximum temperature data from Japan Meteorological Agency (JMA) weather stations as a heatmap. It scrapes historical data from JMA's public website and caches it in DynamoDB. The full specification is in SPEC.md (Japanese).

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
docker compose up dynamodb-local    # Start DynamoDB Local only
docker compose up                   # Start all services (dynamodb-local + backend + frontend)
```

## Architecture

### Backend (Python/FastAPI)

Layered architecture with four layers:

- **presentation/api/** — FastAPI routers (HTTP handlers)
- **application/** — Service layer (ScrapeService for synchronous per-month fetch from JMA, TemperatureService for cached queries)
- **domain/** — Pydantic response schemas
- **infrastructure/** — Database (DynamoDB via boto3), repositories, JMA scraper

Key patterns:
- **Repository pattern**: `StationRepository` and `TemperatureRepository` encapsulate all DB queries
- **DI via FastAPI Depends**: `StationRepoDep`, `TempRepoDep` via FastAPI Depends
- **Rate-limited scraping**: JmaClient enforces 2-second minimum interval between JMA requests with 3 retries + exponential backoff

### Frontend (Next.js / TypeScript)

Single-page client component at `/`. Feature-based organization:

- `src/features/heatmap/` — Heatmap components and utilities (Canvas 2D rendering, color scale, data grid)
- `src/features/shared/libs/` — API client (fetch wrapper)
- `src/components/ui/` — shadcn/ui primitives (Radix UI)
- `src/hooks/` — Custom hooks (temperature data fetching)
- `src/types/` — TypeScript interfaces matching backend schemas

Data flow: fetch stations via REST → user selects station → fetch cached data via REST → if data is missing, sequentially fetch each month via GET `/api/temperature/{id}/fetch-month` → heatmap re-renders incrementally as records arrive.

### Database

DynamoDB with three tables:
- `stations` — Weather observation stations (PK: id, GSI: prec_no-index)
- `daily-temperature` — Daily records (PK: station_id + date)
- `fetch-log` — Tracks which (station, year_month) combos have been scraped (PK: station_id + year_month)

### API Endpoints

- `GET /health` — Health check
- `GET /api/prefectures` — List all prefectures
- `GET /api/stations` — List all stations (optional: `?prec_no=` filter)
- `GET /api/temperature/{station_id}?start_year=&end_year=` — Cached temperature data with metadata
- `GET /api/temperature/{station_id}/fetch-month?year=&month=` — Fetch and return one month of data (scrapes from JMA if not cached)

## Environment

Each service has a `.env.local` file (gitignored):
- `backend/.env.local`: `DYNAMODB_ENDPOINT_URL` (local development, optional), `DYNAMODB_REGION`, `DYNAMODB_TABLE_PREFIX`, `CORS_ALLOW_ORIGINS`
- `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Code Style

- Backend: black (line-length 88), isort (profile "black"), flake8, mypy (strict)
- Frontend: ESLint (next core-web-vitals + typescript), Tailwind CSS v4, shadcn/ui (new-york style)
- Path alias: `@/*` maps to `./src/*` in frontend

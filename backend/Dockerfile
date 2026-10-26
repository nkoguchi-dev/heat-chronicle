FROM ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff AS uv
FROM python:3.14-slim

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

# Keep the Linux environment outside /app so source bind mounts cannot replace it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

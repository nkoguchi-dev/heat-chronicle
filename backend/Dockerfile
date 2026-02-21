FROM python:3.12-slim

WORKDIR /app

# Poetry インストール
RUN pip install poetry

# 依存関係インストール
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# アプリケーションコピー
COPY . .

# エントリポイント
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM python:3.14-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY conf ./conf
COPY migrations ./migrations
COPY app ./app
COPY main.py ./

ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]

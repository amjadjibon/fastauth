# fastauth

JWT authentication API built with FastAPI, SQLModel, and Alembic. Supports SQLite for local development and PostgreSQL for production.

## Stack

- **FastAPI** — web framework
- **SQLModel** — ORM (SQLAlchemy + Pydantic)
- **Alembic** — database migrations
- **bcrypt** — password hashing
- **python-jose** — JWT tokens
- **aiosqlite** / **asyncpg** — async DB drivers

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | — | Create account, returns token pair |
| `POST` | `/auth/login` | — | Authenticate, returns token pair |
| `POST` | `/auth/refresh` | — | Swap refresh token for new pair |
| `GET` | `/auth/me` | Bearer | Current user profile |
| `GET` | `/healthz` | — | Health check (DB ping) |
| `GET` | `/livez` | — | Liveness check |

## Setup

Copy the example env file and fill in required values:

```bash
cp .env.example .env
```

| Variable | Default | Required |
|----------|---------|----------|
| `SECRET_KEY` | — | yes |
| `ALGORITHM` | `HS256` | no |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | `60` | no |
| `REFRESH_TOKEN_EXPIRE_SECONDS` | `3600` | no |
| `DATABASE_URL` | `sqlite+aiosqlite:///fastauth.db` | no |

## Local development

```bash
uv sync
uv run fastapi dev src/main.py
```

Migrations run automatically on startup. API docs at <http://localhost:8000/docs>.

## Docker Compose (PostgreSQL)

```bash
docker compose up --build
```

Starts PostgreSQL and the app at <http://localhost:8000>.

## Migrations

```bash
# generate after model changes
uv run alembic revision --autogenerate -m "description"

# apply
uv run alembic upgrade head

# roll back one step
uv run alembic downgrade -1

# show current state
uv run alembic current
```

## Tests

```bash
uv run pytest
```

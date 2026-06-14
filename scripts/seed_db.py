"""Bulk-seed load-test users directly into the DB, bypassing the HTTP rate limiter.

Usage:
    DATABASE_URL=postgresql://... SECRET_KEY=... uv run python scripts/seed_db.py
    DATABASE_URL=sqlite:///fastauth.db SECRET_KEY=dev uv run python scripts/seed_db.py --count 10

The script is idempotent — re-running with the same prefix skips already-existing users.
"""

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure the project root is on sys.path so `app.*` imports resolve
# regardless of how the script is invoked (python scripts/seed_db.py vs -m).
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.models import UserRole
from app.auth.models import User
from app.core.config import settings
from app.core.security import hash_password

USER_ROLE_ID = "00000000-0000-0000-0000-000000000002"
ADMIN_ROLE_ID = "00000000-0000-0000-0000-000000000001"

_SQLITE_MAX_PARAMS = 999


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def seed(count: int, prefix: str, password: str, output: Path, add_admin: bool) -> None:
    engine = create_async_engine(settings.async_database_url, echo=False)
    is_sqlite = settings.is_sqlite
    now = datetime.now(UTC)

    # Hash once — bcrypt takes ~250ms per call; reuse the same hash for all rows.
    print("Hashing password (once)…")
    hashed = hash_password(password)

    # Build user rows
    user_rows = [
        {
            "id": str(uuid.uuid4()),
            "username": f"{prefix}_{i:06d}",
            "email": f"{prefix}_{i:06d}@loadtest.invalid",
            "hashed_password": hashed,
            "created_at": now,
            "updated_at": now,
        }
        for i in range(1, count + 1)
    ]

    if add_admin:
        user_rows.append(
            {
                "id": str(uuid.uuid4()),
                "username": f"{prefix}_admin",
                "email": f"{prefix}_admin@loadtest.invalid",
                "hashed_password": hashed,
                "created_at": now,
                "updated_at": now,
            }
        )

    print(f"Inserting {len(user_rows)} users…")
    async with engine.begin() as conn:
        if is_sqlite:
            chunk_size = _SQLITE_MAX_PARAMS // len(user_rows[0])
            for chunk in _chunks(user_rows, chunk_size):
                await conn.execute(insert(User).prefix_with("OR IGNORE").values(chunk))
        else:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = (
                pg_insert(User)
                .values(user_rows)
                .on_conflict_do_nothing(index_elements=["username"])
            )
            await conn.execute(stmt)

        # Resolve which rows actually exist (handles partial re-runs gracefully).
        usernames = [r["username"] for r in user_rows]
        if is_sqlite:
            id_map: dict[str, str] = {}
            for chunk in _chunks(usernames, _SQLITE_MAX_PARAMS):
                placeholders = ", ".join(f":n{i}" for i in range(len(chunk)))
                result = await conn.execute(
                    text(f'SELECT id, username FROM "user" WHERE username IN ({placeholders})'),
                    {f"n{i}": v for i, v in enumerate(chunk)},
                )
                id_map.update({row.username: row.id for row in result})
        else:
            result = await conn.execute(
                text('SELECT id, username FROM "user" WHERE username = ANY(:names)'),
                {"names": usernames},
            )
            id_map = {row.username: row.id for row in result}

        # Bulk insert user_roles
        role_rows = [
            {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "role_id": ADMIN_ROLE_ID if uname.endswith("_admin") else USER_ROLE_ID,
                "assigned_at": now,
                "assigned_by": None,
            }
            for uname, uid in id_map.items()
        ]
        if role_rows:
            if is_sqlite:
                chunk_size = _SQLITE_MAX_PARAMS // len(role_rows[0])
                for chunk in _chunks(role_rows, chunk_size):
                    await conn.execute(insert(UserRole).prefix_with("OR IGNORE").values(chunk))
            else:
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                role_stmt = (
                    pg_insert(UserRole)
                    .values(role_rows)
                    .on_conflict_do_nothing(constraint="uq_user_role")
                )
                await conn.execute(role_stmt)

    await engine.dispose()

    # Write JSON manifest for k6 SharedArray
    manifest = [
        {"username": r["username"], "password": password}
        for r in user_rows
        if r["username"] in id_map
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2))
    print(f"Done: {len(manifest)} users written to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed load-test users into the database")
    parser.add_argument(
        "--count", type=int, default=500, help="Number of users to create (default: 500)"
    )
    parser.add_argument(
        "--prefix", type=str, default="loadtest", help="Username/email prefix (default: loadtest)"
    )
    parser.add_argument(
        "--password", type=str, default="LoadTest123!", help="Shared password for all seeded users"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("tests/load/users.json"), help="Output JSON path for k6"
    )
    parser.add_argument(
        "--admin", action="store_true", help="Also create an admin user ({prefix}_admin)"
    )
    args = parser.parse_args()
    asyncio.run(seed(args.count, args.prefix, args.password, args.output, args.admin))


if __name__ == "__main__":
    main()

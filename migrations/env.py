import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlmodel import SQLModel

# import models so their metadata is registered before autogenerate
import app.auth.models  # noqa: F401
from app.core.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _set_nano_rev_id(_context, _revision, directives):  # type: ignore[override]
    if directives:
        directives[0].rev_id = str(int(time.time()))


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_set_nano_rev_id,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.sync_database_url, poolclass=None)

    with engine.connect() as conn:
        context.configure(
            connection=conn,
            target_metadata=target_metadata,
            process_revision_directives=_set_nano_rev_id,
        )
        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import asyncio
from logging.config import fileConfig

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Attempt to import SQLAlchemy Base; if not present (Firestore-only), set None
try:
    from app.models.base import Base
    target_metadata = Base.metadata
except Exception:
    target_metadata = None

# --- Custom part to load config from Pydantic settings (left for completeness) ---
from app.core.config import settings

# Keep SQL URL logic for users who still want to run migrations locally
sync_db_url = getattr(settings, 'DATABASE_URL_SYNC', None)
if not sync_db_url:
    sync_db_url = getattr(settings, 'DATABASE_URL', None)

if sync_db_url:
    config.set_main_option("sqlalchemy.url", str(sync_db_url))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # If there's no SQL URL configured, skip online migrations in Firestore mode.
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        print("No SQL database configured - skipping Alembic online migrations.")
        return

    from sqlalchemy import pool
    from sqlalchemy.ext.asyncio import async_engine_from_config

    connectable = async_engine_from_config(
        config.get_section(config.config_main_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
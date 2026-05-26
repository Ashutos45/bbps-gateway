import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import our settings and base metadata
from app.core.config import settings
from app.database.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy URL dynamically from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))


# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations synchronously inside the database connection context."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    # Create the asynchronous connectable engine
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        # Alembic runs migrations synchronously, so we must run it in a sync block
        # within the async connection using connection.run_sync
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    try:
        # Check if there is an active event loop running
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # In some contexts (e.g. testing), an event loop might already be running
        loop.create_task(run_migrations_online())
    else:
        asyncio.run(run_migrations_online())

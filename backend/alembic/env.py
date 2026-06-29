import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Load .env if present (for local runs)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import all models so Alembic can see them
from app.database import Base
import app.models.user        # noqa: F401
import app.models.project     # noqa: F401
import app.models.timesheet   # noqa: F401
import app.models.allocation  # noqa: F401
import app.models.expense     # noqa: F401

config = context.config

# Override sqlalchemy.url from env if set
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    # Railway sometimes uses postgres:// — rewrite to postgresql:// for SQLAlchemy + psycopg2
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

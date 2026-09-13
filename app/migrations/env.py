from alembic import context
from sqlalchemy import URL

from app import db
from app.models import Base
from app.settings import Settings

settings = Settings()
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=URL.create(
            "sqlite", database=str(settings.DATABASE_PATH.resolve())
        ),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = db.create_database_engine(settings.DATABASE_PATH)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

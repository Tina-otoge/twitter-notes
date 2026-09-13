import shutil
from pathlib import Path

import sqlalchemy
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app import db


def test_standalone_alembic_does_not_create_application_tables(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    source = Path(ScriptDirectory.from_config(config).dir)
    assert source == root / "app" / "migrations"
    scripts = tmp_path / "migrations"
    (scripts / "versions").mkdir(parents=True)
    for filename in ("env.py", "script.py.mako"):
        shutil.copy2(source / filename, scripts / filename)
    config.set_main_option("script_location", str(scripts))
    database_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    assert ScriptDirectory.from_config(config).get_heads() == []
    command.current(config)

    engine = db.create_database_engine(database_path)
    try:
        assert sqlalchemy.inspect(engine).get_table_names() == []
    finally:
        engine.dispose()

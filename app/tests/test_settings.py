import sqlite3
from datetime import timedelta

import sqlalchemy

import app as application
from app import db
from app.models import Note
from app.settings import Settings


def test_settings_and_database(tmp_path):
    settings = Settings(
        _env_file=None, SECRET_KEY="s" * 32, DATABASE_PATH=tmp_path / "notes.db"
    )
    assert settings.LOGIN_TOKEN_EXPIRY == timedelta(days=30)
    app = application.create_app(settings)
    with app.app_context():
        connection = db.get_session().connection().connection.driver_connection
        assert connection.getconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_FKEY)
        assert (
            db.get_session().scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(Note)
            )
            == 0
        )
        assert app.extensions["db_engine"].url.database == str(
            settings.DATABASE_PATH.resolve()
        )
    assert "sqlalchemy" not in app.extensions
    assert "migrate" not in app.extensions

from sqlalchemy.orm import Session

import app as application
from app import db
from app.models import User
from app.settings import Settings


def test_session_teardown_rolls_back_uncommitted_writes(app):
    with app.app_context():
        session = db.get_session()
        assert isinstance(session, Session)
        assert db.get_session() is session
        session.add(User(id="99", username="uncommitted"))
        session.flush()
        assert session.in_transaction()
    assert not session.in_transaction()
    with app.app_context():
        assert db.get_session() is not session
        assert db.get_session().get(User, "99") is None


def test_sessions_and_engines_are_isolated_between_apps(app, tmp_path):
    other = application.create_app(
        Settings(
            _env_file=None,
            SECRET_KEY="s" * 32,
            DATABASE_PATH=tmp_path / "other.db",
        )
    )
    with app.app_context():
        first_session = db.get_session()
        assert first_session.get(User, "1") is not None
        with other.app_context():
            assert db.get_session() is not first_session
            assert db.get_session().get(User, "1") is None
        assert db.get_session() is first_session
    assert app.extensions["db_engine"] is not other.extensions["db_engine"]

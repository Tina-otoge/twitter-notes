import pytest

import app as application
from app import auth, db
from app.models import User
from app.settings import Settings


@pytest.fixture
def app(tmp_path):
    app = application.create_app(
        Settings(
            _env_file=None,
            SECRET_KEY="s" * 32,
            DATABASE_PATH=tmp_path / "notes.db",
            COOKIE_SECURE=False,
            TWITTER_CLIENT_ID="test-client",
        )
    )
    app.config["TESTING"] = True
    with app.app_context():
        db.get_session().add_all(
            [User(id="1", username="alice"), User(id="2", username="bob")]
        )
        db.get_session().commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def headers(app):
    with app.app_context():
        return {
            "Authorization": "Bearer " + auth.create_api_token("1", "Firefox")
        }


@pytest.fixture
def logged_in(app, client):
    with app.app_context():
        client.set_cookie("login_token", auth.issue_login_token("1"))
    with client.session_transaction() as session:
        session["csrf_token"] = "test-csrf"
    return client

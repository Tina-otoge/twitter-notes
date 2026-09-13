from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import jwt
import sqlalchemy

from app import db
from app.models import ApiToken, Tag


def test_dashboard_and_tag_crud(app, logged_in):
    for path in ("/", "/tags", "/tokens"):
        response = logged_in.get(path)
        assert response.status_code == 200
        assert b"bootstrap@5.3.8" in response.data
    form = {"csrf_token": "test-csrf", "name": "Friends", "color": "#ff0000"}
    assert logged_in.post("/tags", data=form).status_code == 302
    with app.app_context():
        tag_id = db.get_session().scalar(sqlalchemy.select(Tag.id))
    form["name"] = "Colleagues"
    logged_in.post(f"/tags/{tag_id}", data=form)
    assert b"Colleagues" in logged_in.get("/tags").data
    logged_in.post(f"/tags/{tag_id}/delete", data={"csrf_token": "test-csrf"})
    assert b"Colleagues" not in logged_in.get("/tags").data


def test_front_note_edit_search_and_escape(logged_in, headers):
    logged_in.put(
        "/api/notes/123",
        json={"username": "someone", "body": "<script>alert(1)</script>"},
        headers=headers,
    )
    page = logged_in.get("/").data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert b"@someone" not in logged_in.get("/?q=missing").data
    logged_in.post(
        "/notes/123",
        data={
            "csrf_token": "test-csrf",
            "username": "someone",
            "body": "Updated",
        },
    )
    assert b"Updated" in logged_in.get("/").data
    logged_in.post("/notes/123/delete", data={"csrf_token": "test-csrf"})
    assert b"No notes yet" in logged_in.get("/").data


def test_token_shown_once_and_revoked(app, logged_in):
    page = logged_in.post(
        "/tokens", data={"csrf_token": "test-csrf", "name": "Chrome"}
    )
    assert page.status_code == 200
    assert b"New token (shown once)" in page.data
    assert b"New token (shown once)" not in logged_in.get("/tokens").data
    with app.app_context():
        token_id = db.get_session().scalar(sqlalchemy.select(ApiToken.id))
    logged_in.post(
        f"/tokens/{token_id}/delete", data={"csrf_token": "test-csrf"}
    )
    with app.app_context():
        assert (
            db.get_session().scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(ApiToken)
            )
            == 0
        )


def test_oauth_callback_sets_expiring_jwt(app, client):
    twitter = Mock()
    twitter.get.return_value.json.return_value = {
        "data": {"id": "55", "username": "new_user"}
    }
    app.extensions["twitter"] = twitter
    response = client.get(
        "/auth/callback?code=accepted&state=verified-by-authlib"
    )
    assert response.status_code == 302
    cookie = client.get_cookie("login_token")
    assert cookie.http_only
    assert cookie.same_site == "Lax"
    claims = jwt.decode(
        cookie.value,
        app.secret_key,
        algorithms=["HS256"],
        audience="twitter-notes-browser",
        issuer="twitter-notes",
    )
    assert claims["sub"] == "55"
    assert claims["exp"] - claims["iat"] == 30 * 24 * 60 * 60
    assert "Max-Age=2592000" in response.headers.get("Set-Cookie")
    assert client.get("/").status_code == 200


def test_expired_jwt_redirects(app, client):
    past = datetime.now(timezone.utc) - timedelta(days=2)
    token = jwt.encode(
        {
            "sub": "1",
            "iat": past,
            "exp": past + timedelta(days=1),
            "aud": "twitter-notes-browser",
            "iss": "twitter-notes",
        },
        app.secret_key,
        algorithm="HS256",
    )
    client.set_cookie("login_token", token)
    assert client.get("/").location == "/login"

import sqlalchemy

from app import auth, db
from app.models import ApiToken, Tag


def test_login_redirect_and_pkce(client):
    assert client.get("/").location == "/login"
    response = client.get("/login")
    assert response.status_code == 302
    assert response.location.startswith("https://x.com/i/oauth2/authorize?")
    assert "code_challenge_method=S256" in response.location
    assert "state=" in response.location
    assert client.get("/auth/callback?code=fake&state=wrong").status_code == 400


def test_api_requires_bearer_even_with_cookie(logged_in):
    assert logged_in.get("/api/me").status_code == 401


def test_notes_crud_and_owner_isolation(app, client, headers):
    payload = {
        "username": "someone",
        "body": "Private <script>text</script>",
        "tag_ids": [],
    }
    assert (
        client.put("/api/notes/123", json=payload, headers=headers).status_code
        == 200
    )
    assert (
        client.get("/api/notes/123", headers=headers).json["note"]["body"]
        == payload["body"]
    )
    with app.app_context():
        other = {
            "Authorization": "Bearer " + auth.create_api_token("2", "Other")
        }
    assert client.get("/api/notes/123", headers=other).json["note"] is None
    client.delete("/api/notes/123", headers=other)
    assert (
        client.get("/api/notes/123", headers=headers).json["note"] is not None
    )
    client.delete("/api/notes/123", headers=headers)
    assert client.get("/api/notes/123", headers=headers).json["note"] is None


def test_tag_ownership_atomicity_and_cascade(app, client, headers):
    with app.app_context():
        db.get_session().add_all(
            [
                Tag(id=1, owner_id="1", name="Friend", color="#198754"),
                Tag(id=2, owner_id="2", name="Other", color="#198754"),
            ]
        )
        db.get_session().commit()
    payload = {"username": "someone", "body": "Original", "tag_ids": [1]}
    assert (
        client.put("/api/notes/123", json=payload, headers=headers).status_code
        == 200
    )
    payload.update(body="Changed", tag_ids=[2])
    assert (
        client.put("/api/notes/123", json=payload, headers=headers).status_code
        == 400
    )
    assert (
        client.get("/api/notes/123", headers=headers).json["note"]["body"]
        == "Original"
    )
    with app.app_context():
        db.get_session().delete(db.get_session().get(Tag, 1))
        db.get_session().commit()
    assert (
        client.get("/api/notes/123", headers=headers).json["note"]["tags"] == []
    )


def test_revocation(app, client, headers):
    assert client.get("/api/me", headers=headers).status_code == 200
    with app.app_context():
        token = headers["Authorization"].split()[1]
        stored_token = db.get_session().scalar(sqlalchemy.select(ApiToken))
        assert stored_token.digest == auth.token_digest(token)
        db.get_session().delete(stored_token)
        db.get_session().commit()
    assert client.get("/api/me", headers=headers).status_code == 401


def test_validation_and_csrf(client, headers, logged_in):
    assert (
        client.put(
            "/api/notes/abc", json={"username": "valid"}, headers=headers
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/notes/1", json={"username": "bad/handle"}, headers=headers
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/notes/1",
            json={"username": "ok", "body": "a" * 10001},
            headers=headers,
        ).status_code
        == 400
    )
    assert (
        logged_in.post("/tags", data={"name": "Missing CSRF"}).status_code
        == 400
    )

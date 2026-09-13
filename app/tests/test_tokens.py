import pytest
import sqlalchemy

from app import db
from app.models import ApiToken


@pytest.mark.parametrize("label", [None, "", "   "])
def test_token_label_is_optional(app, logged_in, label):
    data = {"csrf_token": "test-csrf"}
    if label is not None:
        data["name"] = label
    response = logged_in.post("/tokens", data=data)
    assert response.status_code == 200
    with app.app_context():
        token = db.get_session().scalar(sqlalchemy.select(ApiToken))
        assert token.name == ""
        token_id = token.id
    for page in (response, logged_in.get("/tokens")):
        assert f'<h2 class="token-name">{token_id}</h2>'.encode() in page.data
        assert f'aria-label="Revoke {token_id}"'.encode() in page.data
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


def test_token_label_form_is_not_required(logged_in):
    page = logged_in.get("/tokens").get_data(as_text=True)
    assert "Label (optional)" in page
    label_input = next(
        part for part in page.split("<input") if 'id="token-name"' in part
    )
    assert "required" not in label_input.split(">", 1)[0]


def test_token_label_is_trimmed_and_length_limited(app, logged_in):
    response = logged_in.post(
        "/tokens", data={"csrf_token": "test-csrf", "name": "  Firefox  "}
    )
    assert response.status_code == 200
    assert b'<h2 class="token-name">Firefox</h2>' in response.data
    assert (
        logged_in.post(
            "/tokens", data={"csrf_token": "test-csrf", "name": "a" * 80}
        ).status_code
        == 200
    )
    assert (
        logged_in.post(
            "/tokens", data={"csrf_token": "test-csrf", "name": "a" * 81}
        ).status_code
        == 400
    )
    with app.app_context():
        assert (
            db.get_session().scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(ApiToken)
            )
            == 2
        )

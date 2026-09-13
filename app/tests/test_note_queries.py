import sqlalchemy

from app import db, notes
from app.models import Tag
from app.schemas import NoteInput


def test_search_and_tag_filters_remain_owner_scoped(app, logged_in):
    with app.app_context():
        db.get_session().add_all(
            [
                Tag(id=1, owner_id="1", name="Friend", color="#198754"),
                Tag(id=2, owner_id="2", name="Other", color="#198754"),
            ]
        )
        db.get_session().commit()
        notes.save_note(
            "1",
            "123",
            NoteInput(username="alice_note", body="100% DONE", tag_ids=[1]),
        )
        notes.save_note(
            "1", "456", NoteInput(username="plain_note", body="Done")
        )
        notes.save_note(
            "2",
            "123",
            NoteInput(username="private_note", body="100% DONE", tag_ids=[2]),
        )
    result = logged_in.get("/", query_string={"q": "%"}).data
    assert b"@alice_note" in result
    assert b"@plain_note" not in result
    assert b"@private_note" not in result
    assert b"@alice_note" in logged_in.get("/?q=done&tag=1").data
    assert b"@plain_note" not in logged_in.get("/?tag=1").data
    assert b"No matching notes" in logged_in.get("/?tag=2").data


def test_duplicate_tag_rolls_back_and_preserves_existing_tag(app, logged_in):
    form = {"csrf_token": "test-csrf", "name": "Friend", "color": "#198754"}
    logged_in.post("/tags", data=form)
    form["name"] = "FRIEND"
    result = logged_in.post("/tags", data=form, follow_redirects=True)
    assert result.status_code == 200
    assert b"A tag with that name already exists." in result.data
    with app.app_context():
        assert (
            db.get_session().scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(Tag)
            )
            == 1
        )
    form["name"] = "Colleague"
    assert logged_in.post("/tags", data=form).status_code == 302
    with app.app_context():
        assert (
            db.get_session().scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(Tag)
            )
            == 2
        )

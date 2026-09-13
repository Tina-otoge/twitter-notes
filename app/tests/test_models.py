import pytest
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db
from app.models import ApiToken, Base, Note, NoteTag, Tag, User


def test_models_create_schema_and_enforce_ownership(tmp_path):
    engine = db.create_database_engine(tmp_path / "models.db")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert set(sqlalchemy.inspect(engine).get_table_names()) == {
            "users",
            "api_tokens",
            "notes",
            "tags",
            "note_tags",
        }
        session.add_all(
            [User(id="1", username="alice"), User(id="2", username="bob")]
        )
        session.commit()
        session.add_all(
            [
                Tag(id=1, owner_id="1", name="Friend", color="#198754"),
                Tag(id=2, owner_id="2", name="Other", color="#198754"),
                Note(
                    owner_id="1",
                    user_id="123",
                    username="someone",
                    body="Private",
                ),
            ]
        )
        session.commit()
        session.add(NoteTag(owner_id="1", user_id="123", tag_id=2))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(NoteTag(owner_id="1", user_id="123", tag_id=1))
        session.commit()
        note = session.get(Note, ("1", "123"))
        assert note.to_dict()["tags"][0]["name"] == "Friend"
        session.add(Tag(owner_id="1", name="FRIEND", color="#198754"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.delete(session.get(Tag, 1))
        session.commit()
        assert session.scalars(sqlalchemy.select(NoteTag)).all() == []
        assert session.get(Note, ("1", "123")).body == "Private"
        session.add(ApiToken(owner_id="1", digest="test", prefix="tn_test"))
        session.commit()
        session.delete(session.get(User, "1"))
        session.commit()
        assert session.scalars(sqlalchemy.select(Note)).all() == []
        assert session.scalars(sqlalchemy.select(ApiToken)).all() == []

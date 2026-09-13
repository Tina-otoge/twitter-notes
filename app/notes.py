import flask
import sqlalchemy
from sqlalchemy.dialects import sqlite

from app import db, schemas
from app.models import Note, NoteTag, Tag


def list_tags(owner_id):
    return [
        tag.to_dict()
        for tag in db.get_session().scalars(
            sqlalchemy.select(Tag)
            .where(Tag.owner_id == owner_id)
            .order_by(Tag.name)
        )
    ]


def get_note(owner_id, user_id):
    if not schemas.valid_user_id(user_id):
        flask.abort(400, description="Invalid Twitter user ID.")
    note = db.get_session().get(Note, (owner_id, user_id))
    return note.to_dict() if note is not None else None


def save_note(owner_id, user_id, data):
    if not schemas.valid_user_id(user_id):
        flask.abort(400, description="Invalid Twitter user ID.")
    tag_ids = set(data.tag_ids)
    owned_ids = set(
        db.get_session().scalars(
            sqlalchemy.select(Tag.id).where(Tag.owner_id == owner_id)
        )
    )
    if not tag_ids.issubset(owned_ids):
        flask.abort(400, description="One or more tags do not belong to you.")
    db.get_session().execute(
        sqlite.insert(Note)
        .values(
            owner_id=owner_id,
            user_id=user_id,
            username=data.username,
            body=data.body,
        )
        .on_conflict_do_update(
            index_elements=[Note.owner_id, Note.user_id],
            set_={
                "username": data.username,
                "body": data.body,
                "updated_at": sqlalchemy.func.current_timestamp(),
            },
        )
    )
    db.get_session().execute(
        sqlalchemy.delete(NoteTag).where(
            NoteTag.owner_id == owner_id, NoteTag.user_id == user_id
        )
    )
    db.get_session().add_all(
        [
            NoteTag(owner_id=owner_id, user_id=user_id, tag_id=tag_id)
            for tag_id in tag_ids
        ]
    )
    db.get_session().commit()
    return get_note(owner_id, user_id)


def delete_note(owner_id, user_id):
    db.get_session().execute(
        sqlalchemy.delete(Note).where(
            Note.owner_id == owner_id, Note.user_id == user_id
        )
    )
    db.get_session().commit()

import flask
import sqlalchemy
from flask import Blueprint
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app import auth, db, notes
from app.models import ApiToken, Note, Tag
from app.schemas import NoteInput, TagInput

front = Blueprint("front", __name__)
front.before_request(auth.login_required(lambda: None))


@front.get("/")
def index():
    query = flask.request.args.get("q", "").strip()[:200]
    tag_filter = flask.request.args.get("tag", type=int)
    page = max(1, flask.request.args.get("page", 1, type=int))
    statement = sqlalchemy.select(Note).where(Note.owner_id == flask.g.user.id)
    if query:
        statement = statement.where(
            sqlalchemy.or_(
                sqlalchemy.func.instr(
                    sqlalchemy.func.lower(Note.username),
                    sqlalchemy.func.lower(query),
                )
                > 0,
                sqlalchemy.func.instr(
                    sqlalchemy.func.lower(Note.body),
                    sqlalchemy.func.lower(query),
                )
                > 0,
            )
        )
    if tag_filter:
        statement = statement.where(Note.tags.any(Tag.id == tag_filter))
    rows = (
        db.get_session()
        .scalars(
            statement.order_by(Note.updated_at.desc(), Note.user_id)
            .limit(21)
            .offset((page - 1) * 20)
        )
        .all()
    )
    return flask.render_template(
        "notes.html",
        notes=[note.to_dict() for note in rows[:20]],
        tags=notes.list_tags(flask.g.user.id),
        query=query,
        tag_filter=tag_filter,
        page=page,
        has_next=len(rows) > 20,
        active="notes",
    )


@front.post("/notes/<user_id>")
def edit_note(user_id):
    if notes.get_note(flask.g.user.id, user_id) is None:
        flask.abort(404)
    data = NoteInput.model_validate(
        {
            "username": flask.request.form.get("username"),
            "body": flask.request.form.get("body", ""),
            "tag_ids": flask.request.form.getlist("tag_ids"),
        }
    )
    notes.save_note(flask.g.user.id, user_id, data)
    flask.flash("Note saved.", "success")
    return flask.redirect(flask.url_for("front.index"))


@front.post("/notes/<user_id>/delete")
def remove_note(user_id):
    notes.delete_note(flask.g.user.id, user_id)
    flask.flash("Note deleted.", "success")
    return flask.redirect(flask.url_for("front.index"))


@front.route("/tokens", methods=["GET", "POST"])
def tokens():
    new_token = None
    if flask.request.method == "POST":
        name = flask.request.form.get("name", "").strip()
        if len(name) > 80:
            flask.abort(
                400,
                description="Token label must contain at most 80 characters.",
            )
        new_token = auth.create_api_token(flask.g.user.id, name)
    rows = (
        db.get_session()
        .scalars(
            sqlalchemy.select(ApiToken)
            .where(ApiToken.owner_id == flask.g.user.id)
            .order_by(ApiToken.id.desc())
        )
        .all()
    )
    return flask.render_template(
        "tokens.html", tokens=rows, new_token=new_token, active="tokens"
    )


@front.post("/tokens/<int:token_id>/delete")
def revoke_token(token_id):
    db.get_session().execute(
        sqlalchemy.delete(ApiToken).where(
            ApiToken.id == token_id, ApiToken.owner_id == flask.g.user.id
        )
    )
    db.get_session().commit()
    flask.flash("API token revoked.", "success")
    return flask.redirect(flask.url_for("front.tokens"))


@front.route("/tags", methods=["GET", "POST"])
def tags():
    if flask.request.method == "POST":
        return store_tag()
    return flask.render_template(
        "tags.html", tags=notes.list_tags(flask.g.user.id), active="tags"
    )


def store_tag(tag_id=None):
    try:
        data = TagInput.model_validate(
            {
                "name": flask.request.form.get("name", ""),
                "color": flask.request.form.get("color", "#198754"),
            }
        )
        if tag_id is None:
            tag = Tag(
                owner_id=flask.g.user.id, name=data.name, color=data.color
            )
            db.get_session().add(tag)
        else:
            tag = db.get_session().scalar(
                sqlalchemy.select(Tag).where(
                    Tag.id == tag_id, Tag.owner_id == flask.g.user.id
                )
            )
            if tag is None:
                flask.abort(404)
            tag.name = data.name
            tag.color = data.color
        db.get_session().commit()
    except IntegrityError:
        db.get_session().rollback()
        flask.flash("A tag with that name already exists.", "danger")
    except ValidationError:
        flask.flash(
            "Enter a tag name (up to 50 characters) and a valid color.",
            "danger",
        )
    else:
        flask.flash("Tag saved.", "success")
    return flask.redirect(flask.url_for("front.tags"))


@front.post("/tags/<int:tag_id>")
def edit_tag(tag_id):
    return store_tag(tag_id)


@front.post("/tags/<int:tag_id>/delete")
def delete_tag(tag_id):
    db.get_session().execute(
        sqlalchemy.delete(Tag).where(
            Tag.owner_id == flask.g.user.id, Tag.id == tag_id
        )
    )
    db.get_session().commit()
    flask.flash("Tag deleted.", "success")
    return flask.redirect(flask.url_for("front.tags"))

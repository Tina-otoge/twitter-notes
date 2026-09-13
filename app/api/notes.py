import flask
from flask import Blueprint

from app import auth, notes
from app.schemas import NoteInput

api = Blueprint("api", __name__, url_prefix="/api")
api.before_request(auth.api_required(lambda: None))


@api.get("/me")
def me():
    return {"id": flask.g.user.id, "username": flask.g.user.username}


@api.get("/tags")
def tags():
    return {"tags": notes.list_tags(flask.g.user.id)}


@api.get("/notes/<user_id>")
def read_note(user_id):
    return {"note": notes.get_note(flask.g.user.id, user_id)}


@api.put("/notes/<user_id>")
def write_note(user_id):
    data = NoteInput.model_validate(flask.request.get_json())
    return {"note": notes.save_note(flask.g.user.id, user_id, data)}


@api.delete("/notes/<user_id>")
def remove_note(user_id):
    notes.delete_note(flask.g.user.id, user_id)
    return "", 204

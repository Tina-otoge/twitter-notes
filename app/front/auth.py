import flask
from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint
from requests import RequestException
from sqlalchemy.dialects import sqlite

from app import auth as authentication
from app import db, schemas
from app.models import User

auth = Blueprint("auth", __name__)


@auth.get("/login")
def login():
    settings = flask.current_app.extensions["settings"]
    if not settings.TWITTER_CLIENT_ID:
        flask.abort(
            503,
            description=(
                "Twitter login is not configured. Set TWITTER_CLIENT_ID."
            ),
        )
    return flask.current_app.extensions["twitter"].authorize_redirect(
        settings.TWITTER_REDIRECT_URI
    )


@auth.get("/auth/callback")
def callback():
    if flask.request.args.get("error"):
        flask.session.clear()
        flask.abort(
            400,
            description=(
                "Twitter authorization was declined. Try signing in again."
            ),
        )
    twitter = flask.current_app.extensions["twitter"]
    try:
        token = twitter.authorize_access_token()
        response = twitter.get("users/me", token=token, timeout=15)
        response.raise_for_status()
        user = response.json()["data"]
        if not schemas.valid_user_id(user["id"]) or not isinstance(
            user["username"], str
        ):
            raise ValueError("Invalid Twitter identity")
    except (OAuthError, RequestException, ValueError, KeyError, TypeError):
        flask.abort(
            400, description="Twitter sign-in failed. Please try again."
        )
    db.get_session().execute(
        sqlite.insert(User)
        .values(id=user["id"], username=user["username"])
        .on_conflict_do_update(
            index_elements=[User.id], set_={"username": user["username"]}
        )
    )
    db.get_session().commit()
    flask.session.clear()
    settings = flask.current_app.extensions["settings"]
    response = flask.redirect(flask.url_for("front.index"))
    response.set_cookie(
        "login_token",
        authentication.issue_login_token(user["id"]),
        max_age=int(settings.LOGIN_TOKEN_EXPIRY.total_seconds()),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="Lax",
    )
    return response


@auth.post("/logout")
def logout():
    flask.session.clear()
    response = flask.redirect(flask.url_for("auth.login"))
    response.delete_cookie("login_token")
    return response

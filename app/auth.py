import functools
import hashlib
import secrets
from datetime import datetime, timezone

import flask
import jwt
import sqlalchemy
from jwt import InvalidTokenError

from app import db
from app.models import ApiToken, User


def issue_login_token(user_id):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now
            + flask.current_app.extensions["settings"].LOGIN_TOKEN_EXPIRY,
            "aud": "twitter-notes-browser",
            "iss": "twitter-notes",
        },
        flask.current_app.secret_key,
        algorithm="HS256",
    )


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        try:
            claims = jwt.decode(
                flask.request.cookies.get("login_token", ""),
                flask.current_app.secret_key,
                algorithms=["HS256"],
                audience="twitter-notes-browser",
                issuer="twitter-notes",
                options={"require": ["sub", "exp", "iat", "aud", "iss"]},
            )
        except InvalidTokenError:
            return flask.redirect(flask.url_for("auth.login"))
        flask.g.user = db.get_session().get(User, claims["sub"])
        if flask.g.user is None:
            return flask.redirect(flask.url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_api_token(owner_id, name=""):
    token = "tn_" + secrets.token_urlsafe(32)
    db.get_session().add(
        ApiToken(
            owner_id=owner_id,
            name=name,
            digest=token_digest(token),
            prefix=token[:11],
        )
    )
    db.get_session().commit()
    return token


def api_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        scheme, _, token = flask.request.headers.get(
            "Authorization", ""
        ).partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 256:
            flask.abort(
                401, description="A valid API bearer token is required."
            )
        flask.g.user = db.get_session().scalar(
            sqlalchemy.select(User)
            .join(ApiToken)
            .where(ApiToken.digest == token_digest(token))
        )
        if flask.g.user is None:
            flask.abort(401, description="API token is invalid or revoked.")
        return view(*args, **kwargs)

    return wrapped


def csrf_token():
    if "csrf_token" not in flask.session:
        flask.session["csrf_token"] = secrets.token_urlsafe(32)
    return flask.session["csrf_token"]


def protect_frontend():
    if (
        flask.request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and flask.request.blueprint != "api"
    ):
        expected = flask.session.get("csrf_token", "")
        supplied = flask.request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, supplied):
            flask.abort(
                400, description="Form expired. Reload the page and try again."
            )

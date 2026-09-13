import flask
from flask import Flask
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app import auth, db, twitter
from app.api import notes as notes_api
from app.front import auth as auth_front
from app.front import dashboard
from app.models import Base
from app.settings import Settings


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    app = Flask(__name__)
    settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY.get_secret_value(),
        DATABASE_PATH=str(settings.DATABASE_PATH.resolve()),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=settings.COOKIE_SECURE,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    app.extensions["settings"] = settings
    db.init_db(app)
    app.before_request(auth.protect_frontend)
    app.jinja_env.globals["csrf_token"] = auth.csrf_token
    twitter.init_twitter(app, settings)
    app.register_blueprint(auth_front.auth)
    app.register_blueprint(dashboard.front)
    app.register_blueprint(notes_api.api)

    @app.errorhandler(HTTPException)
    def http_error(error):
        if flask.request.path.startswith("/api/"):
            return flask.jsonify(error=error.description), error.code
        return (
            flask.render_template("error.html", error=error.description),
            error.code,
        )

    @app.errorhandler(ValidationError)
    def validation_error(error):
        message = "Invalid input. Check field lengths, handle, and tag IDs."
        if flask.request.path.startswith("/api/"):
            return flask.jsonify(error=message), 400
        return flask.render_template("error.html", error=message), 400

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        return response

    Base.metadata.create_all(bind=app.extensions["db_engine"])
    return app

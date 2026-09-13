import sqlite3
from pathlib import Path
from sqlite3 import Connection

import flask
import sqlalchemy
from sqlalchemy import URL, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def enable_foreign_keys(connection, connection_record):
    if isinstance(connection, Connection):
        connection.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_FKEY, True)


def create_database_engine(database_path: Path) -> Engine:
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = sqlalchemy.create_engine(
        URL.create("sqlite", database=str(database_path)),
        connect_args={"timeout": 10},
    )
    event.listen(engine, "connect", enable_foreign_keys)
    return engine


def init_db(app):
    engine = create_database_engine(Path(app.config["DATABASE_PATH"]))
    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = sessionmaker(bind=engine)
    app.teardown_appcontext(close_session)


def get_session() -> Session:
    if "db_session" not in flask.g:
        flask.g.db_session = flask.current_app.extensions[
            "db_session_factory"
        ]()
    return flask.g.db_session


def close_session(error=None):
    session = flask.g.pop("db_session", None)
    if session is not None:
        session.close()

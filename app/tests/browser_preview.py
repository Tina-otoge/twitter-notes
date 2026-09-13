import json
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import flask
from flask import Response

import app as application
from app import auth, db, notes
from app.models import Tag, User
from app.schemas import NoteInput
from app.settings import Settings


def preview():
    with TemporaryDirectory(prefix="twitter-notes-preview-") as temporary:
        app = application.create_app(
            Settings(
                _env_file=None,
                SECRET_KEY=secrets.token_hex(32),
                DATABASE_PATH=Path(temporary) / "preview.db",
                COOKIE_SECURE=False,
            )
        )
        twitter = Mock()
        twitter.get.return_value.json.return_value = {
            "data": {"id": "1", "username": "preview"}
        }
        app.extensions["twitter"] = twitter
        with app.app_context():
            db.get_session().add(User(id="1", username="preview"))
            db.get_session().commit()
            db.get_session().add_all(
                [
                    Tag(id=1, owner_id="1", name="Design", color="#198754"),
                    Tag(id=2, owner_id="1", name="Follow up", color="#db5270"),
                    Tag(
                        id=3, owner_id="1", name="Engineering", color="#347dc4"
                    ),
                ]
            )
            db.get_session().commit()
            notes.save_note(
                "1",
                "123",
                NoteInput(
                    username="someone",
                    body=(
                        "Met at the design meetup. "
                        "Ask about the accessibility study."
                    ),
                    tag_ids=[1, 2],
                ),
            )
            notes.save_note(
                "1",
                "456",
                NoteInput(
                    username="another_person",
                    body=(
                        "Useful SQLite articles and "
                        "thoughtful API design notes."
                    ),
                    tag_ids=[3],
                ),
            )
            api_token = auth.create_api_token("1", "Preview extension")

        @app.get("/fixture-assets/<path:asset>")
        def fixture_asset(asset):
            return flask.send_from_directory(
                Path(__file__).resolve().parents[2] / "extension", asset
            )

        @app.get("/fixture.js")
        def fixture_script():
            script = """
              window.previewRoots = [];
              const attach = Element.prototype.attachShadow;
              Element.prototype.attachShadow = function(options) {
                const root = attach.call(this, options);
                window.previewRoots.push(root);
                return root;
              };
              window.chrome = { runtime: { sendMessage: async (message) => {
                const path = message.action === 'tags'
                  ? '/api/tags' : '/api/notes/' + message.userId;
                const method =
                  {save: 'PUT', delete: 'DELETE'}[message.action] || 'GET';
                const response = await fetch(path, {
                  method, headers: {
                    'Authorization': 'Bearer ' + TOKEN,
                    'Content-Type': 'application/json'
                  },
                  body: message.note ? JSON.stringify(message.note) : undefined
                });
                const data = response.status === 204
                  ? null : await response.json();
                return {ok: response.ok, data, error: data?.error};
              } } };
              window.addEventListener(
                'twitter-notes:request-identities', () => {
                window.dispatchEvent(new CustomEvent('twitter-notes:identity', {
                  detail: JSON.stringify({username: 'someone', userId: '123'})
                }));
              });
            """.replace("TOKEN", json.dumps(api_token))
            return Response(script, mimetype="application/javascript")

        @app.get("/someone")
        def profile_fixture():
            return """<!doctype html><html><head>
              <meta name="viewport" content="width=device-width">
              <title>Profile fixture</title></head><body>
              <main style="max-width:600px;margin:auto">
              <div data-testid="primaryColumn">
              <div data-testid="UserName">Someone @someone</div></div></main>
              <script src="/fixture.js"></script>
              <script src="/fixture-assets/content.js"></script>
              </body></html>"""

        app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)


if __name__ == "__main__":
    preview()

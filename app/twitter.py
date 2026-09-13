from authlib.integrations.flask_client import OAuth


def init_twitter(app, settings):
    oauth = OAuth(app)
    oauth.register(
        name="twitter",
        client_id=settings.TWITTER_CLIENT_ID,
        client_secret=settings.TWITTER_CLIENT_SECRET.get_secret_value(),
        authorize_url="https://x.com/i/oauth2/authorize",
        access_token_url="https://api.x.com/2/oauth2/token",
        api_base_url="https://api.x.com/2/",
        client_kwargs={
            "scope": "tweet.read users.read",
            "code_challenge_method": "S256",
            "token_endpoint_auth_method": (
                "client_secret_basic"
                if settings.TWITTER_CLIENT_SECRET.get_secret_value()
                else "none"
            ),
        },
    )
    app.extensions["twitter"] = oauth.twitter

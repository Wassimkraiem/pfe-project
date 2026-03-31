from flask import Flask, g
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from sev.apps.videos.opensearch.documents.views import blueprint as videos_blueprint
from sev.apps.videos.opensearch.indexes.views import blueprint as indexes_blueprint
from sev.opensearch import create_opensearch_client
from marshmallow import ValidationError
from sev.response import SevErrorResponse


def register_blueprint(app):
    app.register_blueprint(videos_blueprint)
    app.register_blueprint(indexes_blueprint)


def handle_marshmallow_error(err):
    """Return json error for marshmallow validation errors.

    This will avoid having to try/catch ValidationErrors in all endpoints, returning
    correct JSON response with associated HTTP 400 Status
    (https://tools.ietf.org/html/rfc7231#section-6.5.1)
    """
    return SevErrorResponse(err.messages, "validation_error")


def register_error_handlers(app):
    app.register_error_handler(ValidationError, handle_marshmallow_error)


def configure_sentry(app):
    sentry_sdk.init(
        dsn=app.config["SENTRY_DSN"],
        environment=app.config["FLASK_ENV"],
        integrations=[
            FlaskIntegration(),
        ],
        traces_sample_rate=0.1,
    )


def create_app():
    app = Flask(__name__)

    # Apply CORS to all routes and allow all origins/methods/headers
    CORS(app, supports_credentials=True)

    app.config.from_pyfile("../conf/conf.py")
    app.config["debug"] = True
    register_blueprint(app)
    register_error_handlers(app)

    @app.before_request
    def before_request():
        if "video_opensearch" not in g:
            g.video_opensearch = create_opensearch_client(app)

    @app.errorhandler(Exception)
    def handle_exception(e):
        print("An error occurred during a request.")
        return SevErrorResponse(str(e), "internal_server_error"), 500

    return app


bviral_app = create_app()

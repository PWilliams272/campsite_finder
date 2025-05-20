from flask import Blueprint

campsite_bp = Blueprint(
    "campsite_finder",
    __name__,
    template_folder="templates",
    static_folder="static"
)

def create_app():
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(campsite_bp, url_prefix="/")
    return app

from . import routes

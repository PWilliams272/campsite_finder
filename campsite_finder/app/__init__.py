from flask import Blueprint

campsite_bp = Blueprint(
    "campsite_finder",
    __name__,
    template_folder="templates",
    static_folder="static"
)

def create_app():
    import os
    from flask import Flask, url_for
    app = Flask(__name__)
    app.register_blueprint(campsite_bp, url_prefix="/")

    @app.template_global()
    def static_url(filename):
        # Appends the file's mtime as a cache-busting query param, so a
        # deploy always invalidates browsers' cached copy (static files are
        # served with a multi-hour max-age) instead of requiring a hard
        # refresh, as happened with a stale admin.js after a deploy.
        path = os.path.join(campsite_bp.static_folder, filename)
        version = int(os.path.getmtime(path)) if os.path.exists(path) else 0
        return f"{url_for('campsite_finder.static', filename=filename)}?v={version}"

    return app

from . import routes

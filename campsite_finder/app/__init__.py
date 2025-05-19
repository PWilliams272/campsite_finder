from flask import Blueprint

campsite_bp = Blueprint(
    "campsite_finder",
    __name__,
    template_folder="templates",
    static_folder="static"
)
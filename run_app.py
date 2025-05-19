from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from campsite_finder.app import campsite_bp

app = Flask(__name__)
app.register_blueprint(campsite_bp, url_prefix="/")
app.run(debug=True)
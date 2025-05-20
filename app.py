from dotenv import load_dotenv
load_dotenv()

from campsite_finder.app import create_app

app = create_app()
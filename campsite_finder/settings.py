import os

MODE = os.environ.get('CAMPSITE_FINDER_MODE', 'aws').lower()
LOCAL_DATA_DIR = os.environ.get('CAMPSITE_FINDER_LOCAL_DATA', 'data')
import os

def get_mode():
    return os.environ.get('CAMPSITE_FINDER_MODE', 'aws').lower()

def get_local_data_dir():
    return os.environ.get('CAMPSITE_FINDER_LOCAL_DATA', 'data')

def get_s3_bucket():
    return os.environ.get('CAMPSITE_FINDER_S3_BUCKET', 'campsite-finder-data')
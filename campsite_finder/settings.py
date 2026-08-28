import os

def get_mode():
    return os.environ.get('CAMPSITE_FINDER_MODE', 'aws').lower()

def get_local_data_dir():
    return os.environ.get('CAMPSITE_FINDER_LOCAL_DATA', 'data')

def get_s3_bucket():
    return os.environ.get('CAMPSITE_FINDER_S3_BUCKET', 'campsite-finder-data')

def get_notification_cooldown_hours():
    """
    Minimum hours before the same site can trigger a repeat "newly available"
    email. Without this, a site flickering available/unavailable across
    consecutive checks (e.g. an abandoned booking hold) would re-notify every
    cycle.
    """
    return float(os.environ.get('CAMPSITE_FINDER_NOTIFICATION_COOLDOWN_HOURS', 6))
import os
import io
import json
import pickle
from .settings import MODE, LOCAL_DATA_DIR

def _get_local_path(key):
    """
    Returns the local filesystem path for a given key.

    Args:
        key (str): Relative path or filename.

    Returns:
        str: Full path in the local data directory.
    """
    return os.path.join(LOCAL_DATA_DIR, key)

def _s3_client():
    """
    Returns a boto3 S3 client instance.

    Returns:
        boto3.Client: The S3 client.
    """
    import boto3
    return boto3.client('s3')

def load_json(key, bucket='campsitedata'):
    """
    Loads a JSON file from local storage or S3.

    Args:
        key (str): Path to the JSON file.
        bucket (str): S3 bucket name (default: 'campsitedata').

    Returns:
        dict: Loaded JSON data. Returns {} if file not found.
    """
    if MODE == 'local':
        path = _get_local_path(key)
        print(path)
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    else:
        s3 = _s3_client()
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj['Body'].read().decode('utf-8'))

def save_json(data, key, bucket='campsitedata'):
    """
    Saves a dictionary as a JSON file to local storage or S3.

    Args:
        data (dict): Data to save.
        key (str): Path to save the JSON file.
        bucket (str): S3 bucket name (default: 'campsitedata').
    """
    if MODE == 'local':
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        path = _get_local_path(key)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        s3 = _s3_client()
        upload_bytes = json.dumps(data).encode('utf-8')
        s3.put_object(Bucket=bucket, Key=key, Body=upload_bytes)

def load_pickle(key, bucket='campsitedata'):
    """
    Loads a pickled object from local storage or S3.

    Args:
        key (str): Name of the pickle file.
        bucket (str): S3 bucket name (default: 'campsitedata').

    Returns:
        object: Loaded Python object, or None if file not found.
    """
    if MODE == 'local':
        path = _get_local_path(key)
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        s3 = _s3_client()
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pickle.load(io.BytesIO(obj['Body'].read()))

def save_pickle(obj, key, bucket='campsitedata'):
    """
    Saves a Python object as a pickle file to local storage or S3.

    Args:
        obj (object): Object to pickle.
        key (str): Name of the pickle file.
        bucket (str): S3 bucket name (default: 'campsitedata').
    """
    if MODE == 'local':
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        path = _get_local_path(key)
        with open(path, 'wb') as f:
            pickle.dump(obj, f)
    else:
        s3 = _s3_client()
        buf = io.BytesIO()
        pickle.dump(obj, buf)
        buf.seek(0)
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())

def load_config(key='config.json'):
    """
    Loads the configuration JSON file from local storage or S3.

    Args:
        key (str): Path to the config file (default: 'config.json').

    Returns:
        dict: Configuration dictionary.
    """
    return load_json(key)

def save_config(data, key='config.json'):
    """
    Saves the configuration dictionary as a JSON file to local storage or S3.

    Args:
        data (dict): Configuration data.
        key (str): Path to save the config file (default: 'config.json').
    """
    return save_json(data, key)
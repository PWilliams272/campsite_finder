import pandas as pd
from .data_io import load_config, load_pickle, save_pickle
from .availability import check_available, check_for_changes
from .notify import format_email, send_email
import os

def process_config_key(key, params):
    """
    Runs the end-to-end check and notification workflow for a single configuration key.
    
    Args:
        key (str): The config key, used for naming the pickle file.
        params (dict): Configuration parameters for this check, including email recipients and search criteria.
    """
    if params.get('active', False) is False:
        return  # Skip processing if this config is not active
    email_to = params.get('email_to')
    current_availability = check_available(params)
    try:
        previous_availability = load_pickle(f"{key}.pkl")
    except FileNotFoundError:
        previous_availability = pd.DataFrame(columns=current_availability.columns)
    new_full_avail, new_partial_avail = check_for_changes(current_availability, previous_availability)
    save_pickle(current_availability, f"{key}.pkl")
    # Add edit_url to params for email if not present
    if 'edit_url' not in params:
        # Try to build the edit URL (assume Flask app runs at root)
        params = dict(params)  # copy to avoid mutating original
        params['edit_url'] = f"https://{os.environ.get('CAMPSITE_FINDER_DOMAIN', 'localhost')}/edit_config/{key}"
    body = format_email(new_full_avail, new_partial_avail, params)
    if body:
        send_email("New Campsites Available!", body, email_to)

def lambda_handler(event, context):
    """
    AWS Lambda handler function. Loads configuration and processes each config key.
    
    Args:
        event: Lambda event payload.
        context: Lambda context object.
    
    Returns:
        dict: Status message.
    """
    config = load_config()
    for key, params in config.items():
        process_config_key(key, params)
    return {"status": "OK"}
import pandas as pd
from .data_io import load_config, load_pickle, save_pickle
from .availability import check_available, check_for_changes
from .notify import format_email, send_email

def process_config_key(key, params):
    """
    Runs the end-to-end check and notification workflow for a single configuration key.
    
    Args:
        key (str): The config key, used for naming the pickle file.
        params (dict): Configuration parameters for this check, including email recipients and search criteria.
    """
    email_to = params.get('email_to')
    current_availability = check_available(params)
    try:
        previous_availability = load_pickle(f"{key}.pkl")
    except FileNotFoundError:
        previous_availability = pd.DataFrame(columns=current_availability.columns)
    new_full_avail, new_partial_avail = check_for_changes(current_availability, previous_availability)
    save_pickle(current_availability, f"{key}.pkl")
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
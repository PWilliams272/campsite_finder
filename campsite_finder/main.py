import logging
import pandas as pd
from .data_io import load_config, load_pickle, save_pickle
from .availability import check_available, check_for_changes, prune_expired_notifications, apply_cooldown, record_notifications
from .notify import format_email, send_email
from .settings import get_notification_cooldown_hours
import os

logger = logging.getLogger(__name__)

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

    cooldown_hours = get_notification_cooldown_hours()
    try:
        notified_state = load_pickle(f"{key}_notified.pkl")
    except FileNotFoundError:
        notified_state = {}
    notified_state = prune_expired_notifications(notified_state, cooldown_hours)
    # Suppress sites already notified within the cooldown window — otherwise
    # a site flickering available/unavailable across consecutive checks
    # would re-trigger an email every cycle.
    new_full_avail, new_partial_avail = apply_cooldown(new_full_avail, new_partial_avail, notified_state, cooldown_hours)

    # Add edit_url to params for email if not present
    if 'edit_url' not in params:
        # Try to build the edit URL (assume Flask app runs at root)
        params = dict(params)  # copy to avoid mutating original
        params['edit_url'] = f"https://{os.environ.get('CAMPSITE_FINDER_DOMAIN', 'localhost')}/edit_config/{key}"
    body = format_email(new_full_avail, new_partial_avail, params)
    if body:
        send_email("New Campsites Available!", body, email_to)
        notified_state = record_notifications(notified_state, new_full_avail, new_partial_avail)
    save_pickle(notified_state, f"{key}_notified.pkl")

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
    failed_keys = []
    for key, params in config.items():
        try:
            process_config_key(key, params)
        except Exception:
            # One broken/malformed config must not stop every other user's
            # alert from being checked in this run.
            logger.exception("Failed to process config %s", key)
            failed_keys.append(key)
    return {"status": "OK" if not failed_keys else "PARTIAL_FAILURE", "failed_keys": failed_keys}
import logging
from datetime import datetime, timedelta, timezone
from .recreationgov import get_campground_availability
import pandas as pd

logger = logging.getLogger(__name__)

RESULT_COLUMNS = ['CampgroundName', 'CampsiteName', 'CampsiteID', 'Available']

def check_available(params):
    """
    Checks current campsite availability based on given parameters.

    Args:
        params (dict): Must include 'campgrounds', 'start_date', and optionally 'end_date', 'TentsPermitted', 'Partial'.

    Returns:
        pd.DataFrame: DataFrame listing available campsites with relevant columns.
    """
    campgrounds = params.get('campgrounds') or {}
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    if not campgrounds:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    df_list = []
    for campground_name, campground_id in campgrounds.items():
        # One campground's request failing (network hiccup, transient API
        # error) must not abort every other campground in this config — the
        # failed one just gets picked up again next cycle.
        try:
            df = get_campground_availability(campground_id, start_date, end_date)
        except Exception:
            logger.exception("Failed to fetch availability for campground %s (%s)", campground_name, campground_id)
            continue
        df = df[df['CampsiteReservable']]
        if params.get('tents_permitted', True):
            df = df[df['TentsPermitted'] == True]
        if params.get('partial'):
            df = df[df['Available'].isin(['Available', 'Partial'])]
        else:
            df = df[df['Available'] == 'Available']

        # Add functionality here to allow for additional requirements (e.g., has fire pit, capacity, etc.)
        df['CampgroundName'] = campground_name
        df_list.append(df)
    if not df_list:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    return pd.concat(df_list)[RESULT_COLUMNS]

def check_for_changes(data, old_data):
    """
    Compares new and old availability data and finds newly available and newly partial sites.

    Args:
        data (pd.DataFrame): Current DataFrame of availability.
        old_data (pd.DataFrame): Previous DataFrame of availability.

    Returns:
        tuple: (newly_available, newly_partial, site_ids). newly_available/newly_partial are
        dicts {campground_name: [CampsiteName, ...]}. site_ids is {campground_name: {CampsiteName:
        CampsiteID}}, letting callers build a reservation link for any site named above —
        CampsiteID is recreation.gov's own site id (used in its campsite URLs), not something
        this app assigns.
    """
    newly_available = {}
    newly_partial = {}
    site_ids = {}
    for campground_name, new in data.groupby('CampgroundName'):
        prev = old_data[old_data['CampgroundName'] == campground_name]
        newly_available[campground_name] = sorted(list(set(new[new['Available'] == 'Available']['CampsiteName']) - set(prev[prev['Available'] == 'Available']['CampsiteName'])))
        newly_partial[campground_name] = sorted(list(set(new[new['Available'] == 'Partial']['CampsiteName']) - set(prev[prev['Available'] == 'Partial']['CampsiteName'])))
        site_ids[campground_name] = dict(zip(new['CampsiteName'], new['CampsiteID']))
    return newly_available, newly_partial, site_ids

def prune_expired_notifications(notified_state, cooldown_hours):
    """
    Drops notified-site entries older than the cooldown window, so the
    stored state doesn't grow without bound.

    Args:
        notified_state (dict): {campground_name: {CampsiteName: iso_timestamp}}
        cooldown_hours (float): Notification cooldown window, in hours.

    Returns:
        dict: Same shape, with expired entries removed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
    pruned = {}
    for campground, sites in notified_state.items():
        kept = {}
        for site, ts_str in sites.items():
            try:
                ts = datetime.fromisoformat(ts_str)
            except (TypeError, ValueError):
                continue
            if ts > cutoff:
                kept[site] = ts_str
        if kept:
            pruned[campground] = kept
    return pruned

def apply_cooldown(new_full_avail, new_partial_avail, notified_state, cooldown_hours):
    """
    Filters out sites already notified within the cooldown window, so a site
    flickering available/unavailable across consecutive checks doesn't
    trigger a fresh email every cycle.

    Args:
        new_full_avail (dict): {campground_name: [CampsiteName, ...]}
        new_partial_avail (dict): {campground_name: [CampsiteName, ...]}
        notified_state (dict): {campground_name: {CampsiteName: iso_timestamp}},
            already pruned via prune_expired_notifications.
        cooldown_hours (float): Notification cooldown window, in hours.

    Returns:
        tuple: (filtered_full, filtered_partial), same shape as the inputs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)

    def _filter(avail):
        filtered = {}
        for campground, sites in avail.items():
            already_notified = notified_state.get(campground, {})
            kept = []
            for site in sites:
                ts_str = already_notified.get(site)
                if ts_str:
                    try:
                        if datetime.fromisoformat(ts_str) > cutoff:
                            continue  # still in cooldown — suppress the repeat
                    except (TypeError, ValueError):
                        pass
                kept.append(site)
            filtered[campground] = kept
        return filtered

    return _filter(new_full_avail), _filter(new_partial_avail)

def record_notifications(notified_state, full_avail, partial_avail):
    """
    Marks sites as notified now. Call only with sites actually included in a
    sent email — the cooldown clock should start at notification, not at diff.

    Args:
        notified_state (dict): {campground_name: {CampsiteName: iso_timestamp}}
        full_avail (dict): {campground_name: [CampsiteName, ...]}
        partial_avail (dict): {campground_name: [CampsiteName, ...]}

    Returns:
        dict: Updated notified_state.
    """
    now = datetime.now(timezone.utc).isoformat()
    updated = {campground: dict(sites) for campground, sites in notified_state.items()}
    for avail in (full_avail, partial_avail):
        for campground, sites in avail.items():
            for site in sites:
                updated.setdefault(campground, {})[site] = now
    return updated
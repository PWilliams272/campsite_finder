from .recreationgov import get_campground_availability
import pandas as pd

def check_available(params):
    """
    Checks current campsite availability based on given parameters.

    Args:
        params (dict): Must include 'campgrounds', 'start_date', and optionally 'end_date', 'TentsPermitted', 'Partial'.

    Returns:
        pd.DataFrame: DataFrame listing available campsites with relevant columns.
    """
    campgrounds = params.get('campgrounds')
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    df_list = []
    for campground_name, campground_id in campgrounds.items():
        df = get_campground_availability(campground_id, start_date, end_date)
        df = df[df['CampsiteReservable']]
        if params.get('TentsPermitted', True):
            df = df[df['TentsPermitted'] == True]
        if params.get('Partial'):
            df = df[df['Available'].isin(['Available', 'Partial'])]
        else:
            df = df[df['Available'] == 'Available']

        # Add functionality here to allow for additional requirements (e.g., has fire pit, capacity, etc.)
        df['CampgroundName'] = campground_name
        df_list.append(df)
    return pd.concat(df_list)[['CampgroundName', 'CampsiteName', 'CampsiteID', 'Available']]

def check_for_changes(data, old_data):
    """
    Compares new and old availability data and finds newly available and newly partial sites.

    Args:
        data (pd.DataFrame): Current DataFrame of availability.
        old_data (pd.DataFrame): Previous DataFrame of availability.

    Returns:
        tuple: (newly_available, newly_partial), both dicts {campground_name: [CampsiteID, ...]}.
    """
    newly_available = {}
    newly_partial = {}
    for campground_name, new in data.groupby('CampgroundName'):
        prev = old_data[old_data['CampgroundName'] == campground_name]
        newly_available[campground_name] = sorted(list(set(new[new['Available'] == 'Available']['CampsiteID']) - set(prev[prev['Available'] == 'Available']['CampsiteID'])))
        newly_partial[campground_name] = sorted(list(set(new[new['Available'] == 'Partial']['CampsiteID']) - set(prev[prev['Available'] == 'Partial']['CampsiteID'])))
    return newly_available, newly_partial
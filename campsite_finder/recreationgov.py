import os
from datetime import datetime, timedelta
import pandas as pd
import requests

API_KEY = os.environ.get("RECREATION_GOV_API_KEY")
if not API_KEY:
    raise ValueError("RECREATION_GOV_API_KEY environment variable must be set")

BASE_URL = "https://ridb.recreation.gov/api/v1/"
BASE_AVAIL_URL = 'https://www.recreation.gov/api/camps/availability/campground/'

def _format_date(date):
    """
    Converts a datetime or string to a datetime object.

    Args:
        date (str or datetime): Date as a string or datetime object.

    Returns:
        datetime: Converted datetime object.

    Raises:
        ValueError: If the string cannot be parsed.
        TypeError: If input is not str or datetime.
    """
    if isinstance(date, datetime):
        return date
    if isinstance(date, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(date, fmt)
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date string: {date}")
    raise TypeError(f"Date must be str or datetime, got {type(date)}")

def national_park_search(name):
    """
    Searches for national parks by name using the Recreation.gov API.

    Args:
        name (str): Name or partial name of the park.

    Returns:
        pd.DataFrame: DataFrame of matching parks.
    """
    headers = {'apikey': API_KEY}
    params = {'query': name}
    response = requests.get(BASE_URL + 'recareas', params=params, headers=headers)
    results = pd.DataFrame(response.json()['RECDATA'])
    return results

def get_park_campgrounds_from_id(park_id):
    """
    Retrieves all campgrounds for a given park area ID.

    Args:
        park_id (int or str): The park area ID.

    Returns:
        pd.DataFrame: DataFrame of campgrounds and their details.
    """
    headers = {'apikey': API_KEY}
    response = requests.get(BASE_URL + f'recareas/{park_id}/facilities', headers=headers)
    df = pd.DataFrame(response.json()['RECDATA'])
    df = df[df['FacilityTypeDescription'] == 'Campground'].reset_index(drop=True)
    return df[['FacilityName', 'FacilityID', 'FacilityTypeDescription', 'Reservable', 'FacilityLatitude', 'FacilityLongitude']]

def get_campground_data(campground_id):
    """
    Retrieves site data for a campground by its facility ID.

    Args:
        campground_id (int or str): Campground facility ID.

    Returns:
        pd.DataFrame: DataFrame of campsite details.
    """
    headers = {'apikey': API_KEY}
    response = requests.get(BASE_URL + f'facilities/{campground_id}/campsites', headers=headers)
    rows = []
    for site in response.json()['RECDATA']:
        attribut_keys = [
            "Capacity/Size Rating",
            "Location Rating",
            "Picnic Table",
            "Fire Pit",
            "GRILLS",
            "BBQ",
        ]
        attribute_dict = {}
        for attribute in site['ATTRIBUTES']:
            if attribute['AttributeName'] in attribut_keys:
                attribute_dict[attribute['AttributeName']] = attribute['AttributeValue']
        row = {
            'CampsiteName': site.get('CampsiteName'),
            'CampsiteID': site.get('CampsiteID'),
            'CampsiteReservable': site.get('CampsiteReservable'),
            'CampsiteType': site.get('CampsiteType'),
            'CampsiteLatitude': site.get('CampsiteLatitude'),
            'CampsiteLongitude': site.get('CampsiteLongitude'),
            'Loop': site.get('Loop'),
            'TentsPermitted': 'tent' in [equip['EquipmentName'].lower() for equip in site.get('PERMITTEDEQUIPMENT', [])],
            'TypeOfUse': site.get('TypeOfUse'),
        }
        row.update(attribute_dict)
        rows.append(row)
    return pd.DataFrame(rows)

def get_campground_availability(campground_id, start_date, end_date=None):
    """
    Retrieves site availability for a campground during a specified date range.

    Args:
        campground_id (int or str): Campground facility ID.
        start_date (str or datetime): Start date of the search.
        end_date (str or datetime, optional): End date of the search. Defaults to one night.

    Returns:
        pd.DataFrame: DataFrame of campsite availability for the requested dates.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CampFinderBot/1.0)'
    }
    start_date = _format_date(start_date)
    if end_date is None:
        end_date = start_date + timedelta(days=1)
    else:
        end_date = _format_date(end_date)
    n_days = (end_date - start_date).days

    month_starts = []
    cursor = start_date.replace(day=1)
    while cursor < end_date:
        month_starts.append(cursor)
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year+1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month+1)
    
    availability_data = {}
    for month_start in month_starts:
        date_str = f"{month_start.year}-{month_start.month:02d}-01T00%3A00%3A00.000Z"
        full_url = f"{BASE_AVAIL_URL}{campground_id}/month?start_date={date_str}"
        response = requests.get(full_url, headers=headers)
        month_data = response.json()
        for campsite_id, site_data in month_data['campsites'].items():
            if campsite_id not in availability_data:
                availability_data[campsite_id] = site_data
            else:
                availability_data[campsite_id]['availabilities'].update(site_data['availabilities'])

    df = get_campground_data(campground_id).set_index('CampsiteID')

    for campsite_id, site_data in availability_data.items():
        if campsite_id not in df.index:
            continue
        available_days = 0
        for i in range(n_days):
            date = start_date + timedelta(days=i)
            key = f"{date.strftime('%Y-%m-%d')}T00:00:00Z"
            if site_data['availabilities'].get(key) == 'Available':
                available_days += 1
        if available_days == n_days:
            status = "Available"
        elif available_days == 0:
            status = "Unavailable"
        else:
            status = "Partial"
        df.loc[campsite_id, 'Available'] = status
    return df.reset_index()
from .data_io import load_config, save_config

def normalize_config_value(value, existing=None):
    """
    Build a clean, schema-consistent config value from form input, merged
    onto an existing config (for edits) or defaults (for new configs).
    All keys lowercase, campground/park IDs coerced to strings.
    """
    existing = existing or {}
    national_parks = value.get('national_parks', existing.get('national_parks', {}))
    campgrounds = value.get('campgrounds', existing.get('campgrounds', {}))
    return {
        'name': value.get('name', existing.get('name')),
        'start_date': value.get('start_date', existing.get('start_date')),
        'end_date': value.get('end_date', existing.get('end_date')),
        'national_parks': {k: str(v) for k, v in national_parks.items()},
        'campgrounds': {k: str(v) for k, v in campgrounds.items()},
        'email_to': value.get('email_to', existing.get('email_to', [])),
        'partial': value.get('partial', existing.get('partial', False)),
        'tents_permitted': value.get('tents_permitted', existing.get('tents_permitted', False)),
        'active': value.get('active', existing.get('active', True)),
        # Set once at creation from the site's forwarded auth identity, never
        # overwritten on edit — edit access itself is governed by the signed
        # per-config token (see app/access_tokens.py), not by owner_id.
        'owner_id': existing.get('owner_id', value.get('owner_id')),
        # A snapshot of the submitter's username at creation time, purely for
        # display (grouping the admin page by account). Not live — if the
        # account is later renamed, past submissions keep the old name, same
        # as the self-reported 'name' field above.
        'owner_username': existing.get('owner_username', value.get('owner_username')),
    }

def group_campgrounds_by_park(conf):
    """
    Groups a config's campgrounds by which national park they belong to, for
    display. Configs don't store this association directly (campgrounds is a
    flat {name: id} dict), so for the common single-park case it's trivial;
    a multi-park config needs a live RIDB lookup per park to determine
    membership (same call the campground picker itself uses).

    Returns:
        list[tuple[str or None, list[tuple[str, str]]]]: (park_name, [(campground_name, campground_id), ...]),
        park_name is None for campgrounds that couldn't be matched to any
        selected park (e.g. a lookup failure) or when no park is on file.
    """
    parks = conf.get('national_parks') or {}
    campgrounds = list((conf.get('campgrounds') or {}).items())
    if not campgrounds:
        return []
    if len(parks) <= 1:
        label = next(iter(parks), None)
        return [(label, campgrounds)]

    from campsite_finder.recreationgov import get_park_campgrounds_from_id
    groups = []
    assigned_ids = set()
    for park_name, park_id in parks.items():
        try:
            df = get_park_campgrounds_from_id(park_id)
            park_campground_ids = set(df['FacilityID'].astype(str))
        except Exception:
            park_campground_ids = set()
        matched = [(name, cg_id) for name, cg_id in campgrounds if cg_id in park_campground_ids]
        if matched:
            groups.append((park_name, matched))
            assigned_ids.update(cg_id for _, cg_id in matched)

    leftover = [(name, cg_id) for name, cg_id in campgrounds if cg_id not in assigned_ids]
    if leftover:
        groups.append((None, leftover))
    return groups

def read_config(key=None):
    """
    Load the config and optionally return just a specific key.
    """
    config = load_config()
    if key is not None:
        return config.get(key)
    return config

def add_config(key, value):
    """
    Add or update a config key with the given value, and save.
    """
    config = load_config()
    config[key] = value
    save_config(config)

def remove_config(key):
    """
    Remove a key from the config and save.
    """
    config = load_config()
    if key in config:
        del config[key]
        save_config(config)
        return True
    return False

def update_config(updates: dict):
    """
    Update multiple keys in the config and save.
    """
    config = load_config()
    config.update(updates)
    save_config(config)
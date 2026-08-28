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
    }

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
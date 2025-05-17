from .data_io import load_config, save_config

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
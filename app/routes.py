import os
import json
from flask import render_template, request, jsonify, redirect, url_for
from campsite_finder.recreationgov import national_park_search, get_park_campgrounds_from_id
from campsite_finder.data_io import load_config, save_config
from campsite_finder.config_utils import add_config
from . import campsite_bp

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')

@campsite_bp.route('/')
def index():
    return render_template('index.html')

@campsite_bp.route('/api/parks')
def api_parks():
    query = request.args.get('q', '')
    if not query.strip():
        return jsonify([])

    try:
        results = national_park_search(query)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Only return RecAreaID and RecAreaName
    parks = []
    if not results.empty:
        parks = [
            {"id": str(row["RecAreaID"]), "name": row["RecAreaName"]}
            for _, row in results.iterrows()
        ]
    return jsonify(parks)

@campsite_bp.route('/api/campgrounds')
def api_campgrounds():
    park_ids = request.args.getlist('park_ids[]')
    result = {}
    for pid in park_ids:
        try:
            df = get_park_campgrounds_from_id(pid)
        except Exception:
            df = None
        campgrounds = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                campgrounds.append({"id": str(row["FacilityID"]), "name": row["FacilityName"]})
        result[pid] = campgrounds
    return jsonify(result)

@campsite_bp.route('/submit', methods=['POST'])
def submit():
    data = request.json
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "success", "data": data})

@campsite_bp.route('/toggle_setup', methods=['POST'])
def toggle_setup():
    idx = int(request.form.get('idx'))
    setups = load_config()
    setups[idx]['enabled'] = not setups[idx].get('enabled', True)
    save_config(setups)
    return redirect(url_for('campsite_finder.admin'))

@campsite_bp.route('/add_config', methods=['POST'])
def add_config_route():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key or not value:
        return jsonify({"error": "Missing key or value"}), 400
    add_config(key, value)
    return jsonify({"success": True})

@campsite_bp.route("/admin")
def admin():
    from campsite_finder.config_utils import load_config
    configs = load_config()
    return render_template('admin.html', configs=configs)

@campsite_bp.route('/toggle_active/<uuid>', methods=['POST'])
def toggle_active(uuid):
    from campsite_finder.config_utils import load_config, save_config
    configs = load_config()
    is_active = request.json.get('active', True)
    configs[uuid]['active'] = is_active
    save_config(configs)
    return '', 204
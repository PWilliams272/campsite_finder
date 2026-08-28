import os
from flask import render_template, request, jsonify
from campsite_finder.recreationgov import national_park_search, get_park_campgrounds_from_id, get_facility_amenities
from campsite_finder.config_utils import add_config, normalize_config_value
from . import campsite_bp

@campsite_bp.route('/')
def index():
    return render_template('campsite_finder_index.html', admin_page=False)

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
                campgrounds.append({
                    "id": str(row["FacilityID"]),
                    "name": row["FacilityName"],
                    "lat": row["FacilityLatitude"],
                    "lon": row["FacilityLongitude"],
                })
        result[pid] = campgrounds
    return jsonify(result)

@campsite_bp.route('/api/campground_amenities/<facility_id>')
def api_campground_amenities(facility_id):
    try:
        return jsonify(get_facility_amenities(facility_id))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@campsite_bp.route('/add_config', methods=['POST'])
def add_config_route():
    from campsite_finder.notify import format_welcome_email, send_email
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key or not value:
        return jsonify({"error": "Missing key or value"}), 400
    config_value = normalize_config_value(value)
    add_config(key, config_value)
    email_to = config_value.get('email_to')
    if email_to:
        domain = os.environ.get('CAMPSITE_FINDER_DOMAIN', 'localhost')
        edit_url = f"https://{domain}/edit_config/{key}"
        params = dict(config_value)
        params['edit_url'] = edit_url
        subject = "Your Campsite Alert is Set Up!"
        html_body = format_welcome_email(params)
        send_email(subject, html_body, email_to)
    return jsonify({"success": True})

@campsite_bp.route("/admin")
def admin():
    from campsite_finder.config_utils import load_config
    configs = load_config()
    return render_template('admin.html', configs=configs, admin_page=True)

@campsite_bp.route('/toggle_active/<uuid>', methods=['POST'])
def toggle_active(uuid):
    from campsite_finder.config_utils import load_config, save_config
    configs = load_config()
    if uuid not in configs:
        return "Config not found", 404
    configs[uuid]['active'] = request.json.get('active', True)
    save_config(configs)
    return '', 204

@campsite_bp.route('/edit_config/<uuid>', methods=['GET', 'POST'])
def edit_config(uuid):
    from campsite_finder.config_utils import load_config, save_config
    configs = load_config()
    if uuid not in configs:
        return "Config not found", 404
    if request.method == 'POST':
        data = request.json
        value = data.get('value', {})
        configs[uuid] = normalize_config_value(value, existing=configs[uuid])
        save_config(configs)
        return jsonify({'status': 'success'}), 200
    # GET: render form
    config = configs[uuid]
    config_for_form = dict(config)
    config_for_form['campgrounds'] = list(config.get('campgrounds', {}).keys())
    return render_template(
        'campsite_finder_index.html',
        edit_mode=True,
        config=config_for_form,
        uuid=uuid,
        admin_page=False,
    )

@campsite_bp.route('/delete_config/<uuid>', methods=['POST'])
def delete_config(uuid):
    from campsite_finder.config_utils import load_config, save_config
    configs = load_config()
    if uuid in configs:
        del configs[uuid]
        save_config(configs)
        return '', 204
    return "Config not found", 404

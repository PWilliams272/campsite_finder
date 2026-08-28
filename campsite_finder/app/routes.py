from flask import render_template, request, jsonify, abort
from campsite_finder.recreationgov import national_park_search, get_park_campgrounds_from_id, get_facility_amenities
from campsite_finder.config_utils import add_config, normalize_config_value, group_campgrounds_by_park
from campsite_finder.access_tokens import generate_access_token, verify_access_token, build_edit_url, build_quick_disable_url
from . import campsite_bp

def require_access_token(uuid):
    token = request.args.get('token')
    if not verify_access_token(token, uuid):
        abort(403)

def current_user_id():
    """The logged-in user's id, forwarded by nginx from the site's login
    check (X-Auth-User-Id) — empty/absent for anonymous or token-only
    requests (e.g. the emailed edit link, or local dev with no nginx)."""
    return request.headers.get('X-Auth-User-Id') or None

def is_admin():
    return request.headers.get('X-Auth-Role') == 'admin'

@campsite_bp.context_processor
def inject_auth_state():
    # Used by base.html to decide which nav links to show.
    return {'current_user_id': current_user_id(), 'viewer_is_admin': is_admin()}

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
    # Set by nginx from the site's verified login (auth_request_set /
    # X-Auth-User-Id) — this route is only reachable while logged in, so this
    # is always present in production; None locally/without nginx in front.
    value = dict(value)
    value['owner_id'] = request.headers.get('X-Auth-User-Id')
    value['owner_username'] = request.headers.get('X-Auth-Username')
    config_value = normalize_config_value(value)
    add_config(key, config_value)
    email_to = config_value.get('email_to')
    if email_to:
        params = dict(config_value)
        params['edit_url'] = build_edit_url(key)
        params['quick_disable_url'] = build_quick_disable_url(key)
        subject = "Your Campsite Alert is Set Up!"
        html_body = format_welcome_email(params)
        send_email(subject, html_body, email_to)
    return jsonify({"success": True})

@campsite_bp.route("/admin")
def admin():
    from campsite_finder.config_utils import load_config
    configs = load_config()
    edit_tokens = {uuid: generate_access_token(uuid) for uuid in configs}
    campground_groups = {uuid: group_campgrounds_by_park(conf) for uuid, conf in configs.items()}

    # Group by owner_id (the true account identity) rather than the
    # self-typed 'name' field, which isn't guaranteed consistent per person
    # (e.g. a typo on one submission shouldn't split someone into two
    # apparent people).
    by_owner = {}
    for uuid, conf in configs.items():
        by_owner.setdefault(conf.get('owner_id'), []).append((uuid, conf))

    def group_label(owner_id, entries):
        if owner_id is None:
            return 'No account on file'
        username = next((c.get('owner_username') for _, c in entries if c.get('owner_username')), None)
        return username or f'Account #{owner_id}'

    groups = [
        {'label': group_label(owner_id, entries), 'configs': dict(entries)}
        for owner_id, entries in sorted(by_owner.items(), key=lambda kv: (kv[0] is None, kv[0] or ''))
    ]

    return render_template(
        'admin.html',
        groups=groups,
        edit_tokens=edit_tokens,
        campground_groups=campground_groups,
        admin_page=True,
        page_title='All Alerts',
        empty_message='No configurations found.',
        grouped=True,
    )

@campsite_bp.route('/my_alerts')
def my_alerts():
    from campsite_finder.config_utils import load_config
    uid = current_user_id()
    all_configs = load_config()
    # owner_id is stamped from this same header at creation time (see
    # add_config_route) — string-compared since both sides come from the
    # same X-Auth-User-Id header. Configs created before ownership tracking
    # existed (owner_id is None) intentionally never show here — only in
    # the full /admin view.
    configs = {k: v for k, v in all_configs.items() if uid and v.get('owner_id') == uid}
    edit_tokens = {uuid: generate_access_token(uuid) for uuid in configs}
    campground_groups = {uuid: group_campgrounds_by_park(conf) for uuid, conf in configs.items()}
    return render_template(
        'admin.html',
        configs=configs,
        edit_tokens=edit_tokens,
        campground_groups=campground_groups,
        admin_page=False,
        my_alerts_page=True,
        page_title='My Alerts',
        empty_message="You haven't submitted any alerts yet.",
        grouped=False,
    )

@campsite_bp.route('/toggle_active/<uuid>', methods=['POST'])
def toggle_active(uuid):
    from campsite_finder.config_utils import load_config, save_config
    require_access_token(uuid)
    configs = load_config()
    if uuid not in configs:
        return "Config not found", 404
    configs[uuid]['active'] = request.json.get('active', True)
    save_config(configs)
    return '', 204

@campsite_bp.route('/edit_config/<uuid>', methods=['GET', 'POST'])
def edit_config(uuid):
    from campsite_finder.config_utils import load_config, save_config
    require_access_token(uuid)
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
        access_token=request.args.get('token'),
        admin_page=False,
    )

@campsite_bp.route('/quick_disable/<uuid>')
def quick_disable(uuid):
    """One-click unsubscribe from the email footer — a plain GET link, since
    email clients can't fire a POST. Token-gated the same as the other
    per-config actions; idempotent, so a link opened twice is harmless."""
    from campsite_finder.config_utils import load_config, save_config
    require_access_token(uuid)
    configs = load_config()
    if uuid not in configs:
        return "Config not found", 404
    configs[uuid]['active'] = False
    save_config(configs)
    return render_template('quick_disable.html', config=configs[uuid])

@campsite_bp.route('/delete_config/<uuid>', methods=['POST'])
def delete_config(uuid):
    from campsite_finder.config_utils import load_config, save_config
    require_access_token(uuid)
    configs = load_config()
    if uuid in configs:
        del configs[uuid]
        save_config(configs)
        return '', 204
    return "Config not found", 404

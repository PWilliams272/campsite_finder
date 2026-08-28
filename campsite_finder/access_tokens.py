"""
Per-config access tokens: a signed, non-expiring capability token that
grants edit/delete/toggle access to exactly one config, independent of site
login. This is what makes the "manage this alert" link in every email work
for whoever has the link — the original creator or anyone they forward it
to — without an account. It is not tied to owner_id; owner_id is metadata
about who created the alert, the token is what actually authorizes editing
it.
"""
import os
from itsdangerous import URLSafeSerializer, BadSignature
from campsite_finder.settings import get_secret_key

ACCESS_TOKEN_SALT = 'campsite-config-access'

# The domain the standalone campsites viewer is deployed at — edit/manage
# links in emails point directly here (not through the main site's iframe
# wrapper), since /edit_config is a token-gated public path, not a
# login-gated one. Overridable for local/dev via CAMPSITE_FINDER_DOMAIN.
# Importable from both the Flask app (app/routes.py) and the Lambda side
# (main.py, which has no Flask dependency) so both mint identical links.
EDIT_LINK_DOMAIN = os.environ.get('CAMPSITE_FINDER_DOMAIN', 'campsites.peterwilliams.dev')

def generate_access_token(uuid):
    serializer = URLSafeSerializer(get_secret_key(), salt=ACCESS_TOKEN_SALT)
    return serializer.dumps({'uuid': uuid})

def verify_access_token(token, uuid):
    if not token:
        return False
    serializer = URLSafeSerializer(get_secret_key(), salt=ACCESS_TOKEN_SALT)
    try:
        data = serializer.loads(token)
    except BadSignature:
        return False
    return data.get('uuid') == uuid

def build_edit_url(uuid):
    token = generate_access_token(uuid)
    return f"https://{EDIT_LINK_DOMAIN}/edit_config/{uuid}?token={token}"

def build_quick_disable_url(uuid):
    token = generate_access_token(uuid)
    return f"https://{EDIT_LINK_DOMAIN}/quick_disable/{uuid}?token={token}"

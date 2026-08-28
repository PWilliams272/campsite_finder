import os
from .settings import *

# Inline-CSS palette mirrored from app/static/css/tokens.css's light-mode
# values — email clients don't load stylesheets or support CSS variables,
# so this is a hand-kept subset, not a generated sync target.
_BG = "#f6f8f9"
_CARD = "#ffffff"
_BORDER = "#cdd6e0"
_TEXT = "#171d27"
_TEXT_2 = "#57657a"
_PRIMARY = "#1976d2"
_DANGER = "#b8382e"
_RADIUS = "5px"


def _button(url, label, color=_PRIMARY):
    return (
        f'<a href="{url}" style="display:inline-block;margin-top:12px;margin-right:8px;'
        f'padding:10px 18px;background:{color};color:#ffffff;text-decoration:none;'
        f'border-radius:{_RADIUS};font-weight:600;font-size:14px;">{label}</a>'
    )


def _wrap_email(title, body_html, footer_html=""):
    """Wraps body content in a table-based card layout, matching the app's
    look. Table-based since that's what actually renders consistently
    across email clients."""
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:24px 0;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:{_CARD};border:1px solid {_BORDER};border-radius:{_RADIUS};overflow:hidden;">
          <tr><td style="padding:20px 24px;border-bottom:1px solid {_BORDER};">
            <span style="font-size:16px;font-weight:700;color:{_TEXT};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">Campsite Finder</span>
          </td></tr>
          <tr><td style="padding:24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:{_TEXT};font-size:14px;line-height:1.6;">
            <p style="margin:0 0 12px 0;font-size:18px;font-weight:700;">{title}</p>
            {body_html}
          </td></tr>
          {f'<tr><td style="padding:16px 24px;border-top:1px solid {_BORDER};font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:{_TEXT_2};font-size:12px;">{footer_html}</td></tr>' if footer_html else ''}
        </table>
      </td></tr>
    </table>
    """


def format_email(new_full_avail, new_partial_avail, params):
    """
    Create an HTML email summarizing new campsite availabilities.

    Args:
        new_full_avail (dict): {campground_name: [site1, ...]} fully available sites.
        new_partial_avail (dict): {campground_name: [site1, ...]} partially available sites.
        params (dict): Must include 'start_date'.

    Returns:
        str or None: HTML-formatted email body, or None if there are no new availabilities.
    """
    from datetime import datetime, timedelta

    def format_campground_list(names):
        """Helper to create a grammatically correct list from campground names."""
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ', '.join(names[:-1]) + f', and {names[-1]}'

    campgrounds_full = [k for k, v in new_full_avail.items() if v]
    n_full_sites = sum(len(v) for v in new_full_avail.values())

    include_partial = params.get("partial", False)
    if include_partial:
        campgrounds_partial = [k for k, v in new_partial_avail.items() if v]
        n_partial_sites = sum(len(v) for v in new_partial_avail.values())
    else:
        campgrounds_partial = []
        n_partial_sites = 0

    n_sites = n_full_sites + (n_partial_sites if include_partial else 0)

    if n_sites == 0:
        return None

    all_campground_names = set(campgrounds_full) | set(campgrounds_partial)
    campground_str = format_campground_list(sorted(all_campground_names))

    start_date = datetime.strptime(params["start_date"], "%Y-%m-%d")
    end_date = start_date + timedelta(days=1) if params.get("end_date") is None else datetime.strptime(params["end_date"], "%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    if end_date == start_date + timedelta(days=1):
        intro = f"There are {n_sites} new campsites available on {start_date_str} in {campground_str}!"
    else:
        intro = f"There are {n_sites} new campsites available from {start_date_str} to {end_date_str} in {campground_str}!"

    body = f'<p style="margin:0 0 16px 0;">{intro}</p>'

    if n_full_sites:
        body += f'<p style="margin:0 0 4px 0;font-weight:700;color:{_TEXT};">Fully available sites</p>'
        for campground_name, sites in new_full_avail.items():
            if sites:
                site_str = ', '.join(sites)
                body += f'<p style="margin:0 0 4px 0;color:{_TEXT_2};"><strong style="color:{_TEXT};">{campground_name}:</strong> {site_str}</p>'
        body += '<div style="height:12px;"></div>'

    if include_partial and n_partial_sites:
        body += f'<p style="margin:0 0 4px 0;font-weight:700;color:{_TEXT};">Partially available sites (not all requested nights)</p>'
        for campground_name, sites in new_partial_avail.items():
            if sites:
                site_str = ', '.join(sites)
                body += f'<p style="margin:0 0 4px 0;color:{_TEXT_2};"><strong style="color:{_TEXT};">{campground_name}:</strong> {site_str}</p>'
        body += '<div style="height:12px;"></div>'

    buttons = ""
    edit_url = params.get('edit_url')
    if edit_url:
        buttons += _button(edit_url, "Edit or Pause This Alert")
    quick_disable_url = params.get('quick_disable_url')
    if quick_disable_url:
        buttons += _button(quick_disable_url, "Unsubscribe", color=_DANGER)
    if buttons:
        body += f'<div>{buttons}</div>'

    return _wrap_email("New campsites available!", body)

def send_email(subject, html_body, recipients, sender="campsitefinder@peterwilliams.dev"):
    """
    Send an email notification with the given subject and HTML body.

    In local mode, saves the email to a file in the local data directory instead of sending.

    Args:
        subject (str): Email subject line.
        html_body (str): HTML-formatted email body.
        recipients (list): List of recipient email addresses.
        sender (str): Sender email address (default: "pwilliams272@gmail.com").
    """
    if get_mode() == 'local':
        os.makedirs(get_local_data_dir(), exist_ok=True)
        fname = os.path.join(get_local_data_dir(), "email_test.html")
        with open(fname, "w") as f:
            f.write(f"<h2>{subject}</h2>\n{html_body}")
        print(f"[LOCAL MODE] Email would be sent to: {recipients}\nSaved HTML to: {fname}")
    else:
        import boto3
        # Explicit region: SES's client construction requires one (unlike
        # S3's), and the EC2 host's environment doesn't set a default.
        client = boto3.client("ses", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"))
        message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": html_body}}}
        client.send_email(
            Source=sender,
            Destination={"ToAddresses": recipients},
            Message=message
        )

def format_welcome_email(params):
    """
    Create an HTML welcome email for a new configuration.

    Args:
        params (dict): Must include 'name' and 'edit_url'.

    Returns:
        str: HTML-formatted welcome email body.
    """
    name = params.get('name', 'Campsite Finder User')
    edit_url = params.get('edit_url')
    quick_disable_url = params.get('quick_disable_url')

    body = (
        f'<p style="margin:0 0 12px 0;">Hi {name},</p>'
        f'<p style="margin:0 0 12px 0;">Your campsite alert has been set up. We\'ll email you as soon as new '
        f'sites become available that match your criteria.</p>'
        f'<p style="margin:0 0 4px 0;color:{_TEXT_2};">You can edit the dates or campgrounds, or pause this '
        f'alert, any time — no login needed, just use the link below:</p>'
    )
    buttons = ""
    if edit_url:
        buttons += _button(edit_url, "View or Edit This Alert")
    if quick_disable_url:
        buttons += _button(quick_disable_url, "Unsubscribe", color=_DANGER)
    if buttons:
        body += f'<div>{buttons}</div>'

    return _wrap_email("Your campsite alert is set up!", body)
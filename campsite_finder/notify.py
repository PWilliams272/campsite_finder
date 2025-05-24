import os
from .settings import *

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

    include_partial = params.get("Partial", False)
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
        email = f"Exciting news!!! There are {n_sites} new campsites available on {start_date_str} in {campground_str}!<br><br>"
    else:
        email = f"Exciting news!!! There are {n_sites} new campsites available from {start_date_str} to {end_date_str} in {campground_str}!<br><br>"
    
    if n_full_sites:
        email += "<b>Fully available sites:</b><br>"
        for campground_name, sites in new_full_avail.items():
            if sites:
                site_str = ', '.join(sites)
                email += f"{campground_name}: {site_str}<br>"
        email += "<br>"

    if include_partial and n_partial_sites:
        email += "<b>Partially available sites (not all requested nights):</b><br>"
        for campground_name, sites in new_partial_avail.items():
            if sites:
                site_str = ', '.join(sites)
                email += f"{campground_name}: {site_str}<br>"
        email += "<br>"

    # Add edit link if available
    edit_url = params.get('edit_url')
    if edit_url:
        email += f'<a href="{edit_url}" style="display:inline-block;margin-top:10px;padding:8px 16px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px;">Edit or Pause This Alert</a><br>'

    return email

def send_email(subject, html_body, recipients, sender="pwilliams272@gmail.com"):
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
        client = boto3.client("ses")
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
    email = f"""
    <p>Hi {name},</p>
    <p>Your campsite alert has been successfully processed. We'll notify you as soon as new sites become available that match your criteria.</p>
    <p>If you ever want to edit, pause, or delete this alert, just use the link below:</p>
    <a href=\"{edit_url}\" style=\"display:inline-block;margin-top:10px;padding:8px 16px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px;\">Edit or Pause This Alert</a><br>
    <p>Thank you for using Campsite Finder!</p>
    """
    return email
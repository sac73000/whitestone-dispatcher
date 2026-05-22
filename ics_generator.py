from icalendar import Calendar, Event, Alarm, vCalAddress, vText
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from database import get_email_settings
import pytz
import re

CST = pytz.timezone("America/Chicago")


def _make_links_clickable(text):
    return re.sub(
        r'(https?://[^\s<>"\']+)',
        r'<a href="\1">\1</a>',
        text
    )


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_ics(job, method="REQUEST"):
    cal = Calendar()
    cal.add("prodid", "-//WHITE STONE GEOMATICS Crew Scheduler//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", method)

    event = Event()

    title = f"WHITE STONE GEOMATICS FIELD ASSIGNMENT – {job['project_number']} – {job['scope_of_work']}"
    event.add("summary", title)

    date_str = job["scheduled_date"]
    time_str = job["scheduled_start_time"]
    start_dt = CST.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
    duration_hours = float(job.get("estimated_duration", 1.0))
    end_dt = start_dt + timedelta(hours=duration_hours)

    event.add("dtstart", start_dt)
    event.add("dtend", end_dt)
    event.add("dtstamp", datetime.now(pytz.utc))

    event["uid"] = job["uid"]
    event.add("sequence", job.get("sequence", 0))

    settings = get_email_settings()
    organizer_email = (settings or {}).get("email_address", "")
    if organizer_email:
        organizer = vCalAddress(f"mailto:{organizer_email}")
        organizer.params["cn"] = vText("WHITE STONE GEOMATICS Crew Scheduler")
        organizer.params["role"] = vText("CHAIR")
        event.add("organizer", organizer)

    crew_email = job.get("crew_email", "")
    if crew_email:
        attendee = vCalAddress(f"mailto:{crew_email}")
        attendee.params["cn"] = vText(job.get("crew_name", "Crew"))
        attendee.params["role"] = vText("REQ-PARTICIPANT")
        attendee.params["partstat"] = vText("ACCEPTED")
        attendee.params["rsvp"] = vText("FALSE")
        event.add("attendee", attendee)

    maps_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(job['job_address'])}"

    description_parts = [
        f"Job Name: {job['job_name']}",
        f"Project Number: {job['project_number']}",
        f"Address: {job['job_address']}",
        f"Google Maps: {maps_link}",
        f"",
        f"Client Contact: {job.get('client_contact_name', 'N/A')}",
        f"Client Phone: {job.get('client_phone', 'N/A')}",
        f"",
        f"Scope of Work: {job['scope_of_work']}",
        f"Scheduled Time: {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}",
        f"Duration: {duration_hours} hours",
    ]

    if job.get("tools_required"):
        description_parts.append("")
        description_parts.append(f"Tools Required: {job['tools_required']}")

    if job.get("invite_notes"):
        description_parts.append("")
        description_parts.append("Invite Notes:")
        description_parts.append(job["invite_notes"])

    if job.get("notes"):
        description_parts.append("")
        description_parts.append("Notes / Instructions:")
        description_parts.append(job["notes"])

    plain_desc = "\n".join(description_parts)
    event.add("description", plain_desc)

    html_lines = []
    html_lines.append("<html><body>")
    html_lines.append(f"<h2>{_escape_html(title)}</h2>")
    html_lines.append(f"<p><strong>Job Name:</strong> {_escape_html(job['job_name'])}</p>")
    html_lines.append(f"<p><strong>Project Number:</strong> {_escape_html(job['project_number'])}</p>")
    html_lines.append(f"<p><strong>Address:</strong> {_escape_html(job['job_address'])}</p>")
    html_lines.append(f'<p><strong>Google Maps:</strong> <a href="{maps_link}">Open in Google Maps</a></p>')
    html_lines.append(f"<p><strong>Client Contact:</strong> {_escape_html(job.get('client_contact_name', 'N/A'))}</p>")
    html_lines.append(f"<p><strong>Client Phone:</strong> {_escape_html(job.get('client_phone', 'N/A'))}</p>")
    html_lines.append(f"<p><strong>Scope of Work:</strong> {_escape_html(job['scope_of_work'])}</p>")
    html_lines.append(f"<p><strong>Scheduled Time:</strong> {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}</p>")
    html_lines.append(f"<p><strong>Duration:</strong> {duration_hours} hours</p>")

    if job.get("tools_required"):
        html_lines.append(f"<p><strong>Tools Required:</strong> {_escape_html(job['tools_required'])}</p>")

    if job.get("invite_notes"):
        notes_html = _escape_html(job["invite_notes"]).replace("\n", "<br>")
        notes_html = _make_links_clickable(notes_html)
        html_lines.append(f"<p><strong>Invite Notes:</strong><br>{notes_html}</p>")

    if job.get("notes"):
        crew_notes_html = _escape_html(job["notes"]).replace("\n", "<br>")
        crew_notes_html = _make_links_clickable(crew_notes_html)
        html_lines.append(f"<p><strong>Notes / Instructions:</strong><br>{crew_notes_html}</p>")

    html_lines.append("</body></html>")
    html_desc = "\n".join(html_lines)

    event.add("X-ALT-DESC;FMTTYPE=text/html", html_desc)

    event.add("location", job["job_address"])
    event.add("status", "CONFIRMED" if method != "CANCEL" else "CANCELLED")

    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", f"Reminder: {title}")
    alarm.add("trigger", timedelta(minutes=-30))
    event.add_component(alarm)

    alarm2 = Alarm()
    alarm2.add("action", "DISPLAY")
    alarm2.add("description", f"Starting soon: {title}")
    alarm2.add("trigger", timedelta(hours=-1))
    event.add_component(alarm2)

    alarm3 = Alarm()
    alarm3.add("action", "DISPLAY")
    alarm3.add("description", f"Starting in 15 minutes: {title}")
    alarm3.add("trigger", timedelta(minutes=-15))
    event.add_component(alarm3)

    cal.add_component(event)
    return cal.to_ical()


def generate_cancel_ics(job):
    return generate_ics(job, method="CANCEL")


def generate_weekly_ics(jobs, crew_name="Crew", week_start=""):
    cal = Calendar()
    cal.add("prodid", "-//WHITE STONE GEOMATICS Crew Scheduler//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"WHITE STONE GEOMATICS - {crew_name} Week of {week_start}")

    for job in jobs:
        event = Event()
        job_status = job.get("status", "active")
        is_cancelled = job_status in ("cancelled", "deleted")

        if is_cancelled:
            title = f"CANCELLED – {job['project_number']} – {job['scope_of_work']}"
        else:
            title = f"WHITE STONE GEOMATICS – {job['project_number']} – {job['scope_of_work']}"
        event.add("summary", title)

        date_str = job["scheduled_date"]
        time_str = job["scheduled_start_time"]
        start_dt = CST.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
        duration_hours = float(job.get("estimated_duration", 1.0))
        end_dt = start_dt + timedelta(hours=duration_hours)

        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("dtstamp", datetime.now(pytz.utc))

        event["uid"] = job["uid"]
        event.add("sequence", job.get("sequence", 0))

        if is_cancelled:
            event.add("status", "CANCELLED")
            event.add("description", f"This job has been {job_status}.")
            event.add("location", job["job_address"])
            cal.add_component(event)
            continue

        maps_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(job['job_address'])}"

        description_parts = [
            f"Job Name: {job['job_name']}",
            f"Project Number: {job['project_number']}",
            f"Address: {job['job_address']}",
            f"Google Maps: {maps_link}",
            f"",
            f"Client Contact: {job.get('client_contact_name', 'N/A')}",
            f"Client Phone: {job.get('client_phone', 'N/A')}",
            f"",
            f"Scope of Work: {job['scope_of_work']}",
            f"Scheduled Time: {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}",
            f"Duration: {duration_hours} hours",
        ]

        if job.get("tools_required"):
            description_parts.append("")
            description_parts.append(f"Tools Required: {job['tools_required']}")

        if job.get("invite_notes"):
            description_parts.append("")
            description_parts.append("Invite Notes:")
            description_parts.append(job["invite_notes"])

        if job.get("notes"):
            description_parts.append("")
            description_parts.append("Notes / Instructions:")
            description_parts.append(job["notes"])

        plain_desc = "\n".join(description_parts)
        event.add("description", plain_desc)

        html_lines = []
        html_lines.append("<html><body>")
        html_lines.append(f"<h2>{_escape_html(title)}</h2>")
        html_lines.append(f"<p><strong>Job Name:</strong> {_escape_html(job['job_name'])}</p>")
        html_lines.append(f"<p><strong>Project Number:</strong> {_escape_html(job['project_number'])}</p>")
        html_lines.append(f"<p><strong>Address:</strong> {_escape_html(job['job_address'])}</p>")
        html_lines.append(f'<p><strong>Google Maps:</strong> <a href="{maps_link}">Open in Google Maps</a></p>')
        html_lines.append(f"<p><strong>Client Contact:</strong> {_escape_html(job.get('client_contact_name', 'N/A'))}</p>")
        html_lines.append(f"<p><strong>Client Phone:</strong> {_escape_html(job.get('client_phone', 'N/A'))}</p>")
        html_lines.append(f"<p><strong>Scope of Work:</strong> {_escape_html(job['scope_of_work'])}</p>")
        html_lines.append(f"<p><strong>Scheduled Time:</strong> {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}</p>")
        html_lines.append(f"<p><strong>Duration:</strong> {duration_hours} hours</p>")

        if job.get("tools_required"):
            html_lines.append(f"<p><strong>Tools Required:</strong> {_escape_html(job['tools_required'])}</p>")

        if job.get("invite_notes"):
            notes_html = _escape_html(job["invite_notes"]).replace("\n", "<br>")
            notes_html = _make_links_clickable(notes_html)
            html_lines.append(f"<p><strong>Invite Notes:</strong><br>{notes_html}</p>")

        if job.get("notes"):
            crew_notes_html = _escape_html(job["notes"]).replace("\n", "<br>")
            crew_notes_html = _make_links_clickable(crew_notes_html)
            html_lines.append(f"<p><strong>Notes / Instructions:</strong><br>{crew_notes_html}</p>")

        html_lines.append("</body></html>")
        event.add("X-ALT-DESC;FMTTYPE=text/html", "\n".join(html_lines))

        event.add("location", job["job_address"])
        event.add("status", "CONFIRMED")

        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Reminder: {title}")
        alarm.add("trigger", timedelta(minutes=-30))
        event.add_component(alarm)

        alarm2 = Alarm()
        alarm2.add("action", "DISPLAY")
        alarm2.add("description", f"Starting soon: {title}")
        alarm2.add("trigger", timedelta(hours=-1))
        event.add_component(alarm2)

        alarm3 = Alarm()
        alarm3.add("action", "DISPLAY")
        alarm3.add("description", f"Starting in 15 minutes: {title}")
        alarm3.add("trigger", timedelta(minutes=-15))
        event.add_component(alarm3)

        cal.add_component(event)

    return cal.to_ical()

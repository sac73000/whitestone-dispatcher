import os
import base64
import logging
from agentmail import AgentMail
from agentmail.attachments.types.send_attachment import SendAttachment
from ics_generator import generate_ics

logger = logging.getLogger(__name__)

AGENTMAIL_API_KEY = os.environ.get("AGENTMAIL_API_KEY", "")
AGENTMAIL_INBOX_ID = os.environ.get("AGENTMAIL_INBOX", "WSG1").lower() + "@agentmail.to"


def _get_client():
    if not AGENTMAIL_API_KEY:
        raise RuntimeError("AGENTMAIL_API_KEY environment variable is not set.")
    return AgentMail(api_key=AGENTMAIL_API_KEY)


def send_calendar_invite(job, method="REQUEST"):
    recipient = (job.get("crew_email") or "").strip()
    if not recipient or "@" not in recipient:
        return False, f"Invalid crew email address: '{recipient}'"

    try:
        ics_data = generate_ics(job, method)
        ics_bytes = ics_data if isinstance(ics_data, bytes) else ics_data.encode("utf-8")
        ics_b64 = base64.b64encode(ics_bytes).decode("ascii")

        is_update = method == "REQUEST" and job.get("sequence", 0) > 0
        is_cancel = method == "CANCEL"

        if is_cancel:
            subject = f"CANCELLED \u2013 {job['project_number']} \u2013 {job['scope_of_work']}"
        elif is_update:
            subject = f"UPDATED \u2013 {job['project_number']} \u2013 {job['scope_of_work']}"
        else:
            subject = f"WHITE STONE GEOMATICS FIELD ASSIGNMENT \u2013 {job['project_number']} \u2013 {job['scope_of_work']}"

        action_word = "Cancellation" if is_cancel else ("Updated Assignment" if is_update else "Assignment")
        body_text = f"""WHITE STONE GEOMATICS Crew Scheduler \u2013 {action_word}

Job:     {job['job_name']}
Project: {job['project_number']}
Date:    {job['scheduled_date']}
Time:    {job['scheduled_start_time']}
Crew:    {job.get('crew_name', 'N/A')}
Scope:   {job['scope_of_work']}
Address: {job['job_address']}
""".strip()

        if job.get("client_contact_name"):
            body_text += f"\nClient:  {job['client_contact_name']}"
        if job.get("client_phone"):
            body_text += f"\nPhone:   {job['client_phone']}"
        if job.get("notes"):
            body_text += f"\n\nField Notes:\n{job['notes']}"
        if job.get("invite_notes"):
            body_text += f"\n\nAdditional Info:\n{job['invite_notes']}"
        body_text += "\n\nPlease accept the calendar invite attached to this email."

        body_html = f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#1F2937;max-width:600px">
  <div style="background:#1B3A5C;color:white;padding:16px 20px;border-radius:8px 8px 0 0">
    <strong style="font-size:16px">White Stone Geomatics \u2013 {action_word}</strong>
  </div>
  <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-top:none;padding:20px;border-radius:0 0 8px 8px">
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151;white-space:nowrap">Project</td><td style="padding:4px 0">{job['project_number']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Job</td><td>{job['job_name']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Date</td><td>{job['scheduled_date']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Time</td><td>{job['scheduled_start_time']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Scope</td><td>{job['scope_of_work']}</td></tr>
      <tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Address</td><td>{job['job_address']}</td></tr>
      {f'<tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Client</td><td>{job.get("client_contact_name","")}</td></tr>' if job.get("client_contact_name") else ""}
      {f'<tr><td style="padding:4px 12px 4px 0;font-weight:600;color:#374151">Phone</td><td>{job.get("client_phone","")}</td></tr>' if job.get("client_phone") else ""}
    </table>
    {f'<div style="margin-top:16px;padding:12px;background:#FEF9C3;border-radius:6px;font-size:13px"><strong>Field Notes:</strong><br>{job["notes"].replace(chr(10),"<br>")}</div>' if job.get("notes") else ""}
    {f'<div style="margin-top:8px;padding:12px;background:#EFF6FF;border-radius:6px;font-size:13px">{job["invite_notes"].replace(chr(10),"<br>")}</div>' if job.get("invite_notes") else ""}
    <p style="margin-top:16px;color:#6B7280;font-size:13px">A calendar invite (.ics) is attached. Open it to add this job to your calendar.</p>
  </div>
</div>"""

        attachment = SendAttachment(
            filename="invite.ics",
            content_type="text/calendar",
            content=ics_b64,
        )

        client = _get_client()
        inbox_id = AGENTMAIL_INBOX_ID
        logger.info(f"Sending {method} invite from {inbox_id} to {recipient} | Job: {job.get('project_number')}")

        client.inboxes.messages.send(
            inbox_id,
            to=[recipient],
            subject=subject,
            text=body_text,
            html=body_html,
            attachments=[attachment],
        )

        logger.info(f"Invite sent successfully to {recipient}")
        return True, "Calendar invite sent successfully."

    except Exception as e:
        logger.error(f"AgentMail send error: {e}")
        return False, f"Failed to send invite: {str(e)}"


def send_job_invite(job):
    return send_calendar_invite(job, "REQUEST")


def send_job_cancellation(job):
    return send_calendar_invite(job, "CANCEL")


def send_reminder(job):
    return send_calendar_invite(job, "REQUEST")

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import threading
import logging
import os

LOG_FILE = os.environ.get("LOG_FILE", "")
log_handlers = [logging.StreamHandler()]
if LOG_FILE:
    log_handlers.append(logging.FileHandler(LOG_FILE))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "whitestone-crew-scheduler-secret")

_app_ready = False
_db = None
_email = None

def _lazy_init():
    global _app_ready, _db, _email
    if not _app_ready:
        _app_ready = True
        import database as db_module
        import email_sender as email_module
        from scheduler import reminder_scheduler
        _db = db_module
        _email = email_module
        db_module.init_db()
        reminder_scheduler.start()

def _get_db():
    _lazy_init()
    return _db

def _get_email():
    _lazy_init()
    return _email


@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


APP_USERNAME = os.environ.get("APP_USERNAME", "WSE")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "WhiteStoneGeo")


OPEN_ROUTES = {"login", "health", "version", "static"}


@app.before_request
def require_login():
    if request.endpoint in OPEN_ROUTES:
        return None
    if not session.get("logged_in"):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("login"))
    return None


@app.route("/health")
def health():
    return "ok", 200


@app.route("/version")
def version():
    return jsonify({"version": APP_VERSION, "app": "WHITE STONE GEOMATICS Crew Scheduler"})


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == APP_USERNAME and password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
def index():
    _lazy_init()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("index.html", today=today)


@app.route("/api/crews", methods=["GET"])
def api_get_crews():
    return jsonify(_get_db().get_all_crews())


@app.route("/api/crews", methods=["POST"])
def api_add_crew():
    data = request.json
    try:
        _get_db().add_crew(data["name"], data["email"], data.get("color", "#3B82F6"))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/crews/<int:crew_id>", methods=["PUT"])
def api_update_crew(crew_id):
    data = request.json
    _get_db().update_crew(crew_id, data["name"], data["email"], data.get("color", "#3B82F6"))
    return jsonify({"success": True})


@app.route("/api/crews/<int:crew_id>", methods=["DELETE"])
def api_delete_crew(crew_id):
    if _get_db().delete_crew(crew_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Crew has assigned jobs. Reassign or delete jobs first."}), 400


@app.route("/api/jobs/next-project-number")
def api_next_project_number():
    from datetime import datetime as dt
    year = dt.now().year
    db = _get_db()
    next_num = db.get_next_project_number(year)
    return jsonify({"project_number": next_num})


@app.route("/api/dashboard")
def api_dashboard():
    from datetime import datetime as dt, timedelta
    db = _get_db()
    today = dt.now().strftime("%Y-%m-%d")
    week_end = (dt.now() + timedelta(days=6)).strftime("%Y-%m-%d")
    stats = db.get_dashboard_stats(today, week_end)
    return jsonify(stats)


@app.route("/api/leads/export.csv")
def api_export_leads_csv():
    import csv, io
    from flask import Response
    leads = _get_db().get_all_leads("all")
    output = io.StringIO()
    fields = [
        "id", "created_at", "status", "client_name", "client_phone", "client_email",
        "property_owner", "property_address", "county", "property_type", "property_size",
        "property_condition", "survey_types", "scope_of_work", "improvements",
        "terrain", "site_risks", "access_type", "existing_documents", "existing_markers",
        "staking", "disputes", "disputes_details", "deliverables", "coordination",
        "timeline_needed_by", "timeline_type", "referral_source",
        "quote_amount", "quote_date", "quote_notes",
        "lost_reason", "job_id", "key_notes", "description"
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        row = {f: lead.get(f, "") for f in fields}
        if row.get("created_at"):
            row["created_at"] = row["created_at"][:10]
        writer.writerow(row)
    csv_data = output.getvalue()
    from datetime import datetime as dt
    filename = f"leads-export-{dt.now().strftime('%Y%m%d')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/jobs", methods=["GET"])
def api_get_jobs():
    date = request.args.get("date")
    if date:
        return jsonify(_get_db().get_jobs_by_date(date))
    return jsonify(_get_db().get_all_jobs())


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def api_get_job(job_id):
    job = _get_db().get_job_by_id(job_id)
    if job:
        return jsonify(job)
    return jsonify({"error": "Job not found"}), 404


@app.route("/api/jobs/<int:job_id>/download.ics")
def api_download_ics(job_id):
    from flask import Response
    from ics_generator import generate_ics
    job = _get_db().get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    ics_data = generate_ics(job, method="REQUEST")
    return Response(
        ics_data,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=job-{job['project_number']}.ics"}
    )


@app.route("/api/crews/<int:crew_id>/weekly.ics")
def api_crew_weekly_ics(crew_id):
    from flask import Response
    from ics_generator import generate_weekly_ics
    from datetime import timedelta as td
    db = _get_db()
    week_start = request.args.get("week")
    if not week_start:
        d = datetime.now()
        week_start = (d - td(days=d.weekday())).strftime("%Y-%m-%d")
    crew = db.get_crew_by_id(crew_id)
    if not crew:
        return jsonify({"error": "Crew not found"}), 404
    jobs = db.get_crew_jobs_for_week(crew_id, week_start, include_cancelled=True)
    ics_data = generate_weekly_ics(jobs, crew_name=crew["name"], week_start=week_start)
    return Response(
        ics_data,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={crew['name'].replace(' ', '_')}_week_{week_start}.ics"}
    )


def _send_email_background(job, method="invite"):
    try:
        email = _get_email()
        if method == "invite":
            success, msg = email.send_job_invite(job)
        else:
            success, msg = email.send_job_cancellation(job)
        if success:
            logger.info(f"Background email sent for job {job.get('project_number', '?')}: {msg}")
        else:
            logger.error(f"Background email failed for job {job.get('project_number', '?')}: {msg}")
    except Exception as e:
        logger.error(f"Background email error: {e}")


@app.route("/api/jobs", methods=["POST"])
def api_create_job():
    db = _get_db()
    data = request.json
    required = ["job_name", "project_number", "job_address", "crew_id", "scope_of_work", "scheduled_date", "scheduled_start_time"]
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

    job_id = db.create_job(data)
    job = db.get_job_by_id(job_id)

    if data.get("send_invite", True):
        threading.Thread(target=_send_email_background, args=(job,), daemon=True).start()

    return jsonify({"success": True, "job_id": job_id, "email_sent": True, "email_message": "Invite is being sent in the background"})


@app.route("/api/jobs/<int:job_id>", methods=["PUT"])
def api_update_job(job_id):
    db = _get_db()
    data = request.json
    db.update_job(job_id, data)
    job = db.get_job_by_id(job_id)

    if data.get("send_invite", True):
        threading.Thread(target=_send_email_background, args=(job,), daemon=True).start()

    return jsonify({"success": True, "email_sent": True, "email_message": "Invite is being sent in the background"})


@app.route("/api/jobs/<int:job_id>/cancel", methods=["POST"])
def api_cancel_job(job_id):
    db = _get_db()
    job = db.get_job_by_id(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    db.cancel_job(job_id)
    job = db.get_job_by_id(job_id)
    threading.Thread(target=_send_email_background, args=(job, "cancel"), daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    db = _get_db()
    job = db.get_job_by_id(job_id)
    if job:
        _get_email().send_job_cancellation(job)
        db.delete_job(job_id)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Job not found"}), 404


@app.route("/api/send-tomorrow", methods=["POST"])
def api_send_tomorrow():
    db = _get_db()
    email = _get_email()
    jobs = db.get_jobs_for_tomorrow()
    if not jobs:
        return jsonify({"success": False, "message": "No jobs scheduled for tomorrow."})

    results = []
    for job in jobs:
        db.bump_sequence(job["id"])
        job = db.get_job_by_id(job["id"])
        success, msg = email.send_job_invite(job)
        results.append({"job": job["project_number"], "success": success, "message": msg})

    all_ok = all(r["success"] for r in results)
    return jsonify({"success": all_ok, "results": results})


@app.route("/api/send-update/<int:job_id>", methods=["POST"])
def api_send_manual_update(job_id):
    db = _get_db()
    db.bump_sequence(job_id)
    job = db.get_job_by_id(job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404
    success, msg = _get_email().send_job_invite(job)
    return jsonify({"success": success, "message": msg})


@app.route("/api/test-invite", methods=["POST"])
def api_test_invite():
    db = _get_db()
    data = request.json or {}
    to_email = data.get("to_email", "").strip()
    if not to_email or "@" not in to_email:
        return jsonify({"success": False, "message": "Please provide a valid email address."})

    test_job = {
        "uid": db.generate_uid(),
        "job_name": "TEST JOB — Please Ignore",
        "project_number": "WSG-TEST-001",
        "job_address": "123 Test Street, Anytown TX",
        "crew_email": to_email,
        "crew_name": "Test Crew",
        "scope_of_work": "Boundary Survey",
        "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
        "scheduled_start_time": "08:00",
        "estimated_duration": 2.0,
        "client_contact_name": "Test Client",
        "client_phone": "(555) 000-0000",
        "notes": "This is a test invite to verify AgentMail delivery is working.",
        "sequence": 0,
    }
    success, msg = _get_email().send_job_invite(test_job)
    if success:
        return jsonify({"success": True, "message": f"Test invite sent to {to_email}. Check your inbox."})
    return jsonify({"success": success, "message": msg})


# ─── LEAD SOURCES / MARKETING API ────────────────────────────────────────────

@app.route("/api/lead-sources", methods=["GET"])
def api_get_lead_sources():
    return jsonify(_get_db().get_all_lead_sources())


@app.route("/api/lead-sources", methods=["POST"])
def api_create_lead_source():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Source name is required"}), 400
    try:
        source_id = _get_db().create_lead_source(
            name,
            monthly_budget=data.get("monthly_budget", 0),
            color=data.get("color", "#3B82F6"),
        )
        return jsonify({"success": True, "source_id": source_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/lead-sources/<int:source_id>", methods=["PUT"])
def api_update_lead_source(source_id):
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Source name is required"}), 400
    try:
        _get_db().update_lead_source(
            source_id, name,
            monthly_budget=data.get("monthly_budget", 0),
            color=data.get("color", "#3B82F6"),
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/lead-sources/<int:source_id>", methods=["DELETE"])
def api_delete_lead_source(source_id):
    _get_db().delete_lead_source(source_id)
    return jsonify({"success": True})


@app.route("/api/marketing/roi")
def api_marketing_roi():
    return jsonify(_get_db().get_marketing_roi())


# ─── LEADS / INTAKE API ───────────────────────────────────────────────────────

@app.route("/api/leads", methods=["GET"])
def api_get_leads():
    status_filter = request.args.get("status", "all")
    return jsonify(_get_db().get_all_leads(status_filter))


@app.route("/api/leads", methods=["POST"])
def api_create_lead():
    data = request.json
    if not data.get("client_name"):
        return jsonify({"success": False, "error": "Client name is required"}), 400
    lead_id = _get_db().create_lead(data)
    return jsonify({"success": True, "lead_id": lead_id})


@app.route("/api/leads/<int:lead_id>", methods=["GET"])
def api_get_lead(lead_id):
    lead = _get_db().get_lead_by_id(lead_id)
    if lead:
        return jsonify(lead)
    return jsonify({"error": "Lead not found"}), 404


@app.route("/api/leads/<int:lead_id>", methods=["PUT"])
def api_update_lead(lead_id):
    data = request.json
    if not data.get("client_name"):
        return jsonify({"success": False, "error": "Client name is required"}), 400
    _get_db().update_lead(lead_id, data)
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>/quote", methods=["POST"])
def api_record_quote(lead_id):
    data = request.json
    quote_amount = data.get("quote_amount")
    if quote_amount is None:
        return jsonify({"success": False, "error": "Quote amount is required"}), 400
    _get_db().record_lead_quote(
        lead_id,
        float(quote_amount),
        data.get("quote_date", datetime.now().strftime("%Y-%m-%d")),
        data.get("quote_notes", "")
    )
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>/won", methods=["POST"])
def api_mark_lead_won(lead_id):
    data = request.json or {}
    job_id = data.get("job_id")
    _get_db().mark_lead_won(lead_id, job_id=job_id)
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>/lost", methods=["POST"])
def api_mark_lead_lost(lead_id):
    data = request.json or {}
    _get_db().mark_lead_lost(lead_id, data.get("lost_reason", ""))
    return jsonify({"success": True})


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def api_delete_lead(lead_id):
    _get_db().delete_lead(lead_id)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

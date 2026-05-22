# WHITE STONE GEOMATICS Crew Scheduler

## Overview
A web-based dispatcher scheduling application for White Stone Geomatics, a land surveying company. The dispatcher uses this app to assign daily field crew jobs and automatically send calendar invites to crew members via SMTP email.

## Architecture
- **Backend**: Python Flask (port 5000)
- **Database**: PostgreSQL (Replit hosted, via DATABASE_URL) with SQLite fallback for self-hosted
- **Frontend**: Vanilla HTML/CSS/JS (single-page app)

## File Structure
- `main.py` - Flask application with all API routes, login auth, version/health endpoints
- `database.py` - Database models and CRUD operations (PostgreSQL when DATABASE_URL set, SQLite fallback via DB_PATH)
- `ics_generator.py` - ICS calendar invite generation with ORGANIZER/ATTENDEE for calendar compatibility
- `email_sender.py` - AgentMail SDK email sending with ICS calendar invite attachments (base64 encoded)
- `scheduler.py` - Background reminder scheduler (5:30 AM daily reminders)
- `templates/index.html` - Main HTML template
- `templates/login.html` - Login page template
- `static/style.css` - White Stone Geomatics-branded CSS styling
- `static/app.js` - Frontend JavaScript (API calls, UI logic)
- `requirements.txt` - Python dependencies for self-hosted deployment
- `start.sh` - Production startup script (gunicorn)
- `backup_db.sh` - Database backup script
- `DEPLOY.md` - Self-hosted deployment guide for Dell 740XD / whitestoneenv.com
- `whitestone-dispatcher.zip` - Complete deployment package for download

## Key Features
- Job CRUD (create, read, update, delete)
- Crew management with color coding
- Daily calendar schedule view
- Calendar-compatible ICS invites via SMTP with multiple reminder alarms
- Automatic 5:30 AM reminders on job day
- Job cancellation with crew notification
- Tools required tracking per job
- Invite notes support (sent with calendar invites)
- Send Tomorrow's Schedule to all crews
- Manual update sending per job
- Email/SMTP settings panel
- Login authentication (username/password via env vars)
- /health and /version endpoints
- File logging support (LOG_FILE env var)
- Configurable database path (DB_PATH env var)

## Environment Variables
- DATABASE_URL - PostgreSQL connection string (auto-set by Replit; when absent, falls back to SQLite)
- APP_USERNAME / APP_PASSWORD - Login credentials
- SECRET_KEY - Flask session secret
- EMAIL_ADDRESS, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, EMAIL_PASSWORD - Email config
- DB_PATH - SQLite database file location (self-hosted only)
- LOG_FILE - Optional log file path

## Database Tables
- crews, jobs, email_settings (existing)
- leads (new): id, created_at, updated_at, client_name, client_email, client_phone, property_address, county, scope_of_work, description, quote_amount, quote_date, quote_notes, status (intake/quoted/won/lost), lost_reason, job_id

## Recent Changes
- 2026-02-18: Initial build of complete application
- 2026-02-23: Renamed from WHITESTONE to WHITE STONE GEOMATICS; added tools_required, invite_notes, status columns; job cancellation feature; multiple ICS reminder alarms; status badges in All Jobs table
- 2026-02-23: Job deletion changed to soft-delete (status='deleted') so cancelled/deleted jobs appear as CANCELLED events in weekly ICS downloads; weekly ICS now includes cancelled/deleted jobs with STATUS:CANCELLED so calendar apps remove them; sequence numbers bumped on every change for proper calendar updates
- 2026-02-25: Fixed timezone issue - ICS calendar invites now use America/Chicago (Central Time) timezone so events display at correct times; added "Form Survey" to scope of work options; email settings now persist via environment variables for deployment reliability
- 2026-02-26: Added login authentication, /version endpoint, configurable DB path, file logging, requirements.txt, start.sh, backup_db.sh, DEPLOY.md, and deployment zip package for self-hosting on Dell 740XD
- 2026-02-27: Migrated from SQLite to PostgreSQL for Replit deployment (data persists permanently); SQLite kept as fallback for self-hosted deployment on Dell 740XD
- 2026-03-30: Added Intake/Quote workflow — new "Intake" tab with leads table; prospects tracked from first contact through quoting (intake → quoted → won/lost); quote amount recorded; lost reason tracked for marketing; won leads can be scheduled as live jobs; lead→job conversion with pre-filled job form
- 2026-03-30: Added 6 improvements — (1) auto-suggest project number (WS-YYYY-NNNN sequence) when opening job form; (2) Export CSV button for all leads; (3) aging badges on quoted leads (grey/yellow/red by days since quote); (4) Dashboard tab with jobs-today, jobs-next-7-days, pipeline funnel, win-rate cards; (5) Print Sheet button on intake modal opens formatted printout; (6) "View Job" link on won leads jumps to All Jobs tab and highlights the row
- 2026-03-30: Replaced SMTP email delivery with AgentMail.TO SDK — calendar invites now sent from wsg1@agentmail.to; removed Email Settings tab (SMTP config no longer needed); added "Send Test Invite" button on Dashboard tab; ICS attachments sent as base64-encoded SendAttachment objects
- 2026-03-31: Added Marketing & Lead Sources tab — define lead channels (name, monthly budget, color), tag each intake lead with a source; ROI summary table (leads/quoted/won/lost/win rate/revenue won/cost per lead/cost per acquisition); Dashboard ROI charts (revenue by source bar, leads by source doughnut, win rate by source bar) via Chart.js CDN; lead_sources table added to DB; lead_source_id FK added to leads table

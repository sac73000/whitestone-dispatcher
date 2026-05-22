import os
import uuid
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitestone.db"))

USE_POSTGRES = bool(DATABASE_URL)


def get_connection():
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _fetchone(cursor):
    if USE_POSTGRES:
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    else:
        row = cursor.fetchone()
        return dict(row) if row else None


def _fetchall(cursor):
    if USE_POSTGRES:
        rows = cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    else:
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def init_db():
    if USE_POSTGRES:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crews (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#3B82F6'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                uid TEXT NOT NULL UNIQUE,
                job_name TEXT NOT NULL,
                project_number TEXT NOT NULL,
                job_address TEXT NOT NULL,
                crew_id INTEGER NOT NULL REFERENCES crews(id),
                client_contact_name TEXT,
                client_phone TEXT,
                scope_of_work TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                scheduled_start_time TEXT NOT NULL,
                estimated_duration REAL NOT NULL DEFAULT 1.0,
                notes TEXT,
                tools_required TEXT NOT NULL DEFAULT '',
                invite_notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                reminder_sent INTEGER NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email_address TEXT NOT NULL DEFAULT '',
                smtp_server TEXT NOT NULL DEFAULT 'smtp.office365.com',
                smtp_port INTEGER NOT NULL DEFAULT 587,
                email_password TEXT NOT NULL DEFAULT '',
                smtp_username TEXT NOT NULL DEFAULT ''
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM email_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO email_settings (id, email_address, smtp_server, smtp_port, email_password, smtp_username) VALUES (1, '', 'smtp.office365.com', 587, '', '')"
            )
        conn.commit()
        conn.close()
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#3B82F6'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL UNIQUE,
                job_name TEXT NOT NULL,
                project_number TEXT NOT NULL,
                job_address TEXT NOT NULL,
                crew_id INTEGER NOT NULL,
                client_contact_name TEXT,
                client_phone TEXT,
                scope_of_work TEXT NOT NULL,
                scheduled_date TEXT NOT NULL,
                scheduled_start_time TEXT NOT NULL,
                estimated_duration REAL NOT NULL DEFAULT 1.0,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                reminder_sent INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (crew_id) REFERENCES crews(id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN tools_required TEXT NOT NULL DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN invite_notes TEXT NOT NULL DEFAULT ''")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        except:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email_address TEXT NOT NULL DEFAULT '',
                smtp_server TEXT NOT NULL DEFAULT 'smtp.office365.com',
                smtp_port INTEGER NOT NULL DEFAULT 587,
                email_password TEXT NOT NULL DEFAULT ''
            )
        """)
        try:
            cursor.execute("ALTER TABLE email_settings ADD COLUMN smtp_username TEXT NOT NULL DEFAULT ''")
        except:
            pass
        cursor.execute("SELECT COUNT(*) FROM email_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO email_settings (id, email_address, smtp_server, smtp_port, email_password) VALUES (1, '', 'smtp.office365.com', 587, '')"
            )
        cursor.execute("SELECT COUNT(*) FROM crews")
        if cursor.fetchone()[0] == 0:
            default_crews = [
                ("Crew 1", "crew1@example.com", "#3B82F6"),
                ("Crew 2", "crew2@example.com", "#10B981"),
                ("Crew 3", "crew3@example.com", "#F59E0B"),
                ("Crew 4", "crew4@example.com", "#EF4444"),
                ("Crew 5", "crew5@example.com", "#8B5CF6"),
            ]
            cursor.executemany(
                "INSERT INTO crews (name, email, color) VALUES (?, ?, ?)", default_crews
            )
        conn.commit()
        conn.close()


def _placeholder(idx=None):
    if USE_POSTGRES:
        return "%s"
    else:
        return "?"


def generate_uid():
    return str(uuid.uuid4())


def get_all_crews():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crews ORDER BY name")
    result = _fetchall(cursor)
    conn.close()
    return result


def add_crew(name, email, color="#3B82F6"):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"INSERT INTO crews (name, email, color) VALUES ({p}, {p}, {p})", (name, email, color)
    )
    conn.commit()
    conn.close()


def update_crew(crew_id, name, email, color):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"UPDATE crews SET name={p}, email={p}, color={p} WHERE id={p}",
        (name, email, color, crew_id),
    )
    conn.commit()
    conn.close()


def delete_crew(crew_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(f"SELECT COUNT(*) FROM jobs WHERE crew_id={p}", (crew_id,))
    jobs = cursor.fetchone()[0]
    if jobs > 0:
        conn.close()
        return False
    cursor.execute(f"DELETE FROM crews WHERE id={p}", (crew_id,))
    conn.commit()
    conn.close()
    return True


def get_crew_by_id(crew_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(f"SELECT * FROM crews WHERE id={p}", (crew_id,))
    result = _fetchone(cursor)
    conn.close()
    return result


def create_job(data):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    uid = generate_uid()
    p = _placeholder()
    if USE_POSTGRES:
        cursor.execute(
            f"""INSERT INTO jobs (uid, job_name, project_number, job_address, crew_id,
                client_contact_name, client_phone, scope_of_work, scheduled_date,
                scheduled_start_time, estimated_duration, notes, tools_required, invite_notes,
                created_at, updated_at, sequence)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 0) RETURNING id""",
            (
                uid, data["job_name"], data["project_number"], data["job_address"],
                data["crew_id"], data.get("client_contact_name", ""), data.get("client_phone", ""),
                data["scope_of_work"], data["scheduled_date"], data["scheduled_start_time"],
                data.get("estimated_duration", 1.0), data.get("notes", ""),
                data.get("tools_required", ""), data.get("invite_notes", ""), now, now,
            ),
        )
        job_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            f"""INSERT INTO jobs (uid, job_name, project_number, job_address, crew_id,
                client_contact_name, client_phone, scope_of_work, scheduled_date,
                scheduled_start_time, estimated_duration, notes, tools_required, invite_notes,
                created_at, updated_at, sequence)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 0)""",
            (
                uid, data["job_name"], data["project_number"], data["job_address"],
                data["crew_id"], data.get("client_contact_name", ""), data.get("client_phone", ""),
                data["scope_of_work"], data["scheduled_date"], data["scheduled_start_time"],
                data.get("estimated_duration", 1.0), data.get("notes", ""),
                data.get("tools_required", ""), data.get("invite_notes", ""), now, now,
            ),
        )
        job_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id, data):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    p = _placeholder()
    cursor.execute(f"SELECT sequence FROM jobs WHERE id={p}", (job_id,))
    row = cursor.fetchone()
    new_seq = (row[0] if row else 0) + 1
    cursor.execute(
        f"""UPDATE jobs SET job_name={p}, project_number={p}, job_address={p}, crew_id={p},
            client_contact_name={p}, client_phone={p}, scope_of_work={p}, scheduled_date={p},
            scheduled_start_time={p}, estimated_duration={p}, notes={p}, tools_required={p}, invite_notes={p},
            updated_at={p}, sequence={p},
            reminder_sent=0
            WHERE id={p}""",
        (
            data["job_name"], data["project_number"], data["job_address"], data["crew_id"],
            data.get("client_contact_name", ""), data.get("client_phone", ""),
            data["scope_of_work"], data["scheduled_date"], data["scheduled_start_time"],
            data.get("estimated_duration", 1.0), data.get("notes", ""),
            data.get("tools_required", ""), data.get("invite_notes", ""), now, new_seq, job_id,
        ),
    )
    conn.commit()
    conn.close()


def bump_sequence(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"UPDATE jobs SET sequence = sequence + 1, updated_at = {p} WHERE id = {p}",
        (datetime.now().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def delete_job(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    p = _placeholder()
    cursor.execute(
        f"UPDATE jobs SET status='deleted', sequence=sequence+1, updated_at={p} WHERE id={p}",
        (now, job_id),
    )
    conn.commit()
    conn.close()


def get_job_by_id(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"""SELECT j.*, c.name as crew_name, c.email as crew_email, c.color as crew_color
           FROM jobs j JOIN crews c ON j.crew_id = c.id WHERE j.id={p}""",
        (job_id,),
    )
    result = _fetchone(cursor)
    conn.close()
    return result


def cancel_job(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"UPDATE jobs SET status='cancelled', updated_at={p}, sequence=sequence+1 WHERE id={p}",
        (datetime.now().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def get_crew_jobs_for_week(crew_id, week_start, include_cancelled=False):
    from datetime import timedelta
    start = datetime.strptime(week_start, "%Y-%m-%d")
    week_end = (start + timedelta(days=6)).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    if include_cancelled:
        cursor.execute(
            f"""SELECT j.*, c.name as crew_name, c.email as crew_email, c.color as crew_color
               FROM jobs j JOIN crews c ON j.crew_id = c.id
               WHERE j.crew_id={p} AND j.scheduled_date>={p} AND j.scheduled_date<={p}
               ORDER BY j.scheduled_date, j.scheduled_start_time""",
            (crew_id, week_start, week_end),
        )
    else:
        cursor.execute(
            f"""SELECT j.*, c.name as crew_name, c.email as crew_email, c.color as crew_color
               FROM jobs j JOIN crews c ON j.crew_id = c.id
               WHERE j.crew_id={p} AND j.scheduled_date>={p} AND j.scheduled_date<={p} AND j.status='active'
               ORDER BY j.scheduled_date, j.scheduled_start_time""",
            (crew_id, week_start, week_end),
        )
    result = _fetchall(cursor)
    conn.close()
    return result


def get_jobs_by_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"""SELECT j.*, c.name as crew_name, c.email as crew_email, c.color as crew_color
           FROM jobs j JOIN crews c ON j.crew_id = c.id
           WHERE j.scheduled_date={p} AND j.status='active'
           ORDER BY j.scheduled_start_time""",
        (date_str,),
    )
    result = _fetchall(cursor)
    conn.close()
    return result


def get_all_jobs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT j.*, c.name as crew_name, c.email as crew_email, c.color as crew_color
           FROM jobs j JOIN crews c ON j.crew_id = c.id
           WHERE j.status != 'deleted'
           ORDER BY j.scheduled_date, j.scheduled_start_time"""
    )
    result = _fetchall(cursor)
    conn.close()
    return result


def get_jobs_for_tomorrow():
    from datetime import timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return get_jobs_by_date(tomorrow)


def get_email_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_settings WHERE id=1")
    result = _fetchone(cursor)
    conn.close()
    if not result:
        result = {"id": 1, "email_address": "", "smtp_server": "smtp.office365.com", "smtp_port": 587, "email_password": "", "smtp_username": ""}
    env_email = os.environ.get("EMAIL_ADDRESS", "")
    env_smtp_server = os.environ.get("SMTP_SERVER", "")
    env_smtp_port = os.environ.get("SMTP_PORT", "")
    env_smtp_username = os.environ.get("SMTP_USERNAME", "")
    env_email_password = os.environ.get("EMAIL_PASSWORD", "")
    if env_email:
        result["email_address"] = env_email
    if env_smtp_server:
        result["smtp_server"] = env_smtp_server
    if env_smtp_port:
        result["smtp_port"] = int(env_smtp_port)
    if env_smtp_username:
        result["smtp_username"] = env_smtp_username
    if env_email_password:
        result["email_password"] = env_email_password
    return result


def update_email_settings(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(
        f"""UPDATE email_settings SET email_address={p}, smtp_server={p}, smtp_port={p}, email_password={p}, smtp_username={p}
           WHERE id=1""",
        (data["email_address"], data["smtp_server"], data["smtp_port"], data["email_password"], data.get("smtp_username", "")),
    )
    conn.commit()
    conn.close()


def mark_reminder_sent(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()
    cursor.execute(f"UPDATE jobs SET reminder_sent=1 WHERE id={p}", (job_id,))
    conn.commit()
    conn.close()


# ─── LEADS / INTAKE ───────────────────────────────────────────────────────────

def _ensure_lead_sources_table(cursor):
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_sources (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                monthly_budget NUMERIC(10,2) NOT NULL DEFAULT 0,
                color TEXT NOT NULL DEFAULT '#3B82F6',
                created_at TEXT NOT NULL
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lead_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                monthly_budget REAL NOT NULL DEFAULT 0,
                color TEXT NOT NULL DEFAULT '#3B82F6',
                created_at TEXT NOT NULL
            )
        """)


def _ensure_leads_table(cursor):
    _ensure_lead_sources_table(cursor)
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                client_phone TEXT,
                property_address TEXT,
                county TEXT,
                scope_of_work TEXT,
                description TEXT,
                quote_amount NUMERIC(10,2),
                quote_date TEXT,
                quote_notes TEXT,
                status TEXT NOT NULL DEFAULT 'intake',
                lost_reason TEXT,
                job_id INTEGER REFERENCES jobs(id),
                lead_source_id INTEGER REFERENCES lead_sources(id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_source_id INTEGER REFERENCES lead_sources(id)")
        except Exception:
            pass
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_email TEXT,
                client_phone TEXT,
                property_address TEXT,
                county TEXT,
                scope_of_work TEXT,
                description TEXT,
                quote_amount REAL,
                quote_date TEXT,
                quote_notes TEXT,
                status TEXT NOT NULL DEFAULT 'intake',
                lost_reason TEXT,
                job_id INTEGER REFERENCES jobs(id),
                lead_source_id INTEGER REFERENCES lead_sources(id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN lead_source_id INTEGER REFERENCES lead_sources(id)")
        except Exception:
            pass


def get_all_leads(status_filter=None):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    p = _placeholder()
    if status_filter and status_filter != 'all':
        cursor.execute(
            f"SELECT * FROM leads WHERE status={p} ORDER BY created_at DESC",
            (status_filter,)
        )
    else:
        cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
    result = _fetchall(cursor)
    conn.close()
    return result


def get_lead_by_id(lead_id):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    p = _placeholder()
    cursor.execute(f"SELECT * FROM leads WHERE id={p}", (lead_id,))
    result = _fetchone(cursor)
    conn.close()
    return result


def _lead_fields(data):
    return (
        data.get('client_name', ''),
        data.get('client_email', ''),
        data.get('client_phone', ''),
        data.get('caller_name', ''),
        data.get('property_owner', ''),
        data.get('property_address', ''),
        data.get('county', ''),
        data.get('property_size', ''),
        data.get('deadline', ''),
        data.get('key_notes', ''),
        data.get('property_type', ''),
        data.get('survey_purpose', ''),
        data.get('survey_purpose_other', ''),
        data.get('property_condition', ''),
        data.get('improvements', ''),
        data.get('improvements_other', ''),
        data.get('terrain', ''),
        data.get('terrain_details', ''),
        data.get('site_risks', ''),
        data.get('site_risks_other', ''),
        data.get('access_type', ''),
        data.get('existing_documents', ''),
        data.get('existing_markers', ''),
        data.get('survey_types', ''),
        data.get('staking', ''),
        data.get('disputes', ''),
        data.get('disputes_details', ''),
        data.get('timeline_needed_by', ''),
        data.get('timeline_type', ''),
        data.get('timeline_other', ''),
        data.get('deliverables', ''),
        data.get('deliverables_other', ''),
        data.get('coordination', ''),
        data.get('coordination_details', ''),
        data.get('referral_source', ''),
        data.get('referral_source_other', ''),
        data.get('scope_of_work', ''),
        data.get('description', ''),
        data.get('lead_source_id') or None,
    )


_LEAD_INSERT_COLS = """client_name, client_email, client_phone,
    caller_name, property_owner, property_address, county, property_size, deadline, key_notes,
    property_type, survey_purpose, survey_purpose_other, property_condition,
    improvements, improvements_other, terrain, terrain_details,
    site_risks, site_risks_other, access_type,
    existing_documents, existing_markers, survey_types, staking,
    disputes, disputes_details, timeline_needed_by, timeline_type, timeline_other,
    deliverables, deliverables_other, coordination, coordination_details,
    referral_source, referral_source_other, scope_of_work, description, lead_source_id"""


def create_lead(data):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    vals = _lead_fields(data)
    all_vals = (now, now) + vals + ('intake',)
    placeholders = ','.join([p] * len(all_vals))
    if USE_POSTGRES:
        cursor.execute(
            f"""INSERT INTO leads (created_at, updated_at, {_LEAD_INSERT_COLS}, status)
                VALUES ({placeholders}) RETURNING id""",
            all_vals
        )
        lead_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            f"""INSERT INTO leads (created_at, updated_at, {_LEAD_INSERT_COLS}, status)
                VALUES ({placeholders})""",
            all_vals
        )
        lead_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id, data):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    cols = [c.strip() for c in _LEAD_INSERT_COLS.replace('\n', ' ').split(',')]
    set_clause = ', '.join(f"{c}={p}" for c in cols)
    vals = _lead_fields(data)
    cursor.execute(
        f"UPDATE leads SET updated_at={p}, {set_clause} WHERE id={p}",
        (now,) + vals + (lead_id,)
    )
    conn.commit()
    conn.close()


def record_lead_quote(lead_id, quote_amount, quote_date, quote_notes):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    cursor.execute(
        f"""UPDATE leads SET updated_at={p}, quote_amount={p}, quote_date={p},
            quote_notes={p}, status='quoted' WHERE id={p}""",
        (now, quote_amount, quote_date, quote_notes, lead_id)
    )
    conn.commit()
    conn.close()


def mark_lead_won(lead_id, job_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    cursor.execute(
        f"UPDATE leads SET updated_at={p}, status='won', job_id={p} WHERE id={p}",
        (now, job_id, lead_id)
    )
    conn.commit()
    conn.close()


def mark_lead_lost(lead_id, lost_reason=''):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    cursor.execute(
        f"UPDATE leads SET updated_at={p}, status='lost', lost_reason={p} WHERE id={p}",
        (now, lost_reason, lead_id)
    )
    conn.commit()
    conn.close()


def delete_lead(lead_id):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_leads_table(cursor)
    p = _placeholder()
    cursor.execute(f"DELETE FROM leads WHERE id={p}", (lead_id,))
    conn.commit()
    conn.close()


# ─── LEAD SOURCES / MARKETING ─────────────────────────────────────────────────

def get_all_lead_sources():
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_lead_sources_table(cursor)
    cursor.execute("SELECT * FROM lead_sources ORDER BY name")
    result = _fetchall(cursor)
    conn.close()
    return result


def create_lead_source(name, monthly_budget=0, color='#3B82F6'):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_lead_sources_table(cursor)
    now = datetime.now().isoformat()
    p = _placeholder()
    if USE_POSTGRES:
        cursor.execute(
            f"INSERT INTO lead_sources (name, monthly_budget, color, created_at) VALUES ({p},{p},{p},{p}) RETURNING id",
            (name, float(monthly_budget), color, now)
        )
        source_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            f"INSERT INTO lead_sources (name, monthly_budget, color, created_at) VALUES ({p},{p},{p},{p})",
            (name, float(monthly_budget), color, now)
        )
        source_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return source_id


def update_lead_source(source_id, name, monthly_budget=0, color='#3B82F6'):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_lead_sources_table(cursor)
    p = _placeholder()
    cursor.execute(
        f"UPDATE lead_sources SET name={p}, monthly_budget={p}, color={p} WHERE id={p}",
        (name, float(monthly_budget), color, source_id)
    )
    conn.commit()
    conn.close()


def delete_lead_source(source_id):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_lead_sources_table(cursor)
    _ensure_leads_table(cursor)
    p = _placeholder()
    cursor.execute(f"UPDATE leads SET lead_source_id=NULL WHERE lead_source_id={p}", (source_id,))
    cursor.execute(f"DELETE FROM lead_sources WHERE id={p}", (source_id,))
    conn.commit()
    conn.close()


def get_marketing_roi():
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_lead_sources_table(cursor)
    _ensure_leads_table(cursor)

    cursor.execute("""
        SELECT
            ls.id as source_id, ls.name as source_name,
            ls.monthly_budget, ls.color,
            COUNT(l.id) as total_leads,
            COUNT(CASE WHEN l.status IN ('quoted','won','lost') THEN 1 END) as quoted_count,
            COUNT(CASE WHEN l.status = 'won' THEN 1 END) as won_count,
            COUNT(CASE WHEN l.status = 'lost' THEN 1 END) as lost_count,
            COALESCE(SUM(CASE WHEN l.status = 'won' THEN l.quote_amount ELSE 0 END), 0) as total_revenue
        FROM lead_sources ls
        LEFT JOIN leads l ON l.lead_source_id = ls.id
        GROUP BY ls.id, ls.name, ls.monthly_budget, ls.color
        ORDER BY total_revenue DESC, total_leads DESC
    """)
    rows = _fetchall(cursor)

    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN status IN ('quoted','won','lost') THEN 1 END) as quoted,
               COUNT(CASE WHEN status = 'won' THEN 1 END) as won,
               COUNT(CASE WHEN status = 'lost' THEN 1 END) as lost,
               COALESCE(SUM(CASE WHEN status = 'won' THEN quote_amount ELSE 0 END), 0) as revenue
        FROM leads WHERE lead_source_id IS NULL
    """)
    unassigned = _fetchone(cursor)
    conn.close()

    def _enrich(r, won, lost, total, budget, revenue):
        win_rate = round(won / (won + lost) * 100) if (won + lost) > 0 else None
        b = float(budget or 0)
        return {
            **r,
            'win_rate': win_rate,
            'cost_per_lead': round(b / total, 2) if total > 0 and b > 0 else None,
            'cost_per_acq': round(b / won, 2) if won > 0 and b > 0 else None,
            'total_revenue': float(revenue or 0),
            'monthly_budget': float(budget or 0),
        }

    result = []
    for r in rows:
        r = dict(r)
        result.append(_enrich(r, r['won_count'], r['lost_count'], r['total_leads'], r['monthly_budget'], r['total_revenue']))

    if unassigned and unassigned['total'] > 0:
        won = unassigned['won']
        lost = unassigned['lost']
        total = unassigned['total']
        revenue = float(unassigned['revenue'] or 0)
        row = {
            'source_id': None, 'source_name': 'Unassigned',
            'monthly_budget': 0, 'color': '#9CA3AF',
            'total_leads': total, 'quoted_count': unassigned['quoted'],
            'won_count': won, 'lost_count': lost, 'total_revenue': revenue,
        }
        result.append(_enrich(row, won, lost, total, 0, revenue))

    return result


def get_next_project_number(year):
    conn = get_connection()
    cursor = conn.cursor()
    prefix = f"WS-{year}-"
    p = _placeholder()
    cursor.execute(
        f"SELECT project_number FROM jobs WHERE project_number LIKE {p} ORDER BY project_number DESC LIMIT 1",
        (prefix + "%",)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        last = row[0]
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"WS-{year}-{seq:04d}"


def get_dashboard_stats(today, week_end):
    conn = get_connection()
    cursor = conn.cursor()
    p = _placeholder()

    cursor.execute(
        f"SELECT COUNT(*) FROM jobs WHERE scheduled_date={p} AND status='active'", (today,)
    )
    jobs_today = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT COUNT(*) FROM jobs WHERE scheduled_date>={p} AND scheduled_date<={p} AND status='active'",
        (today, week_end)
    )
    jobs_week = cursor.fetchone()[0]

    _ensure_leads_table(cursor)
    cursor.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status")
    rows = _fetchall(cursor)
    lead_counts = {r["status"]: r["cnt"] for r in rows}

    won = lead_counts.get("won", 0)
    lost = lead_counts.get("lost", 0)
    conversion = round(won / (won + lost) * 100) if (won + lost) > 0 else None

    conn.close()
    return {
        "jobs_today": jobs_today,
        "jobs_week": jobs_week,
        "leads_intake": lead_counts.get("intake", 0),
        "leads_quoted": lead_counts.get("quoted", 0),
        "leads_won": won,
        "leads_lost": lost,
        "conversion_rate": conversion,
    }

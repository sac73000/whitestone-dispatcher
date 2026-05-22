# WHITE STONE GEOMATICS Crew Scheduler - Self-Hosted Deployment Guide

## Server Requirements

- Python 3.11 or newer
- Nginx (reverse proxy)
- SQLite3 (usually pre-installed)

## Quick Setup

### 1. Copy Files to Server

Unzip this package to your desired location, for example:
```
C:\apps\dispatcher
```
Or on Linux:
```
/opt/dispatcher
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Set these before starting the app. On Windows, use System Environment Variables or a `.env` file.
On Linux, export them or add to the start script.

**Required:**
| Variable | Default | Description |
|----------|---------|-------------|
| APP_USERNAME | WSE | Login username |
| APP_PASSWORD | WhiteStoneGeo | Login password |
| SECRET_KEY | (auto) | Session encryption key - change this to a random string |

**Email (SMTP):**
| Variable | Default | Description |
|----------|---------|-------------|
| EMAIL_ADDRESS | (none) | Sending email address |
| SMTP_SERVER | smtp.office365.com | SMTP server hostname |
| SMTP_PORT | 587 | SMTP port |
| SMTP_USERNAME | (none) | SMTP login username (if different from email) |
| EMAIL_PASSWORD | (none) | SMTP password |

**Optional:**
| Variable | Default | Description |
|----------|---------|-------------|
| DB_PATH | ./whitestone.db | Path to SQLite database file |
| LOG_FILE | (none) | Path to log file (logs to console if not set) |
| PORT | 5000 | Port the app listens on |
| WORKERS | 2 | Number of gunicorn worker processes |
| HOST | 127.0.0.1 | Bind address |

### 4. Start the Application

**Linux:**
```bash
bash start.sh
```

**Windows (without gunicorn):**
Gunicorn does not run on Windows. Use waitress instead:
```bash
pip install waitress
python -c "from waitress import serve; from main import app; serve(app, host='127.0.0.1', port=5000)"
```

Or install WSL (Windows Subsystem for Linux) and use the Linux instructions.

### 5. Set Up Nginx Reverse Proxy

Example Nginx configuration for whitestoneenv.com:

```nginx
server {
    listen 80;
    server_name whitestoneenv.com www.whitestoneenv.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name whitestoneenv.com www.whitestoneenv.com;

    ssl_certificate /etc/letsencrypt/live/whitestoneenv.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/whitestoneenv.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. SSL Certificate (HTTPS)

Install certbot and get a free Let's Encrypt certificate:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d whitestoneenv.com -d www.whitestoneenv.com
```

## Database Backup

Run the backup script to create a copy of your database:
```bash
bash backup_db.sh
```

This creates timestamped backups in a `backups/` folder and keeps the last 10.

You can schedule this with cron (Linux) or Task Scheduler (Windows):
```
0 2 * * * /opt/dispatcher/backup_db.sh
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| / | Main application (requires login) |
| /login | Login page |
| /logout | Log out |
| /health | Health check (returns "ok") |
| /version | App version info (JSON) |

## Troubleshooting

- **App won't start:** Check Python version (`python --version`) and that all packages installed
- **Can't connect:** Make sure the port isn't blocked by firewall
- **Email not sending:** Verify SMTP settings in the Email Settings panel
- **Database errors:** Check DB_PATH points to a writable location

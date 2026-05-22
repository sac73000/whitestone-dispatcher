import threading
import time
from datetime import datetime
from database import get_jobs_by_date, mark_reminder_sent
from email_sender import send_reminder


class ReminderScheduler:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            try:
                self._check_reminders()
            except Exception as e:
                print(f"Reminder scheduler error: {e}")
            time.sleep(60)

    def _check_reminders(self):
        now = datetime.now()
        if now.hour == 5 and now.minute >= 25 and now.minute <= 35:
            today = now.strftime("%Y-%m-%d")
            jobs = get_jobs_by_date(today)
            for job in jobs:
                if not job.get("reminder_sent"):
                    success, msg = send_reminder(job)
                    if success:
                        mark_reminder_sent(job["id"])
                        print(f"Reminder sent for job {job['project_number']}")
                    else:
                        print(f"Failed to send reminder for {job['project_number']}: {msg}")


reminder_scheduler = ReminderScheduler()

# guardian_rituals.py

import threading
import uuid

RITUAL_JOBS = {}


class RitualJob:
    def __init__(self, target, description, total, **kwargs):
        self.job_id = str(uuid.uuid4())
        self.description = description
        self.state = "running"
        self.current = 0
        self.total = total
        self.error = None
        self.result = None
        self.thread = threading.Thread(target=self._run, args=(target,), kwargs=kwargs)
        RITUAL_JOBS[self.job_id] = self

    def _run(self, target, **kwargs):
        try:
            self.result = target(job=self, **kwargs)
            self.state = "done"
        except Exception as e:
            self.error = str(e)
            self.state = "failed"

    def update(self, step=1, message=None):
        self.current += step

    def done(self):
        self.state = "done"


def start_ritual_job(target, description, total, **kwargs):
    job = RitualJob(target, description, total, **kwargs)
    job.thread.start()
    return job.job_id


# Minimal stub for Notion seed function
def seed_notion_db_with_progress(records, db_id, notion_token, job=None):
    import time

    for i, record in enumerate(records):
        # Simulate a time-consuming step
        time.sleep(0.2)
        if job:
            job.update()
    if job:
        job.done()
    return f"Seeded {len(records)} records to Notion DB {db_id}"

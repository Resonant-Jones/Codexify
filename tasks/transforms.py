# guardian-backend_v2/tasks/transforms.py

from prefect import task

@task
def clean_rows(raw_rows):
    # Simple example: skip header row
    return raw_rows[1:]
from prefect import flow, task

@task(retries=3, retry_delay_seconds=5)
def extract_logs():
    # Imagine this pulls raw logs from your Guardian memory DB
    print("Extracting logs...")
    return ["log1", "log2"]

@task
def transform_logs(logs):
    # Maybe you compress, enrich, or index them
    print(f"Transforming logs: {logs}")
    return [log.upper() for log in logs]

@task
def load_logs(processed_logs):
    # Store back into your Codex or push to a search index
    print(f"Loading logs: {processed_logs}")

@flow
def memory_log_etl_flow():
    logs = extract_logs()
    processed = transform_logs(logs)
    load_logs(processed)

if __name__ == "__main__":
    memory_log_etl_flow()
    
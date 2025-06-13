

# 🩺 health_agent.py
"""
This agent provides a summary of key health metrics such as heart rate, HRV,
sleep hours, etc., potentially pulled from Apple HealthKit or similar APIs.
"""

# TODO: Replace with actual HealthKit API call integration when available
def get_health_summary(timeframe: str = "last_week", metrics: list = None):
    if metrics is None:
        metrics = ["heart_rate", "HRV", "sleep"]

    # Example static values; later pull from HealthKit / local cache
    mock_data = {
        "heart_rate": "Average 78 bpm",
        "HRV": "Average 48 ms",
        "sleep": "Average 6.2 hours/night"
    }

    result = {m: mock_data.get(m, "Data not available") for m in metrics}

    return {
        "status": "ok",
        "summary": result,
        "timeframe": timeframe
    }
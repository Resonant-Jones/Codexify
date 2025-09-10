import time
from concurrent.futures import ThreadPoolExecutor

def mock_fast_agent(*args, **kwargs):
    print("Running mock_fast_agent")
    time.sleep(0.01)
    return {"status": "success", "message": "I finished on time"}

def orchestrate():
    print("Starting orchestrate()...")
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(mock_fast_agent)
        try:
            result = future.result(timeout=1)  # Use a safe timeout for testing
        except Exception as e:
            print(f"Future raised exception: {e}")
            result = {"status": "error", "message": str(e)}
    print(f"Result from future: {result}")
    return result

if __name__ == "__main__":
    final_result = orchestrate()
    print(f"Final orchestrate result: {final_result}")
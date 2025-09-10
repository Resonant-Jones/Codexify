# test_gemini.py

import google.generativeai as genai

def test_gemini_config():
    try:
        print("✅ google.generativeai imported successfully.")
        print(f"Version: {genai.__version__}")
    except Exception as e:
        print("❌ There was a problem importing google.generativeai.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gemini_config()
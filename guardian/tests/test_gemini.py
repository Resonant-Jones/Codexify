# test_gemini.py

import logging

import google.generativeai as genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_gemini_config():
    try:
        logger.info("google.generativeai imported successfully.")
        logger.info("Version: %s", genai.__version__)
    except Exception as e:
        logger.error("There was a problem importing google.generativeai.")
        logger.error("Error: %s", e)


if __name__ == "__main__":
    test_gemini_config()

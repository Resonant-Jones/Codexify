# tests/conftest.py
import os

from dotenv import load_dotenv


def pytest_configure(config):
    # Resolve the full path to the .env file
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)

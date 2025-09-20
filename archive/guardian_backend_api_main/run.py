"""
Run script for Guardian AI Companion
Starts the FastAPI server and initializes all required components
"""

from pathlib import Path

import uvicorn

from guardian.core.db import GuardianDB


def init_application():
    """Initialize application components"""
    # Ensure required directories exist
    Path("actors").mkdir(exist_ok=True)

    # Initialize database
    db = GuardianDB()
    db.init_db()

    print("✨ Guardian AI Companion initialized successfully!")
    print("📝 Database and required directories created")


def main():
    """Main entry point"""
    print("🚀 Starting Guardian AI Companion...")

    # Initialize application
    init_application()

    # Start FastAPI server
    print("🌐 Starting API server at http://localhost:8000")
    uvicorn.run(
        "guardian.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
    )


if __name__ == "__main__":
    main()

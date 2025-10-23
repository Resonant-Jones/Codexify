from setuptools import setup, find_packages

setup(
    name="guardian_codex",
    version="0.1.0",
    description="A modular AI assistant with plugin support and core memory management",
    author="Guardian Core Team",
    packages=find_packages(exclude=["tests*", "docs*"]),
    python_requires=">=3.10",
    install_requires=[
        # Core dependencies
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.0",
        "fastapi>=0.100.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "uvicorn>=0.23.0",
        "sqlalchemy>=2.0.0",
        "aiosqlite>=0.19.0",
        "httpx>=0.24.0",
        "structlog>=21.1.0",  # Added structlog
        
        # Plugin system
        "importlib-metadata>=6.0.0",
        "pluggy>=1.0.0",
        
        # TTS Plugin dependencies
        "requests>=2.31.0",
        "google-cloud-texttospeech>=2.14.1",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",  # For code coverage reports
        ],
    },
    entry_points={
        "console_scripts": [
            "guardian=guardian.cli.plugin_cli:main",
        ],
    },
)
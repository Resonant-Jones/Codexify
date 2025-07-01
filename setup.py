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
        
        # Plugin system
        "importlib-metadata>=6.0.0",
        "pluggy>=1.0.0",
        
        # TTS Plugin dependencies
        "requests>=2.31.0",
        "google-cloud-texttospeech>=2.14.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "mkdocs>=1.4.0",
            "mkdocs-material>=9.1.0",
            "mkdocstrings>=0.22.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "guardian=guardian.cli.plugin_cli:main",
        ],
    },
)

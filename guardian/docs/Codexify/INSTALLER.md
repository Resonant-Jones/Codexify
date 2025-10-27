# Bundled Installer

This project can be distributed as a single installer bundling ThreadSpace and required Ollama models.

## Steps
1. Package the `guardian_codex` application using `python -m build`.
2. Download the necessary Ollama model files.
3. Place the archives and wheel files into an `installer/` directory.
4. Create an installer script that extracts the models and installs the wheel with `pip`.
5. Distribute the installer script along with the packaged assets.

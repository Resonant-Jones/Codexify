# Bundled Installer
> Legacy notice
> This document is retained for historical context and does not describe Codexify's current runtime architecture, supported install path, or present product identity.
> Before using any documentation for architecture or diagram work, read `/docs/architecture/kb-validity-matrix.md`. For current runtime truth, start with `/docs/architecture/README.md` and `/docs/architecture/00-current-state.md`.

This project can be distributed as a single installer bundling Codexify and required Ollama models.

## Steps
1. Package the `guardian_codex` application using `python -m build`.
2. Download the necessary Ollama model files.
3. Place the archives and wheel files into an `installer/` directory.
4. Create an installer script that extracts the models and installs the wheel with `pip`.
5. Distribute the installer script along with the packaged assets.

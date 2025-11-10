import os
import json
from pathlib import Path
from datetime import datetime, timezone

class CodexifyFSManifest:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[2])
        self.tools_dir = self.base_dir / "guardian" / "tools"
        self.skills_dir = self.base_dir / "guardian" / "skills"
        self.sandbox_dir = self.base_dir / "guardian" / "sandbox"
        self.manifest_path = self.base_dir / "manifest.json"

    def _file_metadata(self, file_path: Path):
        rel_path = file_path.relative_to(self.base_dir)
        stat = file_path.stat()
        return {
            "path": str(rel_path),
            "name": file_path.stem,
            "ext": file_path.suffix,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "category": file_path.parent.name
        }

    def scan_dir(self, directory: Path):
        entries = []
        if not directory.exists():
            return entries
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".py", ".json", ".md")):
                    file_path = Path(root) / file
                    entries.append(self._file_metadata(file_path))
        return entries

    def generate_manifest(self):
        tools = self.scan_dir(self.tools_dir)
        skills = self.scan_dir(self.skills_dir)
        sandbox = self.scan_dir(self.sandbox_dir)
        manifest = {
            "mcp_version": "1.2",
            "server_name": "CodexifyFS",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tools": tools,
            "skills": skills,
            "sandbox": sandbox,
        }
        print(f"[CodexifyFS] Indexed {len(tools)} tools, {len(skills)} skills, {len(sandbox)} sandbox entries with metadata.")
        return manifest

    def save_manifest(self):
        manifest = self.generate_manifest()
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"[CodexifyFS] Manifest written to {self.manifest_path}")

def load_manifest():
    return CodexifyFSManifest().generate_manifest()

if __name__ == "__main__":
    manifest = CodexifyFSManifest()
    manifest.save_manifest()

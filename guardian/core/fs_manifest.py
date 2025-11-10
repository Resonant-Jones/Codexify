import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import importlib

class CodexifyFSManifest:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parents[2])
        self.tools_dir = self.base_dir / "guardian" / "tools"
        self.skills_dir = self.base_dir / "guardian" / "skills"
        self.sandbox_dir = self.base_dir / "guardian" / "sandbox"
        self.manifest_path = self.base_dir / "manifest.json"
        self.verified_count = 0

    def _compute_sha256(self, file_path: Path):
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _verify_signature(self, file_path: Path):
        # Look for both .sig and .asc signature files
        sig_file = None
        for ext in [file_path.suffix + ".sig", file_path.suffix + ".asc"]:
            candidate = file_path.with_suffix(ext)
            if candidate.exists():
                sig_file = candidate
                break
        if sig_file is None:
            return {
                "verified": False,
                "signer": None,
                "verified_at": None,
                "method": None,
                "signature_file": None,
            }

        # Check for gpg binary
        try:
            subprocess.run(["gpg", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            gpg_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            gpg_available = False

        if gpg_available:
            try:
                result = subprocess.run(
                    ["gpg", "--verify", str(sig_file), str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                verified = (result.returncode == 0)
                signer = None
                verified_at = datetime.now(timezone.utc).isoformat() if verified else None
                method = "gpg"
                if verified:
                    # Attempt to extract signer from stderr output
                    stderr_output = result.stderr.decode(errors="ignore")
                    for line in stderr_output.splitlines():
                        if line.startswith("gpg: Good signature from"):
                            signer = line.partition("gpg: Good signature from")[2].strip().strip('"')
                            break
                return {
                    "verified": verified,
                    "signer": signer,
                    "verified_at": verified_at,
                    "method": method,
                    "signature_file": str(sig_file.relative_to(self.base_dir)) if sig_file else None,
                }
            except Exception:
                return {
                    "verified": False,
                    "signer": None,
                    "verified_at": None,
                    "method": "gpg",
                    "signature_file": str(sig_file.relative_to(self.base_dir)) if sig_file else None,
                }
        else:
            # fallback to pgpy
            try:
                pgpy = importlib.import_module("pgpy")
                trusted_key_path = self.base_dir / "trusted_pubkey.asc"
                if not trusted_key_path.exists():
                    return {
                        "verified": False,
                        "signer": None,
                        "verified_at": None,
                        "method": "pgpy",
                        "signature_file": str(sig_file.relative_to(self.base_dir)) if sig_file else None,
                    }

                with open(trusted_key_path, "r") as key_file:
                    pubkey_data = key_file.read()
                pubkey, _ = pgpy.PGPKey.from_blob(pubkey_data)

                with open(sig_file, "rb") as sf:
                    signature = pgpy.PGPSignature.from_blob(sf.read())
                with open(file_path, "rb") as ff:
                    file_data = ff.read()

                verified = pubkey.verify(file_data, signature)
                verified_bool = bool(verified)
                verified_at = datetime.now(timezone.utc).isoformat() if verified_bool else None
                signer = pubkey.userids[0].name if verified_bool and pubkey.userids else None

                return {
                    "verified": verified_bool,
                    "signer": signer,
                    "verified_at": verified_at,
                    "method": "pgpy",
                    "signature_file": str(sig_file.relative_to(self.base_dir)) if sig_file else None,
                }
            except Exception:
                return {
                    "verified": False,
                    "signer": None,
                    "verified_at": None,
                    "method": "pgpy",
                    "signature_file": str(sig_file.relative_to(self.base_dir)) if sig_file else None,
                }

    def _file_metadata(self, file_path: Path):
        rel_path = file_path.relative_to(self.base_dir)
        stat = file_path.stat()
        sha_hash = self._compute_sha256(file_path)
        sig_verification = self._verify_signature(file_path)
        provenance = {
            "path": str(rel_path),
            "hash": sha_hash,
            "verified": sig_verification.get("verified", False),
            "signature_file": sig_verification.get("signature_file", None),
        }
        # Add additional provenance fields if verified
        if sig_verification.get("verified", False):
            provenance.update(sig_verification)
            self.verified_count += 1
        else:
            # Also include method, signer, verified_at even if not verified for completeness
            provenance.update({
                "signer": sig_verification.get("signer"),
                "verified_at": sig_verification.get("verified_at"),
                "method": sig_verification.get("method"),
            })

        return {
            "path": str(rel_path),
            "name": file_path.stem,
            "ext": file_path.suffix,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "category": file_path.parent.name,
            "sha256": sha_hash,
            "provenance": provenance
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
        self.verified_count = 0
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
        total_files = len(tools) + len(skills) + len(sandbox)
        print(f"[CodexifyFS] Indexed {len(tools)} tools, {len(skills)} skills, {len(sandbox)} sandbox entries with metadata + provenance.")
        print(f"[CodexifyFS] Verified {self.verified_count} of {total_files} files with signatures.")
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

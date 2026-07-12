#!/usr/bin/env python3
"""Render a manifest-controlled cinematic interpretation of real UI captures."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "Demo-Assets/peekaboo-demo/cinematic-manifest.json"
OUTPUT = ROOT / "Demo-Assets/peekaboo-demo/renders/codexify-peekaboo-cinematic-16x9.mp4"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def render_shot(shot: dict, index: int, temp: Path) -> Path:
    camera = shot["camera"]
    treatment = shot["treatment"]
    frames = shot["durationFrames"]
    seconds = frames / 30
    source = ROOT / "Demo-Assets/peekaboo-demo" / shot["source"]
    output = temp / f"{index:02d}-{shot['id']}.mp4"
    # zoompan is intentionally fed one still frame repeatedly. Every value comes
    # from the manifest; there is no per-render random seed or timeline mutation.
    zoom = f"{camera['startScale']}+({camera['endScale']}-{camera['startScale']})*on/{max(frames - 1, 1)}"
    x = f"iw/2-(iw/zoom/2)+({camera['startX']}+({camera['endX']}-{camera['startX']})*on/{max(frames - 1, 1)})"
    y = f"ih/2-(ih/zoom/2)+({camera['startY']}+({camera['endY']}-{camera['startY']})*on/{max(frames - 1, 1)})"
    filters = [
        "scale=1920:1080:force_original_aspect_ratio=increase",
        "crop=1920:1080",
        f"zoompan=z='min(max({zoom},0.85),1.35)':x='{x}':y='{y}':d=1:s=1920x1080:fps=30",
        f"eq=brightness=-{treatment['backgroundDim']}",
        "format=yuv420p",
    ]
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(source), "-t", f"{seconds:.6f}", "-vf", ",".join(filters), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(output)])
    return output


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    subprocess.run([sys.executable, str(ROOT / "scripts/demo/validate_cinematic_manifest.py"), str(MANIFEST)], cwd=ROOT, check=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codexify-cinematic-") as directory:
        temp = Path(directory)
        segments = [render_shot(shot, index, temp) for index, shot in enumerate(manifest["shots"], 1)]
        concat = temp / "concat.txt"
        concat.write_text("".join(f"file '{path}'\n" for path in segments), encoding="utf-8")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT)])
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

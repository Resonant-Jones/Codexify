#!/usr/bin/env python3
"""Validate the bounded, deterministic cinematic manifest without third-party deps."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SHOT_TYPES = {"WorkspaceReveal", "InterfacePullback", "FocusPush", "MessageIsolation", "SidebarDrift", "ThreadDive", "ContextSwitch", "CardLift", "DocumentUnfold", "GallerySweep", "ArtifactPortal", "ParallaxWorkspace", "GlassRefractionPass", "GeometryMatch", "ColorBridge", "OcclusionWipe", "BreathingHold"}
TRANSITIONS = {"GeometryMatch", "ColorBridge", "OcclusionWipe", "BreathingHold", "ArtifactPortal"}
EASINGS = {"cinematic-soft", "linear", "hold"}


def fail(message: str) -> None:
    raise ValueError(message)


def number(value: object, name: str, low: float, high: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= value <= high:
        fail(f"{name} must be between {low} and {high}")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Demo-Assets/peekaboo-demo/cinematic-manifest.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("fps") != 30 or data.get("width") != 1920 or data.get("height") != 1080:
        fail("manifest must be version 1 at 1920x1080/30fps")
    root = path.parent
    seen: set[str] = set()
    total = 0
    for shot in data.get("shots", []):
        shot_id = shot.get("id")
        if not shot_id or shot_id in seen:
            fail(f"duplicate or missing shot id: {shot_id}")
        seen.add(shot_id)
        if shot.get("type") not in SHOT_TYPES:
            fail(f"unrecognized shot type: {shot.get('type')}")
        source = root / shot["source"]
        if not source.is_file():
            fail(f"missing source: {source}")
        frames = shot.get("durationFrames")
        if not isinstance(frames, int) or frames < 1 or frames > 900:
            fail(f"invalid durationFrames for {shot_id}")
        total += frames
        camera = shot["camera"]
        for key in ("startScale", "endScale"):
            number(camera[key], f"{shot_id}.{key}", 0.85, 1.35)
        for key in ("startX", "endX"):
            number(camera[key], f"{shot_id}.{key}", -240, 240)
        for key in ("startY", "endY"):
            number(camera[key], f"{shot_id}.{key}", -180, 180)
        if camera["easing"] not in EASINGS:
            fail(f"invalid easing for {shot_id}")
        treatment = shot["treatment"]
        number(treatment["backgroundDim"], f"{shot_id}.backgroundDim", 0, 0.35)
        number(treatment["backgroundBlur"], f"{shot_id}.backgroundBlur", 0, 6)
        number(treatment["shadowStrength"], f"{shot_id}.shadowStrength", 0, 0.5)
        transition = shot["transitionOut"]
        if transition["type"] not in TRANSITIONS:
            fail(f"invalid transition for {shot_id}")
        region = shot.get("focusRegion")
        if region:
            number(region["x"], f"{shot_id}.focusRegion.x", 0, 1920)
            number(region["y"], f"{shot_id}.focusRegion.y", 0, 1080)
            number(region["width"], f"{shot_id}.focusRegion.width", 0.0001, 1920)
            number(region["height"], f"{shot_id}.focusRegion.height", 0.0001, 1080)
            if region["x"] + region["width"] > 1920 or region["y"] + region["height"] > 1080:
                fail(f"focusRegion exceeds frame for {shot_id}")
    if not data.get("shots") or total <= 0:
        fail("manifest must contain shots")
    print(f"validated {len(seen)} shots, {total} frames ({total / 30:.2f}s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"manifest invalid: {exc}", file=sys.stderr)
        raise SystemExit(1)

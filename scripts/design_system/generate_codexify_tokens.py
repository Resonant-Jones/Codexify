#!/usr/bin/env python3
"""Generate portable typed adapters. Requires jsonschema (requirements/all.txt).

Only this adapter owns CSS spelling and unit conversion. Token values belong to
codexify.tokens.json. --check is read-only and compares exact UTF-8 bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("design-system/codexify.tokens.json")
SCHEMA = Path("design-system/codexify.tokens.schema.json")
WEB = Path("frontend/src/theme/generated/codexifyTokens.ts")
SWIFT = Path("mobile/scout-ios/Scout/Views/Generated/CodexifyDesignTokens.swift")
GROUPS = ("primitives", "semantic", "components", "experiences")

# Renderer bindings, never a second registry of numeric/color values.
CSS_BINDINGS = {
    "--accent": {"token": "semantic.accent"},
    "--accent-strong": {"token": "semantic.accentStrong"},
    "--bezel": {"token": "semantic.bezel"},
    "--board-edge": {"alias": "--edge-chrome"},
    "--card-pad": {"token": "components.cardPadding"},
    "--card-radius": {"alias": "--radius-tile"},
    "--cfy-session-tab-active-basis": {"token": "components.cfySessionTabActiveBasis"},
    "--cfy-session-tab-inactive-basis": {
        "token": "components.cfySessionTabInactiveBasis"
    },
    "--cfy-transition-rolodex": {"token": "components.cfyTransitionRolodex"},
    "--chip-bg": {"token": "semantic.chipBg"},
    "--chip-border": {"token": "semantic.chipBorder"},
    "--danger-border": {"token": "semantic.dangerBorder"},
    "--danger-surface": {"token": "semantic.dangerSurface"},
    "--danger-text": {"token": "semantic.dangerText"},
    "--dock-border": {"alias": "--frame"},
    "--dock-padding": {"token": "components.dockPadding"},
    "--dock-radius": {"alias": "--radius-tile"},
    "--edge-chrome": {"token": "semantic.edgeChrome"},
    "--frame": {"token": "semantic.frame"},
    "--gutter": {"alias": "--shell-gap"},
    "--icon": {"token": "semantic.icon"},
    "--icon-muted": {"token": "semantic.iconMuted"},
    "--info-surface": {"token": "semantic.infoSurface"},
    "--info-text": {"token": "semantic.infoText"},
    "--muted": {"token": "semantic.muted"},
    "--page-pad": {"token": "semantic.pagePadding"},
    "--panel-bezel": {"token": "semantic.panelBezel"},
    "--panel-bg": {"token": "semantic.panelBg"},
    "--panel-border": {"token": "semantic.panelBorder"},
    "--panel-sheet": {"token": "semantic.panelSheet"},
    "--panel-sheet-border": {"token": "semantic.panelSheetBorder"},
    "--persona-studio-editor-flex": {"token": "components.personaStudioEditorFlex"},
    "--persona-studio-preview-flex": {"token": "components.personaStudioPreviewFlex"},
    "--persona-studio-preview-min": {"token": "components.personaStudioPreviewMin"},
    "--radius": {"alias": "--tile-radius"},
    "--radius-micro": {"token": "semantic.microRadius"},
    "--radius-tile": {"token": "semantic.tileRadius"},
    "--rim": {"alias": "--frame"},
    "--shell-gap": {"token": "semantic.shellGap"},
    "--surface-hover": {"token": "semantic.surfaceHover"},
    "--surface-soft": {"token": "semantic.surfaceSoft"},
    "--tag-surface": {"token": "semantic.tagSurface"},
    "--tag-text": {"token": "semantic.tagText"},
    "--text": {"token": "semantic.text"},
    "--text-on-accent": {"token": "semantic.textOnAccent"},
    "--text-subtle": {"token": "semantic.textSubtle"},
    "--tile-radius": {"alias": "--radius-tile"},
    "--viewport-radius": {"alias": "--radius-tile"},
    "--workspace-w": {"token": "components.workspaceW"},
}


def load_tokens(root: Path = ROOT) -> tuple[dict, dict]:
    source = json.loads((root / SOURCE).read_text())
    schema = json.loads((root / SCHEMA).read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(source)
    registry = {
        f"{group}.{name}": token
        for group in GROUPS
        for name, token in source[group].items()
    }
    resolved = {}

    def resolve(path: str, visiting: tuple = ()) -> dict:
        if path in visiting:
            raise ValueError(f"Token reference cycle: {visiting + (path,)}")
        if path not in registry:
            raise ValueError(f"Unknown token reference: {path}")
        if path in resolved:
            return resolved[path]
        token = registry[path]
        value = token.get("value")
        if "reference" in token:
            target = resolve(token["reference"], visiting + (path,))
            if token["type"] != target["type"]:
                raise ValueError(f"Reference type mismatch: {path}")
            value = target["value"]
        if token["type"] == "boundedDimension" and value["minimum"] > value["maximum"]:
            raise ValueError(f"Inverted dimension bounds: {path}")
        resolved[path] = {"type": token["type"], "value": value}
        return resolved[path]

    for path in registry:
        resolve(path)
    return source, resolved


def number(value: float) -> str:
    return format(value, ".15g")


def css_value(token: dict) -> str:
    kind, value = token["type"], token["value"]
    units = {
        "dimension": "px",
        "textRelativeDimension": "rem",
        "ratio": "fr",
        "duration": "ms",
    }
    if kind in units:
        return number(value) + units[kind]
    if kind == "color":
        channels = [value[k] for k in ("red", "green", "blue")]
        if value["alpha"] == 1:
            return "#" + "".join(f"{int(c):02x}" for c in channels)
        return "rgba(" + ",".join(number(c) for c in channels + [value["alpha"]]) + ")"
    if kind == "boundedDimension":
        return (
            f"clamp({number(value['minimum'])}px, "
            f"{number(value['availableFraction'] * 100)}vw, {number(value['maximum'])}px)"
        )
    raise ValueError(f"No root CSS mapping for {kind}")


def root_css(resolved: dict) -> dict:
    result = {}
    for css, binding in sorted(CSS_BINDINGS.items()):
        if "alias" in binding:
            if binding["alias"] not in CSS_BINDINGS:
                raise ValueError(f"Unknown CSS alias: {css}")
            result[css] = f"var({binding['alias']})"
        else:
            result[css] = css_value(resolved[binding["token"]])
    return result


SWIFT_TYPES = {
    "dimension": "Dimension",
    "textRelativeDimension": "TextRelativeDimension",
    "ratio": "Ratio",
    "duration": "Duration",
    "color": "SRGBColor",
    "boundedDimension": "BoundedDimension",
    "fontFamily": "FontFamily",
    "selectionTreatment": "SelectionTreatment",
    "frameOwnership": "FrameOwnership",
    "navigationIntent": "NavigationIntent",
    "contextIntent": "ContextIntent",
}


def swift_value(token: dict) -> str:
    kind, value = token["type"], token["value"]
    fields = {
        "dimension": "logicalUnits",
        "textRelativeDimension": "textScale",
        "ratio": "weight",
        "duration": "milliseconds",
    }
    if kind in fields:
        return f".init({fields[kind]}: {number(value)})"
    if kind in ("color", "boundedDimension"):
        return ".init(" + ", ".join(f"{k}: {number(v)}" for k, v in value.items()) + ")"
    return "." + value


def render(root: Path = ROOT) -> dict[Path, bytes]:
    source, resolved = load_tokens(root)
    digest = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    header = (
        f"// Generated by scripts/design_system/generate_codexify_tokens.py; DO NOT EDIT.\n"
        f"// Canonical source SHA-256: {digest}\n"
    )
    values = {
        group: {name: resolved[f"{group}.{name}"] for name in sorted(source[group])}
        for group in GROUPS
    }
    web = (
        header
        + "\nexport const codexifyTokens = "
        + json.dumps(values, indent=2)
        + " as const;\n"
        + "\nexport type CodexifyDesignTokens = typeof codexifyTokens;\n"
        + "\n/** Root fallback only. AppShell retains theme and responsive overrides. */\n"
        + "export const codexifyRootCssVars = "
        + json.dumps(root_css(resolved), indent=2)
        + " as const satisfies Readonly<Record<`--${string}`, string>>;\n"
    )
    swift = [
        header,
        "// Values only: native materials, Dynamic Type, safe areas and layout remain renderer-owned.",
        "public enum CodexifyDesignTokens {",
    ]
    structs = {
        "Dimension": ("logicalUnits",),
        "TextRelativeDimension": ("textScale",),
        "Ratio": ("weight",),
        "Duration": ("milliseconds",),
        "SRGBColor": ("red", "green", "blue", "alpha"),
        "BoundedDimension": ("minimum", "availableFraction", "maximum"),
    }
    for name, fields in structs.items():
        swift.append(f"    public struct {name}: Equatable, Sendable {{")
        swift.extend(f"        public let {field}: Double" for field in fields)
        swift.append("    }")
    # Enumerations derive their allowed values from the schema, not a Swift registry.
    schema = json.loads((root / SCHEMA).read_text())
    for variant in schema["$defs"]["token"]["oneOf"]:
        properties = variant["properties"]
        value = properties.get("value", {})
        if "enum" in value:
            name = SWIFT_TYPES[properties["type"]["const"]]
            swift.append(f"    public enum {name}: String, Sendable {{")
            swift.extend(f"        case {case}" for case in value["enum"])
            swift.append("    }")
    for group in GROUPS:
        swift.append(f"    public enum {group.title()} {{")
        for name in sorted(source[group]):
            token = resolved[f"{group}.{name}"]
            swift.append(
                f'        public static let {name}: {SWIFT_TYPES[token["type"]]} = {swift_value(token)}'
            )
        swift.append("    }")
    swift.append("}")
    return {WEB: web.encode(), SWIFT: ("\n".join(swift) + "\n").encode()}


def generate(root: Path = ROOT, *, check: bool = False) -> bool:
    outputs = render(root)  # Validate everything before writing either adapter.
    stale = []
    for relative, content in outputs.items():
        path = root / relative
        if check:
            if not path.exists() or path.read_bytes() != content:
                stale.append(str(relative))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if stale:
        print(
            "Stale generated tokens (run generator):\n" + "\n".join(stale),
            file=sys.stderr,
        )
    return not stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail on missing or altered adapters; never write.",
    )
    args = parser.parse_args()
    try:
        return 0 if generate(check=args.check) else 1
    except (ValueError, KeyError, OSError) as exc:
        print(f"Token generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

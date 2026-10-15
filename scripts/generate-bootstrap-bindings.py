#!/usr/bin/env python3
"""Generate the bounded bootstrap semantic bindings, or fail on drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts/bootstrap/readiness.v1.json"


def render_bindings(contract: dict) -> dict[Path, str]:
    if contract.get("version") != 1:
        raise ValueError("Unsupported bootstrap contract version")
    domains = contract["domains"]
    for name, values in domains.items():
        if not name.isidentifier() or not values:
            raise ValueError("Invalid bootstrap token domain")
        if len(set(values.values())) != len(values):
            raise ValueError(f"Duplicate tokens in {name}")
        for symbol, value in values.items():
            if not symbol.isidentifier() or not value.replace("_", "").isalnum():
                raise ValueError(f"Invalid token in {name}")
    if contract["snapshot"] != {
        "workflow": "BootstrapWorkflow", "core_ready": "boolean",
        "inference_ready": "boolean", "human_action": "BootstrapHumanAction",
    }:
        raise ValueError("Snapshot changes require an explicit generator migration")

    py = [
        '# Generated from contracts/bootstrap/readiness.v1.json. Do not edit.',
        'from __future__ import annotations',
        'from dataclasses import dataclass', 'from enum import Enum', '',
        'BOOTSTRAP_CONTRACT_VERSION = 1', '',
    ]
    ts = [
        '// Generated from contracts/bootstrap/readiness.v1.json. Do not edit.',
        'export const BOOTSTRAP_CONTRACT_VERSION = 1 as const;', '',
    ]
    rs = [
        '// Generated from contracts/bootstrap/readiness.v1.json. Do not edit.',
        'use serde::{Deserialize, Serialize};', '',
        'pub const BOOTSTRAP_CONTRACT_VERSION: u8 = 1;', '',
    ]
    for name, values in domains.items():
        py += [f'class {name}(str, Enum):']
        py += [f'    {symbol} = {json.dumps(value)}' for symbol, value in values.items()]
        py += ['', '']
        ts += [f'export const {name} = {{']
        ts += [f'  {symbol}: {json.dumps(value)},' for symbol, value in values.items()]
        ts += ['} as const;', f'export type {name} = (typeof {name})[keyof typeof {name}];', '']
        rs += ['#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]',
               '#[allow(non_camel_case_types)]', f'pub enum {name} {{']
        for symbol, value in values.items():
            rs += [f'    #[serde(rename = {json.dumps(value)})]', f'    {symbol},']
        rs += ['}', f'impl {name} {{', '    pub fn as_str(self) -> &\'static str {', '        match self {']
        rs += [f'            Self::{symbol} => {json.dumps(value)},' for symbol, value in values.items()]
        rs += ['        }', '    }', '}', '']
    py += [
        '@dataclass(frozen=True)', 'class BootstrapReadiness:',
        '    workflow: BootstrapWorkflow', '    core_ready: bool = False',
        '    inference_ready: bool = False',
        '    human_action: BootstrapHumanAction = BootstrapHumanAction.NONE', '',
        '    def as_dict(self) -> dict:',
        '        return {"version": BOOTSTRAP_CONTRACT_VERSION,',
        '                "workflow": self.workflow.value, "coreReady": self.core_ready,',
        '                "inferenceReady": self.inference_ready,',
        '                "humanAction": self.human_action.value}', '',
    ]
    ts += [
        'export interface BootstrapReadiness {',
        '  version: typeof BOOTSTRAP_CONTRACT_VERSION;',
        '  workflow: BootstrapWorkflow;', '  coreReady: boolean;',
        '  inferenceReady: boolean;', '  humanAction: BootstrapHumanAction;', '}', '',
    ]
    rs += [
        '#[derive(Debug, Clone, Serialize, Deserialize)]', '#[serde(rename_all = "camelCase")]',
        'pub struct BootstrapReadiness {', '    pub version: u8,',
        '    pub workflow: BootstrapWorkflow,', '    pub core_ready: bool,',
        '    pub inference_ready: bool,', '    pub human_action: BootstrapHumanAction,', '}', '',
    ]
    shell = ['# Generated from contracts/bootstrap/readiness.v1.json. Do not edit.',
             'BOOTSTRAP_CONTRACT_VERSION=1']
    for name in ('BootstrapWorkflow', 'BootstrapHumanAction'):
        for symbol, value in domains[name].items():
            shell.append(f'{name}_{symbol}={value}')
    shell.append('')
    return {
        ROOT / 'scripts/bootstrap_readiness.generated.sh': '\n'.join(shell),
        ROOT / 'guardian/ops/bootstrap_readiness_generated.py': '\n'.join(py),
        ROOT / 'frontend/src/contracts/bootstrapReadiness.generated.ts': '\n'.join(ts),
        ROOT / 'src-tauri/src/bootstrap_readiness_generated.rs': '\n'.join(rs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = render_bindings(json.loads(SOURCE.read_text()))
    drift = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                drift.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if drift:
        print('Bootstrap binding drift: ' + ', '.join(drift))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

# Ralph Audit Loop (OpenAI Codex)

This is my Ralph "audit" loop wired up to the **OpenAI Codex CLI**. It runs a long-lived, autonomous, **read-only** code audit: the agent documents problems, but does not modify your repo.

You obviously need to tailor this to your codebase. The included `prd.json` is my example set of audit tasks for a specific stack/project; treat it as a template.

## What’s Different Here (The Codex Part)

People know what a Ralph loop is; the part folks often miss is that you can run the loop with **Codex** and enforce **read-only** execution.

`ralph.sh` does this each iteration:

- It counts as 'Desktop App' usage (2x limits, through April 2nd, as of this writing), by using the variable `export CODEX_INTERNAL_ORIGINATOR_OVERRIDE="Codex Desktop"`
- Picks the next story in `prd.json` where `passes: false`
- Builds a prompt from that story plus `CODEX.md`
- Runs `codex exec` in read-only mode (`-s read-only`)
- (Optional) Enables web research with `--search`
- Captures only the model’s final message via `--output-last-message`
- Writes that markdown into the output file declared in the story acceptance criteria (the line starting with `Created ...`)
- Marks the story passed and moves on

## Prereqs

- `codex` CLI on your PATH and authenticated
- `jq` (the runner uses it to read/update `prd.json`)
- Bash

## How to Run

These files are meant to live at `.codex/ralph-audit/` in your repo (or adjust `REPO_ROOT` in `ralph.sh`).

```bash
cd .codex/ralph-audit
./ralph.sh 20
```

Web research is enabled by default. To disable it:

```bash
./ralph.sh 20 --no-search
```

## Logs / Tailing

- High-level progress: `events.log`
- Full Codex output: `run.log`

```bash
tail -n 200 -f events.log
tail -n 200 -f run.log
```

## Output

Reports land in `audit/*.md` (relative to `.codex/ralph-audit/`). The PRD’s acceptance criteria define the exact output filenames.

## Customize

- Edit `prd.json` to match your repo’s file layout and the audits you care about.
- Edit `CODEX.md` to reflect your quality bar and safety rules.
- Edit the model pin in `ralph.sh` (`REQUESTED_MODEL`, `REASONING_EFFORT`).
- If you’re on Linux, `sed -i ''` (macOS `sed`) will need a small adjustment.

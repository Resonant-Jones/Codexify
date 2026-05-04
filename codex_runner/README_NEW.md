# Campaign Runner - Pi-Powered AI Agent

A simplified, user-friendly campaign runner that uses the **Pi coding agent** as its only backend. All authentication (Claude, Codex, OpenAI, etc.) is handled through Pi's unified interface.

## Quick Start

### 1. Install Dependencies

```bash
cd codex_runner
npm install
```

### 2. Authenticate with Pi

```bash
pi /login
# Follow prompts to authenticate with your preferred provider
```

### 3. Run Your First Command

```bash
# Natural language command
python src/runner_cli.py run "List the files in this project"

# Audit analysis
python src/runner_cli.py audit "Find security vulnerabilities"

# Compile campaigns
python src/runner_cli.py compile "Generate campaigns from findings"
```

## Profile System

Profiles are named configurations that control model, thinking level, passes, etc.

### Default Profiles

| Profile | Model | Thinking | Use Case |
|---------|-------|----------|----------|
| `default` | Sonnet 4 | medium | General use |
| `fast` | Sonnet 4 | low | Quick tasks, 2 passes |
| `thorough` | Opus 4 | high | Deep analysis, 3 passes |
| `review` | Sonnet 4 | medium | Read-only review |

### Profile Commands

```bash
# List all profiles
python src/runner_cli.py profile list

# Show profile details
python src/runner_cli.py profile show fast

# Create custom profile
python src/runner_cli.py profile create my-profile model=opus thinking=high passes=2

# Activate a profile
python src/runner_cli.py profile activate fast

# Delete a profile
python src/runner_cli.py profile delete my-profile
```

## Commands

### Natural Language (`run`)

Execute any command through the agent:

```bash
python src/runner_cli.py run "Fix the bug in src/index.ts"
python src/runner_cli.py run "Refactor the auth module"
python src/runner_cli.py run "Write tests for the API"
```

### Audit (`audit`)

Analyze the repository for issues:

```bash
python src/runner_cli.py audit "Find all security issues"
python src/runner_cli.py --profile thorough audit "Comprehensive code review"
```

### Compile (`compile`)

Generate campaign sets from audit results:

```bash
python src/runner_cli.py compile "Create campaigns from findings"
```

### Profile Management

```bash
# Short form
python src/profile.py list
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--profile <name>` | Use specific profile | active profile |
| `--verbose` | Enable verbose output | false |
| `--cwd <path>` | Working directory | current |
| `--model <id>` | Override model | from profile |
| `--thinking <level>` | Override thinking | from profile |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PI_MODEL` | Model to use | claude-sonnet-4-20250514 |
| `PI_PROVIDER` | Provider to use | anthropic |
| `PI_THINKING` | Thinking level | medium |
| `PI_VERBOSE` | Verbose output | 0 |

## Model Shortcuts

| Shortcut | Full Model ID |
|----------|---------------|
| `sonnet` | claude-sonnet-4-20250514 |
| `opus` | claude-opus-4-5 |
| `haiku` | claude-haiku-4 |

## Files

- `src/agent-wrapper.js` - Pi SDK wrapper
- `src/profile.py` - Profile management
- `src/runner_cli.py` - Main CLI entry point
- `~/.config/campaign_runner/profiles.toml` - Profile storage

## Architecture

```
runner_cli.py (CLI entry)
    ├── profile.py (profile management)
    │   └── profiles.toml (storage)
    └── agent-wrapper.js (Pi SDK wrapper)
            └── @mariozechner/pi-coding-agent (Pi SDK)
                    └── Handles all providers (Claude, Codex, etc.)
```

## Provider Support

Since we use Pi, all providers configured in Pi work automatically:

- **Anthropic**: Claude models
- **OpenAI**: GPT models
- **Google**: Gemini models
- **GitHub Copilot**: Codex
- **And many more via Pi**

Authenticate once with `pi /login` and all providers work.

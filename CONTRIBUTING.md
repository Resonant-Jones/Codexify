# Contributing to Codexify

<div align="center">

*"In collaboration, we forge not just code, but collective intelligence."*

Thank you for considering contributing to Codexify! Whether you're fixing a bug, adding a feature, improving documentation, or enhancing tests, your contribution helps build a more powerful, accessible platform for AI-augmented knowledge work.

</div>

---

## 🌟 Introduction

Codexify is built on the principle of **collaborative intelligence**—the idea that powerful AI systems should be transparent, extensible, and shaped by their community. We welcome contributions from developers of all experience levels who share our vision of:

- **Local-first AI**: Data sovereignty and privacy by design
- **Open Architecture**: Extensible systems that empower customization
- **Rigorous Engineering**: Quality, tested, well-documented code
- **Inclusive Community**: Respectful collaboration and knowledge sharing

By contributing to Codexify, you're not just writing code—you're helping define the future of AI-powered knowledge management.

---

## 📜 Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

**In brief:**
- **Be respectful** of differing viewpoints and experiences
- **Be collaborative** and assume good faith in others
- **Be constructive** in feedback and discussions
- **Be inclusive** and welcoming to all contributors

Unacceptable behavior may be reported to **conduct@catalystlabs.ai**. All reports will be handled with discretion and confidentiality.

---

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have the following installed:

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| **Python** | 3.10, 3.11, or 3.12 | Backend development |
| **Docker** | 20.10+ | Container orchestration |
| **Docker Compose** | v2.0+ | Multi-container management |
| **Node.js** | 20+ | Frontend development |
| **pnpm** | 9+ | Frontend package management |
| **Make** | Any | Convenience commands (optional) |
| **Git** | 2.30+ | Version control |

### Initial Setup

```bash
# 1. Fork the repository on GitHub
# Click "Fork" at https://github.com/Resonant-Jones/Codexify

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/Codexify.git
cd Codexify

# 3. Add upstream remote
git remote add upstream https://github.com/Resonant-Jones/Codexify.git

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env with your API keys (at minimum, set one LLM provider key)
# Required: GROQ_API_KEY or OPENAI_API_KEY
# Optional: ANTHROPIC_API_KEY, GENAI_API_KEY, NOTION_API_KEY
nano .env

# 6. Install Python dependencies
python -m pip install -e .
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt

# 7. Install frontend dependencies
cd frontend/src
pnpm install
cd ../..

# 8. Install pre-commit hooks (IMPORTANT!)
pip install pre-commit
pre-commit install

# 9. Start the development stack
make dev
# Or: docker-compose up -d
```

### Verify Your Setup

```bash
# Check backend health
curl http://localhost:8888/healthz
# Expected: {"ok": true}

# Run quick test suite
pytest -v --maxfail=1 -k "not cli and not net"

# Check frontend
cd frontend/src
pnpm lint
pnpm build

# Verify pre-commit hooks work
git commit --allow-empty -m "test: verify pre-commit"
# Should run Black, Ruff, MyPy, Bandit, etc.
```

If all checks pass, you're ready to contribute! 🎉

---

## 🔄 Development Workflow

### Branch Naming Convention

Use descriptive branch names with one of these prefixes:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New features | `feat/add-redis-caching` |
| `fix/` | Bug fixes | `fix/memory-leak-in-chat-router` |
| `docs/` | Documentation | `docs/update-api-reference` |
| `test/` | Testing improvements | `test/add-e2e-for-connectors` |
| `refactor/` | Code restructuring | `refactor/simplify-plugin-loader` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |
| `perf/` | Performance improvements | `perf/optimize-vector-search` |

**Example:**
```bash
git checkout -b feat/add-webhook-connector
```

### Staying in Sync with Main

Before starting work, always sync with the upstream repository:

```bash
# Fetch latest changes from upstream
git fetch upstream

# Update your local main branch
git checkout main
git merge upstream/main

# Rebase your feature branch on latest main
git checkout feat/your-feature
git rebase main

# If conflicts occur, resolve them, then:
git add .
git rebase --continue
```

### Pull Request Workflow

1. **Create a Draft PR** (optional for work-in-progress):
   ```bash
   git push origin feat/your-feature
   # On GitHub, create PR and mark as "Draft"
   ```

2. **Ensure CI Passes**:
   - All tests must pass (pytest + pnpm test)
   - Linting must pass (Black, Ruff, MyPy, ESLint)
   - Pre-commit hooks must succeed
   - Coverage should not decrease

3. **Request Review**:
   - Mark PR as "Ready for Review"
   - Tag relevant maintainers if needed
   - Respond to feedback promptly

4. **Merge**:
   - PRs are merged via **squash and merge**
   - Ensure final commit message follows [Conventional Commits](#-commit-conventions)
   - Delete branch after merge

### CI Automation

GitHub Actions automatically runs on every push:

- ✅ **Frontend Quality**: Lint, build, and test with pnpm
- ✅ **Backend Tests**: pytest on Python 3.10, 3.11, 3.12
- ✅ **Schema Validation**: Alembic migration checks
- ✅ **Security Scanning**: Bandit for Python security issues

**All checks must pass before merge.**

---

## 🎨 Code Style & Quality

### Line Length

**Unified standard: 88 characters** (Black's default)

This applies to all Python and TypeScript/JavaScript code. We've standardized on 88 to match Black's defaults and modern practices.

### Python Code Style

#### Formatting Tools

| Tool | Purpose | Auto-fix |
|------|---------|----------|
| **Black** | Code formatting | ✅ `make format` |
| **isort** | Import sorting | ✅ `make format` |
| **Ruff** | Fast linting | ⚠️ `make lint-fix` |
| **MyPy** | Type checking | ❌ Manual fixes |
| **Bandit** | Security linting | ❌ Manual review |

#### Run All Checks

```bash
# Format code
make format  # Runs Black + isort

# Lint code
make lint    # Runs Ruff + MyPy

# Combined check (format + lint + test)
make check
```

#### Docstring Convention

Use **Google-style docstrings** for all public functions, classes, and modules:

```python
def create_chat_thread(
    user_id: str,
    title: str,
    project_id: Optional[int] = None
) -> ChatThread:
    """Create a new chat thread for a user.

    Args:
        user_id: Unique identifier for the user.
        title: Display title for the thread.
        project_id: Optional project to associate with thread.

    Returns:
        ChatThread: The newly created thread instance.

    Raises:
        ValueError: If user_id is empty or invalid.
        DatabaseError: If thread creation fails.

    Example:
        >>> thread = create_chat_thread("user_123", "My Chat")
        >>> print(thread.id)
        42
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")

    # Implementation...
```

#### Type Hints

**Type hints are mandatory** for all new functions and methods:

```python
# ✅ Good
def process_messages(
    messages: List[ChatMessage],
    max_tokens: int = 4096
) -> str:
    ...

# ❌ Bad
def process_messages(messages, max_tokens=4096):
    ...
```

Use modern type hint syntax from `typing` module:
- `Optional[T]` for nullable types
- `List[T]`, `Dict[K, V]`, `Set[T]` for collections
- `Union[A, B]` for multiple types
- `Callable[[Args], Return]` for functions

#### Imports

Organize imports in this order (isort handles this automatically):

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from typing import List, Optional

# Third-party
from fastapi import FastAPI, HTTPException
from sqlalchemy import select

# Local
from guardian.core.db import GuardianDB
from guardian.db.models import ChatThread
```

### Frontend Code Style

#### TypeScript/React

- **ESLint** enforces React best practices, accessibility, and TypeScript rules
- **Prettier** handles formatting (integrated with ESLint)
- **Conventional component structure**: Hooks → Effects → Handlers → Render

```typescript
// ✅ Good: Typed props, proper hooks usage
interface ChatMessageProps {
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  content,
  role,
  timestamp
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Side effects here
  }, [content]);

  const handleToggle = () => setIsExpanded(!isExpanded);

  return (
    <div className="chat-message" role="article">
      {/* Render logic */}
    </div>
  );
};
```

#### Run Frontend Checks

```bash
cd frontend/src

# Lint TypeScript/React
pnpm lint

# Type check
pnpm type-check

# Format (if not auto-formatted)
pnpm format
```

### Pre-commit Hooks

Pre-commit hooks **automatically run** when you commit. They check:

1. Trailing whitespace removal
2. End-of-file fixes
3. YAML/JSON validation
4. Large file detection
5. Debug statement detection
6. Private key detection
7. Black formatting
8. isort import sorting
9. Flake8 linting
10. MyPy type checking
11. Bandit security scanning

**If hooks fail, your commit is blocked.** Fix the issues and retry.

To skip hooks (not recommended):
```bash
git commit --no-verify -m "fix: emergency hotfix"
```

---

## 🧪 Testing Guidelines

### Backend Testing

#### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=guardian --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest guardian/tests/test_contracts.py

# Run tests matching pattern
pytest -k "test_chat"

# Stop on first failure
pytest -x

# Run up to N failures
pytest --maxfail=3
```

#### Test Categories

Use markers to organize tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_chat():
    """Test async chat operations."""
    ...

@pytest.mark.net
def test_openai_integration():
    """Test requiring network access."""
    ...

@pytest.mark.slow
def test_full_rag_pipeline():
    """Long-running integration test."""
    ...
```

Run specific categories:
```bash
# Skip slow tests
pytest -m "not slow"

# Run only async tests
pytest -m asyncio

# Run network tests (requires ALLOW_NET_TESTS=1)
ALLOW_NET_TESTS=1 pytest -m net
```

#### Writing Good Tests

**Structure: Arrange-Act-Assert**

```python
def test_create_chat_thread():
    # Arrange: Set up test data
    db = GuardianDB(TEST_DATABASE_URL)
    user_id = "test_user_123"
    title = "Test Chat"

    # Act: Execute the function
    thread = db.create_chat_thread(user_id=user_id, title=title)

    # Assert: Verify expected behavior
    assert thread.id is not None
    assert thread.user_id == user_id
    assert thread.title == title
    assert thread.created_at is not None
```

**Use fixtures for common setup:**

```python
@pytest.fixture
def db():
    """Provide test database instance."""
    db = GuardianDB(TEST_DATABASE_URL)
    yield db
    db.close()

def test_with_fixture(db):
    """Test using the db fixture."""
    thread = db.create_chat_thread("user", "title")
    assert thread.id is not None
```

### Frontend Testing

```bash
cd frontend/src

# Run unit tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run E2E tests (Cypress)
pnpm test:e2e

# Run E2E in headless mode (CI)
pnpm test:e2e:ci
```

#### Frontend Test Structure

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage', () => {
  it('renders message content', () => {
    render(
      <ChatMessage
        content="Hello world"
        role="user"
        timestamp={new Date()}
      />
    );

    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('toggles expanded state on click', () => {
    render(
      <ChatMessage
        content="Long message..."
        role="assistant"
        timestamp={new Date()}
      />
    );

    const toggle = screen.getByRole('button', { name: /expand/i });
    fireEvent.click(toggle);

    expect(screen.getByRole('article')).toHaveClass('expanded');
  });
});
```

### Coverage Requirements

**Minimum coverage: 80%** (line coverage)

- New code should have **>90% coverage** when possible
- Critical paths (auth, data access, API routes) should have **100% coverage**
- Tests should cover edge cases, error conditions, and happy paths

Check coverage locally:
```bash
# Backend
pytest --cov=guardian --cov-report=term-missing
# Look for "TOTAL" line at bottom

# Frontend
pnpm test:coverage
# Open coverage/index.html
```

---

## 📝 Commit Conventions

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) for clear, semantic commit history.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(chat): add stream message buffering` |
| `fix` | Bug fix | `fix(memory): resolve race condition in consolidation` |
| `docs` | Documentation only | `docs(api): update embeddings endpoint examples` |
| `test` | Adding/updating tests | `test(connectors): add GitHub integration tests` |
| `refactor` | Code change without behavior change | `refactor(db): simplify session management` |
| `perf` | Performance improvement | `perf(vector): optimize FAISS index queries` |
| `chore` | Maintenance tasks | `chore(deps): update FastAPI to 0.110.0` |
| `style` | Formatting, whitespace | `style: apply Black formatting to core module` |
| `ci` | CI/CD changes | `ci: add coverage reporting to workflow` |
| `build` | Build system changes | `build(docker): optimize multi-stage build` |
| `revert` | Revert previous commit | `revert: rollback commit abc123` |

### Scopes

Common scopes (use relevant module):

- `chat` - Chat thread/message functionality
- `memory` - Memory system
- `rag` - RAG engine
- `api` - API routes
- `db` - Database layer
- `plugins` - Plugin system
- `connectors` - External integrations
- `ui` - Frontend components
- `auth` - Authentication/authorization
- `docs` - Documentation

### Examples

**Simple commit:**
```bash
git commit -m "feat(memory): add auto-consolidation scheduler"
```

**Detailed commit with body:**
```bash
git commit -m "fix(chat): resolve token overflow in context window

The previous implementation didn't account for system prompt tokens
when calculating context window usage, causing truncation errors.

This fix:
- Adds system prompt to token count
- Implements sliding window for long conversations
- Adds test coverage for edge cases

Closes #234"
```

**Breaking change:**
```bash
git commit -m "feat(api)!: redesign embeddings endpoint

BREAKING CHANGE: The /embeddings endpoint now returns normalized
vectors by default. Use ?normalize=false to get raw embeddings.

Migration guide: https://docs.codexify.io/migration/v2"
```

### Commit Message Rules

✅ **DO:**
- Use imperative mood ("add" not "added" or "adds")
- Keep subject line under 72 characters
- Capitalize subject line
- Don't end subject with period
- Separate subject from body with blank line
- Wrap body at 72 characters
- Explain *what* and *why*, not *how*

❌ **DON'T:**
- Use vague messages like "fix stuff" or "update"
- Include multiple unrelated changes in one commit
- Mix formatting changes with logic changes
- Commit broken/untested code

---

## 🔀 Pull Request Guidelines

### Before Opening a PR

- [ ] **Tests pass locally**: `pytest && pnpm test`
- [ ] **Linting passes**: `make lint`
- [ ] **Code is formatted**: `make format`
- [ ] **Coverage maintained/improved**: Check coverage reports
- [ ] **Documentation updated**: If API/behavior changed
- [ ] **Commit messages follow conventions**: Conventional Commits format
- [ ] **Branch is up to date**: Rebased on latest `main`

### PR Title

Use the same format as commit messages:

```
feat(chat): add stream message buffering
```

### PR Description Template

```markdown
## Description
Brief summary of what this PR does.

## Motivation
Why is this change needed? What problem does it solve?

## Changes
- Bullet list of key changes
- Include any breaking changes
- Note any new dependencies

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] Coverage: XX% → YY%

## Screenshots (if UI changes)
![Before](url) ![After](url)

## Related Issues
Closes #123
Relates to #456

## Checklist
- [ ] Documentation updated
- [ ] CHANGELOG updated (if applicable)
- [ ] Breaking changes documented
- [ ] Tests pass locally
- [ ] Linting passes
```

### PR Size Guidelines

**Keep PRs focused and small:**

- ✅ **Ideal**: <200 lines changed
- ⚠️ **Acceptable**: 200-500 lines
- ❌ **Too large**: >500 lines (consider splitting)

**Exceptions:**
- Auto-generated code (migrations, protobuf, etc.)
- Large refactors (get approval before starting)
- Documentation updates

### Review Process

1. **Automated checks run** (GitHub Actions)
2. **Maintainer reviews code** (1-2 business days)
3. **Feedback addressed** by contributor
4. **Final approval** from maintainer
5. **Squash and merge** to main

### Merge Requirements

- ✅ At least 1 approving review
- ✅ All CI checks passing
- ✅ No unresolved conversations
- ✅ Branch up to date with main
- ✅ No merge conflicts

---

## 🐛 Local Debugging

### Make Commands

```bash
# View logs from all services
make logs

# View logs from specific service
docker-compose logs -f backend

# Restart a service
make restart service=backend

# Reset database (WARNING: deletes all data)
make db-reset

# Run database migrations
make migrate

# Open PostgreSQL shell
make db-shell

# Open Neo4j browser
open http://localhost:7474

# Run linters
make lint

# Run formatters
make format

# Run full check (format + lint + test)
make check
```

### VSCode Integration (Optional)

We provide a development container configuration for VSCode:

1. Install **Remote - Containers** extension
2. Open command palette: "Remote-Containers: Reopen in Container"
3. VSCode will build and connect to dev container

Includes:
- Python language server (Pylance)
- Extensions: Black, Ruff, MyPy, GitLens
- Pre-configured debugger launch configs
- Integrated terminal with all tools

### Debugging FastAPI

Add this to any route for interactive debugging:

```python
import debugpy

@app.post("/debug-route")
def debug_route():
    debugpy.listen(("0.0.0.0", 5678))
    debugpy.wait_for_client()  # Execution pauses here
    breakpoint()  # Or use this for Python's built-in debugger
    # Your code here
```

Then connect with VSCode debugger on port 5678.

### Debugging React

Use React DevTools browser extension:
- [Chrome](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)

Or add debugger statements:

```typescript
const handleClick = () => {
  debugger; // Execution pauses in browser DevTools
  // Your code here
};
```

---

## 🙏 Acknowledgments

### Contributors

We maintain a list of all contributors in `AUTHORS.md` *(coming soon)*. If you've contributed code, documentation, or other improvements, please add yourself!

### First-Time Contributors

We welcome first-time contributors! Look for issues labeled:

- `good first issue` - Well-scoped tasks perfect for newcomers
- `help wanted` - Areas where we need community help
- `documentation` - Documentation improvements (great starting point!)

### Recognition

Contributors will be:
- Listed in `AUTHORS.md`
- Mentioned in release notes for significant contributions
- Invited to join the Codexify community Discord *(coming soon)*

---

## 📚 Additional Resources

### Documentation

- [README.md](README.md) - Project overview and quick start
- [Architecture Guide](docs/DB_POSTGRES_ONLY.md) - Database design
- [API Documentation](http://localhost:8888/docs) - Interactive API reference
- [Plugin Development](docs/Plugins/) - Building custom plugins
- [Infrastructure Guides](docs/infra/) - Deployment and scaling

### Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/Resonant-Jones/Codexify/issues)
- **GitHub Discussions**: [Ask questions and share ideas](https://github.com/Resonant-Jones/Codexify/discussions)
- **Email**: dev@catalystlabs.ai

### Getting Help

**Before asking for help:**
1. Check the [README](README.md) and [documentation](docs/)
2. Search [existing issues](https://github.com/Resonant-Jones/Codexify/issues)
3. Review [discussions](https://github.com/Resonant-Jones/Codexify/discussions)

**When asking for help:**
- Provide context (what you're trying to do)
- Include error messages (full stack trace)
- Share relevant code snippets
- Describe what you've already tried

---

## 🔐 Security

**Never commit:**
- API keys or secrets
- `.env` files
- Credentials or tokens
- Private keys or certificates

**Security vulnerabilities:**
- Email **security@catalystlabs.ai** (do not open public issues)
- Include detailed description and reproduction steps
- We'll respond within 48 hours

---

## 📄 License

By contributing to Codexify, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

<div align="center">

**Thank you for contributing to Codexify!**

*Together, we're building the future of intelligent, local-first knowledge management.*

**Questions?** Reach out at dev@catalystlabs.ai or [open a discussion](https://github.com/Resonant-Jones/Codexify/discussions).

</div>

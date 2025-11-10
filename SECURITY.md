# Security Policy

## Security Overview

Codexify is committed to providing a secure, local-first AI orchestration platform that prioritizes data sovereignty and user privacy. Our architecture is designed to keep your data under your control, with secure integrations to cloud services only when explicitly configured.

**Core Security Principles:**

- **Data Sovereignty**: All processing occurs locally by default; cloud integrations are opt-in and user-controlled
- **Privacy by Design**: Sensitive information is scrubbed from logs and never transmitted without explicit user consent
- **Secure by Default**: Environment-based configuration prevents hardcoded secrets and credential leakage
- **Transparency**: Open-source codebase allows full security auditing and community review

## Current Security Protections

Codexify implements multiple layers of security to protect your data and system:

### Authentication & Authorization

- **API Key Authentication**: Guardian API endpoints are protected with `GUARDIAN_API_KEY` environment variable
- **Configurable Access Control**: API keys can be rotated and managed through environment configuration
- **OAuth Integration**: Google Drive and other cloud integrations use OAuth 2.0 for secure, delegated access

### Input Validation & Injection Prevention

- **[Pydantic](https://docs.pydantic.dev/)** model validation on all API inputs prevents malformed data from reaching backend logic
- **[SQLAlchemy](https://www.sqlalchemy.org/)** ORM protections guard against SQL injection attacks through parameterized queries
- **Type-safe data models** enforce schema validation across the entire application stack

### Sensitive Data Protection

- **Automatic Log Scrubbing**: `ScrubFormatter` class masks sensitive file paths and credentials in all log output
  - Redacts: `client_secret*.json`, `credentials.json`, `token.*`, private keys (`.pem`, `.p12`, `.pfx`)
  - Configurable via `GUARDIAN_SCRUB_LOGS`, `GUARDIAN_SCRUB_EXTRA_EXTS`, `GUARDIAN_SCRUB_PLAINTEXT_SECRETS`
- **Environment-based Secrets**: All API keys and credentials stored in `.env` files (never committed to version control)
- **Secret Masking in APIs**: Connector configuration endpoints automatically redact secret fields in responses

### Network Security

- **CORS Restrictions**: Configurable cross-origin resource sharing policies
  - Default: localhost only (`http://localhost:5173`)
  - Configurable via `GUARDIAN_CORS_ORIGINS`, `GUARDIAN_CORS_METHODS`, `GUARDIAN_CORS_HEADERS`
  - Credential handling follows secure CORS best practices

### Code Quality & Security Scanning

- **[Bandit](https://bandit.readthedocs.io/)** static security analysis runs on all Python code via pre-commit hooks
- **Pre-commit Security Hooks**:
  - `detect-private-key`: Prevents accidental commit of private keys
  - `check-merge-conflict`: Detects unresolved merge conflicts
  - `debug-statements`: Removes debug code before commit
- **Automated Testing**: `pytest` suite runs on every push to validate security-critical paths
- **Type Checking**: `mypy` enforces type safety to prevent runtime type confusion vulnerabilities

## Planned Security Enhancements

We are actively working to strengthen Codexify's security posture with the following near-term improvements:

### Rate Limiting & DoS Protection

- **[SlowAPI](https://github.com/laurentS/slowapi)** integration for request rate limiting
- Configurable rate limits per endpoint and per API key
- Automatic IP-based throttling for abuse prevention

### Security Headers

- **[fastapi-security-headers](https://github.com/yezz123/fastapi-security-headers)** implementation
- Content Security Policy (CSP) headers
- HSTS, X-Frame-Options, and other OWASP-recommended headers

### Advanced Authentication

- **JWT-based Authentication** option for stateless, scalable API access
- Token expiration and refresh mechanisms
- Support for multiple authentication backends

### Session & Cache Security

- **Redis-backed Session Caching** for improved performance and security
- Encrypted session storage
- Configurable session timeout and invalidation

### Audit Logging & RBAC

- **Comprehensive Audit Logging** of all security-sensitive operations
- Role-Based Access Control (RBAC) for multi-user environments
- Tamper-proof audit trail with cryptographic signing

## Vulnerability Disclosure Policy

Security is a top priority for the Codexify project. We deeply appreciate responsible disclosure from security researchers and the community.

### Reporting Security Issues

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, please report security concerns through one of the following channels:

- **GitHub Security Advisories**: [Report a vulnerability](https://github.com/Resonant-Jones/Codexify/security/advisories/new) (preferred)
- **Email**: Send details to `security@codexify.dev` (if available) or contact the maintainers directly

### What to Include

When reporting a vulnerability, please provide:

- Description of the vulnerability and potential impact
- Steps to reproduce the issue
- Affected versions (if known)
- Any proof-of-concept code (if applicable)
- Your contact information for follow-up

### Response Timeline

- **Initial Response**: We aim to acknowledge your report within **72 hours**
- **Status Update**: Regular updates every 5-7 days until resolution
- **Disclosure Coordination**: We will work with you to coordinate public disclosure timing

### Our Commitment

- Security bugs are **prioritized above all other work**
- Fixes will be released as soon as they are validated and tested
- Credit will be given to researchers in security advisories (unless you prefer to remain anonymous)

## Dependency Security

Codexify actively monitors and maintains its dependency tree to minimize exposure to known vulnerabilities.

### Security Tooling

We use the following tools to track and remediate dependency vulnerabilities:

- **[Bandit](https://bandit.readthedocs.io/)**: Static security analysis for Python code
- **[pip-audit](https://pypi.org/project/pip-audit/)**: Automated scanning of Python dependencies for known CVEs
- **[safety](https://pyup.io/safety/)**: Database of known security vulnerabilities in Python packages
- **Dependabot** (GitHub): Automated pull requests for dependency updates

### Patch Policy

- **Critical vulnerabilities**: Patched within **48 hours** of disclosure
- **High-severity vulnerabilities**: Patched within **7 days** of disclosure
- **Medium/Low severity**: Patched in next regular release cycle

We encourage users to keep their Codexify installations up to date to receive the latest security patches.

## Environment & Secrets Management

### Environment Variables

Codexify uses environment variables for all sensitive configuration. Key files:

- **`.env`**: Local secrets (never committed to git, added to `.gitignore`)
- **`.env.example`**: Template showing required environment variables with dummy values
- **`.env.template`**: Additional configuration template

### Required Secrets

The following environment variables may contain sensitive information:

| Variable | Description | Required |
|----------|-------------|----------|
| `GENAI_API_KEY` | Google Gemini API key for language model access | Yes |
| `NOTION_API_KEY` | Notion integration token | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | Optional |
| `GROQ_API_KEY` | Groq API key for LLM provider | Optional |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `GUARDIAN_API_KEY` | API key for Guardian backend authentication | Recommended |
| `DATABASE_URL` | Database connection string (may contain passwords) | Optional |

### Best Practices

- **Never commit** `.env` or any file containing real API keys or credentials
- Use **dummy values** (e.g., `GENAI_API_KEY=dummy`) in CI/CD pipelines and automated testing
- Rotate API keys regularly, especially if you suspect compromise
- Use environment-specific `.env` files for development, staging, and production
- Limit `.env` file permissions to current user only: `chmod 600 .env`

### Example Configuration

See [`.env.example`](.env.example) for a complete template of required and optional environment variables.

## Best Practices for Contributors

All contributors must follow these security guidelines:

### Pre-commit Hooks

- **Always enable pre-commit hooks** before making your first commit:
  ```bash
  pip install pre-commit
  pre-commit install
  ```
- Hooks will automatically check for:
  - Private keys and credentials
  - Security vulnerabilities (Bandit)
  - Code quality issues
  - Test failures

### Secure Coding Standards

- **Never hardcode credentials** or API keys in source code
- Use **dummy/fake API keys** during testing (e.g., `sk-test-dummy-key-12345`)
- Implement **principle of least privilege**: request minimum necessary permissions
- Validate all user inputs with Pydantic models or similar validation frameworks
- Use parameterized queries (via SQLAlchemy ORM) to prevent SQL injection
- Avoid storing sensitive data in logs; use `ScrubFormatter` patterns when logging user data

### Code Review Requirements

All pull requests must:

- Pass Bandit security scans (no high-severity findings)
- Include tests for security-sensitive functionality
- Document any new environment variables or configuration options
- Update `.env.example` if new secrets are introduced

### Secure Development Environment

- Keep your development dependencies up to date: `pip install --upgrade -r requirements.txt`
- Use virtual environments to isolate project dependencies
- Never run untrusted code with production credentials
- Use separate API keys for development and production

## Reporting Security Issues (Summary)

**If you discover a security vulnerability:**

1. **DO NOT** create a public GitHub issue
2. **DO** report via [GitHub Security Advisories](https://github.com/Resonant-Jones/Codexify/security/advisories/new) or email maintainers
3. **Include** detailed reproduction steps and impact assessment
4. **Wait** for confirmation before public disclosure

We will respond within **72 hours** and work with you to coordinate responsible disclosure.

## Acknowledgments

We are grateful to the security research community and all contributors who help make Codexify more secure.

**Security Model Inspiration:**
- [OpenAI Security Practices](https://openai.com/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)

**Special Thanks:**
- All security researchers who responsibly disclose vulnerabilities
- The Bandit, SQLAlchemy, and FastAPI teams for their security-focused frameworks
- The open-source security community for continuous improvement

---

**Last Updated**: November 2025
**Security Contact**: GitHub Security Advisories or maintainer direct contact

For general questions about Codexify, see our [main documentation](./docs/) or [open an issue](https://github.com/Resonant-Jones/Codexify/issues/new).

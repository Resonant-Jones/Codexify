# Changelog

All notable changes to Codexify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive root README.md with architecture diagram and quick start guide
- Detailed CONTRIBUTING.md with development workflow and code style guidelines
- CHANGELOG.md for version tracking and release notes

### Changed
- Standardized line length to 88 characters across all tooling
- Updated pre-commit configuration for consistent code quality

### Fixed
- Resolved line length inconsistency between .pre-commit-config.yaml (80) and pyproject.toml (88)

## [0.9.0] - 2025-11-08

### Added
- Comprehensive codebase audit and documentation review
- Test coverage reporting integration (targeting 80% minimum)
- Security section in documentation with vulnerability reporting process
- Frontend quality checks in CI pipeline (lint, build, test)
- Schema drift validation workflow in GitHub Actions

### Changed
- Improved API documentation structure
- Enhanced error handling in FastAPI routes
- Optimized Docker Compose configuration for development workflow

### Fixed
- Database connection pooling configuration (preparing for production)
- Memory leak in long-running chat sessions
- Token count overflow in context window management

### Security
- Implemented log scrubbing for sensitive filenames and credentials
- Added API key authentication to FastAPI endpoints
- Enabled Bandit security linting in pre-commit hooks
- Added private key detection in git hooks

## [0.8.0] - 2025-10-26

### Added
- Comprehensive database documentation (DB_POSTGRES_ONLY.md)
- PostgreSQL setup guide with migration instructions
- Alembic migration workflow documentation
- Event sourcing with events_outbox table
- Audit logging table for compliance tracking

### Changed
- **BREAKING**: Migrated from dual SQLite/Postgres to Postgres-only architecture
- Refactored GuardianDB to thin service layer over SQLAlchemy ORM
- All schema management now handled exclusively via Alembic migrations
- Updated all database adapters to use SQLAlchemy 2.0 patterns

### Removed
- **BREAKING**: SQLite support completely removed
- Legacy sqlite3 imports and .db file references
- Runtime DDL creation in application code

### Fixed
- Schema drift issues between runtime models and database
- Connection handling in async database operations
- Migration idempotency issues

## [0.7.0] - 2025-09-15

### Added
- Multi-provider AI routing (Groq, OpenAI, Anthropic, Gemini)
- Provider registry with capability detection
- Streaming response support with Server-Sent Events
- ChromaDB integration for vector storage
- FAISS backend for fast similarity search
- Sentence transformers for local embeddings

### Changed
- Improved LLM client factory with provider selection
- Enhanced token budget management for context windows
- Optimized vector search performance with FAISS indexing

### Fixed
- Streaming response buffering issues
- Provider fallback mechanism reliability
- Embedding dimension mismatch errors

## [0.6.0] - 2025-08-20

### Added
- Plugin architecture with manifest-based loading
- Pattern analyzer plugin for conversation analysis
- Memory analyzer plugin for consolidation strategies
- System diagnostics plugin for health monitoring
- Plugin registry with dynamic discovery
- Plugin scaffolding command (`make init-plugin`)

### Changed
- Decoupled plugins from core system for better extensibility
- Standardized plugin interface with base classes
- Improved plugin error handling and isolation

### Deprecated
- Direct plugin imports (use registry instead)

### Fixed
- Plugin loading race conditions
- Memory leaks in long-running plugin instances

## [0.5.0] - 2025-07-10

### Added
- Neo4j knowledge graph integration
- Graph-based relationship tracking for messages and users
- Semantic connection discovery via graph queries
- Neo4j session management with connection pooling
- Graph initialization scripts with constraints

### Changed
- Enhanced memory system with graph-backed relationships
- Improved context retrieval using hybrid Postgres + Neo4j queries
- Updated Docker Compose with Neo4j service

### Fixed
- Neo4j driver cleanup on shutdown
- Graph query optimization for large datasets
- Bolt connection timeout handling

## [0.4.0] - 2025-06-05

### Added
- Three-tier memory system (ephemeral, midterm, longterm)
- Memory consolidation algorithms
- Semantic search across memory silos
- Memory tagging and pinning functionality
- Memory entry CRUD operations via API

### Changed
- Refactored memory storage to use dedicated tables
- Improved memory retrieval with vector similarity
- Enhanced memory update operations with timestamps

### Fixed
- Memory silo transitions and expiration logic
- Vector embedding consistency across memory types

## [0.3.0] - 2025-05-01

### Added
- Connector framework for external integrations
- GitHub connector with repository sync
- Google Drive connector with OAuth2 flow
- Notion connector with API integration
- Connector configuration management
- Connector run tracking and logging

### Changed
- Unified connector interface for consistent behavior
- Improved OAuth2 flow with state management
- Enhanced connector error handling and retries

### Security
- OAuth2 credentials stored encrypted
- Connector API keys managed via environment variables

## [0.2.0] - 2025-04-10

### Added
- Chat thread hierarchies with parent-child relationships
- Thread archival functionality
- Project-based thread organization
- Message role management (user, assistant, system)
- Thread summary generation
- Full-text search across threads and messages

### Changed
- Migrated from flat chat structure to hierarchical threads
- Improved thread listing with pagination
- Enhanced message retrieval with context window management

### Fixed
- Thread deletion cascade behavior
- Message ordering in long conversations

## [0.1.0] - 2025-03-01

### Added
- Initial FastAPI backend with RESTful API
- Basic chat thread and message management
- PostgreSQL database with SQLAlchemy ORM
- React frontend with TypeScript and Vite
- Tailwind CSS styling
- Docker Compose development environment
- Makefile with common development tasks
- Pre-commit hooks for code quality
- GitHub Actions CI pipeline
- Pytest test suite with fixtures
- Basic authentication with API keys
- Environment-based configuration

### Security
- API key authentication
- CORS middleware configuration
- Input validation with Pydantic

---

## Version History Links

[Unreleased]: https://github.com/Resonant-Jones/Codexify/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Resonant-Jones/Codexify/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Resonant-Jones/Codexify/releases/tag/v0.1.0

---

## Maintenance Notes

### Updating This Changelog

This changelog is maintained following these guidelines:

1. **Keep [Unreleased] section up-to-date** - Add entries as changes are made
2. **Use standard categories** - Added, Changed, Deprecated, Removed, Fixed, Security
3. **Write for humans** - Clear, concise descriptions of changes
4. **Note breaking changes** - Prefix with **BREAKING** in bold
5. **Link to issues** - Reference issue numbers when applicable (e.g., #123)

### Release Process

When cutting a new release:

1. Move [Unreleased] entries to new version section
2. Add version number and release date in ISO 8601 format (YYYY-MM-DD)
3. Update version links at bottom of file
4. Create git tag: `git tag -a v0.9.0 -m "Release v0.9.0"`
5. Push tag: `git push origin v0.9.0`

### Future Automation

This changelog is currently maintained manually. Future enhancements:

- Automatic changelog generation from Conventional Commits
- Integration with GitHub Releases
- Automated version bumping via CI/CD
- Changelog validation in pre-commit hooks

For questions about releases or changelog entries, contact dev@catalystlabs.ai.

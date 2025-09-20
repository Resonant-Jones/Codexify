# Local Postgres Setup

## Quick Start

Run the bootstrap script from the repo root to provision Docker Postgres, update `.env`, apply SQL, and confirm connectivity:

```bash
bash scripts/pg_bootstrap.sh
```

The script is idempotent, so you can run it again whenever you need to ensure your database is ready.

## Verifying Your Database

Use the verification helper to print the active DSN, list tables, and confirm the session user:

```bash
bash scripts/pg_verify.sh
```

You can also invoke `make db-bootstrap`, `make db-verify`, or the npm scripts `npm run db:bootstrap` and `npm run db:verify` if you prefer those entry points.

## Troubleshooting

- **Port already in use** – Another process is listening on `localhost:5432`. Stop that service or change its port, then rerun the bootstrap script.
- **Container name mismatch** – If you already have a container exposing `localhost:5432`, the script will reuse it and warn you. Rename or stop conflicting containers if you want to manage a dedicated `guardian-pg` instance.
- **`psql` not installed** – Install the PostgreSQL client tools. On macOS: `brew install libpq && brew link --force libpq`. On other systems use your package manager (e.g. `apt install postgresql-client`).

## Rerunning

Re-run `bash scripts/pg_bootstrap.sh` anytime after pulling new migrations or resetting local data. It will restart the container if needed, keep `DATABASE_URL` in sync with `GUARDIAN_DB_URL`, re-apply SQL files, and print the next steps when everything is healthy.

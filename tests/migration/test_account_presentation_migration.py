"""Synthetic-store round trip; never targets an application database."""

import importlib
import os

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

migration = importlib.import_module(
    "guardian.db.migrations.versions.f3a9c7d2b8e1_account_presentation"
)


@pytest.fixture(params=["sqlite", "postgres"])
def store(request):
    url = "sqlite+pysqlite://"
    if request.param == "postgres":
        url = os.environ.get("PRESENTATION_TEST_DATABASE_URL")
        if not url:
            pytest.skip("Disposable PRESENTATION_TEST_DATABASE_URL required")
        parsed = sa.engine.make_url(url)
        assert (parsed.host or parsed.query.get("host")) in (
            "127.0.0.1",
            "/tmp/presentation-pg-20261118/socket",
        )
        assert parsed.database == "codexify_presentation_proof"
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE users (id VARCHAR(255) PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO users VALUES ('synthetic-owner')"))
        conn.commit()
        try:
            yield conn
        finally:
            conn.rollback()
            conn.execute(sa.text("DROP TABLE IF EXISTS user_presentation"))
            conn.execute(sa.text("DROP TABLE users"))
            conn.commit()
    engine.dispose()


def apply(conn, action):
    with Operations.context(MigrationContext.configure(conn)):
        action()
    conn.commit()


def test_empty_upgrade_binary_json_roundtrip_constraints_and_downgrade(store):
    apply(store, migration.upgrade)
    assert store.scalar(sa.text("SELECT count(*) FROM user_presentation")) == 0
    table = sa.Table("user_presentation", sa.MetaData(), autoload_with=store)
    data = b"\x00\xffSynthetic private image"
    row = dict(
        user_id="synthetic-owner",
        workspace_id="account",
        is_unique=False,
        settings={"theme_mode": "dark"},
        wallpaper_data=data,
        wallpaper_mime="image/png",
    )
    store.execute(table.insert(), row)
    store.commit()
    got = store.execute(sa.select(table)).mappings().one()
    assert got["wallpaper_data"] == data and got["settings"] == row["settings"]
    for change in (
        {"is_unique": True},
        {"wallpaper_mime": None},
        {"wallpaper_mime": "image/svg+xml"},
        {"wallpaper_data": None},
    ):
        with pytest.raises(sa.exc.IntegrityError):
            with store.begin_nested():
                store.execute(table.update().values(**change))
    apply(store, migration.downgrade)
    assert "user_presentation" not in sa.inspect(store).get_table_names()
    assert store.scalar(sa.text("SELECT id FROM users")) == "synthetic-owner"
    apply(store, migration.upgrade)
    assert store.scalar(sa.text("SELECT count(*) FROM user_presentation")) == 0


def test_single_head_and_no_private_bio_revision():
    config = Config("backend/alembic.ini")
    config.set_main_option("script_location", "guardian/db/migrations")
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["a3f8c2d6e901"]
    assert migration.down_revision == "d2e7a9b4c1f6"
    assert len(list(scripts.walk_revisions())) == 145


def test_postgres_concurrent_partial_changes_preserve_both_fields(store):
    if store.dialect.name != "postgresql":
        pytest.skip("Row locking proof requires PostgreSQL")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4
    from sqlalchemy.orm import sessionmaker
    from guardian.services import account_presentation

    apply(store, migration.upgrade)
    store.commit()
    factory = sessionmaker(store.engine, autoflush=False)
    barrier = Barrier(2)
    workspace = str(uuid4())

    def change(settings):
        with factory.begin() as session:
            barrier.wait(timeout=5)
            account_presentation.save(
                session, "synthetic-owner", workspace, settings=settings
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(change, value)
            for value in ({"theme_mode": "dark"}, {"base_color": "#123456"})
        ]
        for future in futures:
            future.result(timeout=10)
    with factory() as session:
        settings = account_presentation.payload(session, "synthetic-owner", workspace)[
            "settings"
        ]
        assert settings["theme_mode"] == "dark" and settings["base_color"] == "#123456"

"""Bind opt-in OpenAI imports to an owner-selected logical source."""

from alembic import op

revision = "a64c358e2241"
down_revision = "e723ba9046cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE openai_import_sources (
            id varchar(36) PRIMARY KEY,
            user_id varchar(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label varchar(120) NOT NULL CHECK (length(btrim(label)) > 0),
            CONSTRAINT uq_openai_import_sources_id_user UNIQUE (id, user_id)
        )
    """)
    op.execute("""
        CREATE TABLE openai_import_project_groups (
            user_id varchar(255) NOT NULL,
            source_id varchar(36) NOT NULL,
            group_id varchar(36) NOT NULL,
            project_id integer,
            PRIMARY KEY (user_id, source_id, group_id),
            CONSTRAINT fk_openai_import_groups_source_owner
                FOREIGN KEY (source_id, user_id)
                REFERENCES openai_import_sources(id, user_id) ON DELETE CASCADE,
            CONSTRAINT fk_openai_import_groups_project_owner
                FOREIGN KEY (project_id, user_id)
                REFERENCES projects(id, user_id) ON DELETE SET NULL (project_id),
            CONSTRAINT ck_openai_import_groups_full_id
                CHECK (group_id ~ '^g-p-[0-9a-f]{32}$')
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_openai_import_groups_project
        ON openai_import_project_groups(project_id) WHERE project_id IS NOT NULL
    """)
    for table, origin, fk, check in (
        ("chat_threads", "origin_system",
         "fk_chat_threads_openai_import_source_owner",
         "ck_chat_threads_openai_import_source_origin"),
        ("openai_account_import_jobs", "source_system",
         "fk_openai_import_jobs_openai_source_owner",
         "ck_openai_import_jobs_openai_source_system"),
    ):
        op.execute(f"""
            ALTER TABLE {table} ADD COLUMN openai_import_source_id varchar(36),
            ADD CONSTRAINT {fk} FOREIGN KEY (openai_import_source_id, user_id)
                REFERENCES openai_import_sources(id, user_id),
            ADD CONSTRAINT {check}
                CHECK (openai_import_source_id IS NULL OR {origin} = 'openai')
        """)
    op.execute("""
        CREATE FUNCTION guard_openai_import_source_placement() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.openai_import_source_id IS DISTINCT FROM NEW.openai_import_source_id
               OR (OLD.openai_import_source_id IS NOT NULL AND OLD.user_id IS DISTINCT FROM NEW.user_id)
            THEN
                RAISE EXCEPTION 'OpenAI import source binding is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $$
    """)
    for table in ("chat_threads", "openai_account_import_jobs"):
        op.execute(f"""
            CREATE TRIGGER immutable_openai_import_source BEFORE UPDATE OF user_id, openai_import_source_id
            ON {table} FOR EACH ROW EXECUTE FUNCTION guard_openai_import_source_placement()
        """)
    op.execute("""
        CREATE FUNCTION guard_openai_import_project_group() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF (OLD.user_id, OLD.source_id, OLD.group_id) IS DISTINCT FROM
               (NEW.user_id, NEW.source_id, NEW.group_id)
               OR (OLD.project_id IS DISTINCT FROM NEW.project_id AND
                   (NEW.project_id IS NOT NULL OR EXISTS
                    (SELECT 1 FROM projects WHERE id = OLD.project_id)))
            THEN
                RAISE EXCEPTION 'OpenAI import Project mapping is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $$
    """)
    op.execute("""
        CREATE TRIGGER immutable_openai_import_project_group BEFORE UPDATE
        ON openai_import_project_groups FOR EACH ROW EXECUTE FUNCTION guard_openai_import_project_group()
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM openai_import_sources) THEN
                RAISE EXCEPTION 'Refusing to discard OpenAI import source placement state';
            END IF;
        END $$
    """)
    for table in ("openai_account_import_jobs", "chat_threads"):
        op.execute(f"DROP TRIGGER immutable_openai_import_source ON {table}")
        op.drop_column(table, "openai_import_source_id")
    op.execute("DROP FUNCTION guard_openai_import_source_placement()")
    op.drop_table("openai_import_project_groups")
    op.execute("DROP FUNCTION guard_openai_import_project_group()")
    op.drop_table("openai_import_sources")

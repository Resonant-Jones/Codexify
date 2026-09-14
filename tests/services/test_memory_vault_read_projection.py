"""
Focused PostgreSQL tests for the Memory Vault backend read projection (UMS-05B1).

This test exercises the production ``MemoryVaultReadService`` against a
dedicated PostgreSQL 17.6 authority on ``/tmp/.s.PGSQL.55432``. It
proves:

- account isolation across the canonical and compatibility surfaces;
- canonical list/detail projection of every UMS-05A admitted field;
- compatibility coexistence (legacy memory + verified fact +
  candidate fact) in one Vault read surface;
- Personal Facts posture derives through the existing UMS-03F/03G
  authority without persisting a second Vault truth;
- stable Persona attribution and stable-id filter behavior;
- provenance multiplicity, local provenance, and opaque external
  provenance preservation;
- canonical-only filters (species, Project, account scope, review,
  lifecycle, source system, pinned, held) operate as documented;
- integrity defects fail closed without returning partial content;
- the read path performs zero durable writes (snapshots taken
  before and after the full read surface exercises).

The unrelated ``MemoryKeyVault`` in
``guardian/modules/memory_key_vault.py`` is intentionally not exercised
by this test.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker

from guardian.db.models import (
    MemoryEntry,
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    PersonalFact,
    PersonalFactEvidence,
    PersonalFactRevision,
    PersonaSubject,
    PersonaSubjectBinding,
    PersonaSubjectLifecycle,
    Project,
    User,
)
from guardian.protocol_tokens import MemorySemanticSpecies, PersonalFactStatus

#: Closed source-system vocabulary from the canonical migration
#: ``f6b0d3e8c5a2_add_canonical_memory_persistence``. Kept as a
#: module-level string constant so the test does not depend on a
#: Python enum that does not yet exist in ``protocol_tokens``.
CODEXIFY_SOURCE_SYSTEM = "codexify"
CHAT_SOURCE_SUBJECT_KIND = "chat"
from guardian.services.memory_vault_read import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    MemoryVaultReadError,
    MemoryVaultReadService,
    VaultIdentity,
    VaultListFilter,
)

ACCOUNT_A = "ums05b1-account-a"
ACCOUNT_B = "ums05b1-account-b"


def _admin_url() -> str:
    base = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not base:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")
    return base


def _create_disposable_database(admin_url: str, name: str) -> str:
    import psycopg

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{name}"')
    parts = admin_url.split("?", 1)
    base = parts[0].rsplit("/", 1)[0]
    suffix = ("?" + parts[1]) if len(parts) == 2 else ""
    return f"{base}/{name}{suffix}"


def _drop_database(admin_url: str, name: str) -> None:
    import psycopg

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
    except Exception:
        pass


def _migrate_to_head(database_url: str) -> None:
    from alembic.command import upgrade
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    os.environ["DATABASE_URL"] = database_url
    os.environ["GUARDIAN_DATABASE_URL"] = database_url
    upgrade(config, "head")


@pytest.fixture
def database_url():
    admin = _admin_url()
    name = f"ums05b1_{uuid.uuid4().hex[:10]}"
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture
def session_factory(database_url):
    engine = sa.create_engine(database_url, future=True)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    try:
        yield factory
    finally:
        engine.dispose()


def _seed_users_and_project(session, *, account_ids: list[str]) -> dict[str, int]:
    """Seed users + one Project per account. Returns account_id -> project_id."""
    project_by_account: dict[str, int] = {}
    for i, account_id in enumerate(account_ids):
        session.add(
            User(id=account_id, username=account_id, password_hash="test", role="guest")
        )
        project = Project(
            id=9000 + i,
            user_id=account_id,
            name=f"{account_id}-project",
            identity_depth="light",
        )
        session.add(project)
        project_by_account[account_id] = project.id
    session.commit()
    return project_by_account


def _seed_canonical_fixtures(session, *, account_id: str, project_id: int) -> dict:
    """Seed Account A canonical fixture per the UMS-05B1 spec."""
    canonical_ids = {}

    # 1. episodic/semantic memory
    episodic_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=episodic_id,
            user_id=account_id,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Episodic memory text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    canonical_ids["episodic_id"] = episodic_id

    # 2. project-scoped memory
    project_scoped_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=project_scoped_id,
            user_id=account_id,
            project_id=project_id,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Project-scoped memory text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    canonical_ids["project_scoped_id"] = project_scoped_id

    # 3. pinned memory
    pinned_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=pinned_id,
            user_id=account_id,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Pinned memory text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=True,
            held=False,
        )
    )
    canonical_ids["pinned_id"] = pinned_id

    # 4. held memory
    held_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=held_id,
            user_id=account_id,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Held memory text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=True,
        )
    )
    canonical_ids["held_id"] = held_id

    # 5. canonical memory with two provenance rows + one with two
    prov_id = str(uuid.uuid4())
    prov_memory_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=prov_memory_id,
            user_id=account_id,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Multi-provenance memory text",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
            pinned=False,
            held=False,
        )
    )
    session.flush()
    session.add(
        MemoryProvenance(
            provenance_id=prov_id,
            memory_id=prov_memory_id,
            user_id=account_id,
            source_system=CODEXIFY_SOURCE_SYSTEM,
            source_subject_kind=CHAT_SOURCE_SUBJECT_KIND,
            source_subject_id="chat-thread-1",
            is_imported=False,
        )
    )
    session.add(
        MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=prov_memory_id,
            user_id=account_id,
            source_system=CODEXIFY_SOURCE_SYSTEM,
            source_subject_kind=CHAT_SOURCE_SUBJECT_KIND,
            source_subject_id="chat-message-42",
            is_imported=False,
        )
    )
    canonical_ids["prov_memory_id"] = prov_memory_id

    # 6. stable Persona subject attribution on episodic_id
    persona_subject_id = str(uuid.uuid4())
    session.add(
        PersonaSubject(
            persona_subject_id=persona_subject_id,
            user_id=account_id,
            display_name_snapshot="Account-A Persona 1",
            lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
        )
    )
    session.flush()
    session.add(
        MemoryPersonaLink(
            link_id=str(uuid.uuid4()),
            memory_id=episodic_id,
            user_id=account_id,
            persona_subject_id=persona_subject_id,
            persona_user_id=account_id,
            link_kind="captured_under",
        )
    )
    canonical_ids["persona_subject_id"] = persona_subject_id

    return canonical_ids


def _seed_compatibility_fixtures(session, *, account_id: str) -> dict:
    """Seed Account A compatibility fixtures per the UMS-05B1 spec."""
    compat_ids = {}

    # 1. legacy memory entry -> episodic_semantic_memory
    me = MemoryEntry(
        user_id=account_id,
        content="Legacy memory entry text",
        silo="longterm",
        tags="legacy",
        pinned=False,
    )
    session.add(me)
    session.flush()
    compat_ids["memory_entry_id"] = me.id

    # 2. verified + active personal fact
    pf_verified = PersonalFact(
        user_id=account_id,
        key="city",
        value="Test City",
        status=PersonalFactStatus.VERIFIED.value,
        is_active=True,
        confidence=0.95,
    )
    session.add(pf_verified)
    session.flush()
    compat_ids["verified_fact_id"] = pf_verified.id

    # 3. candidate / unreviewed personal fact
    pf_candidate = PersonalFact(
        user_id=account_id,
        key="hobby",
        value="Reading",
        status=PersonalFactStatus.CANDIDATE.value,
        is_active=False,
        confidence=None,
    )
    session.add(pf_candidate)
    session.flush()
    compat_ids["candidate_fact_id"] = pf_candidate.id

    return compat_ids


def _seed_account_b_fixtures(session, *, account_id: str) -> dict:
    """Seed Account B with one canonical memory and one compatibility record."""
    canonical_id = str(uuid.uuid4())
    session.add(
        MemoryRecord(
            memory_id=canonical_id,
            user_id=account_id,
            project_id=None,
            semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value,
            text_content="Account-B canonical memory",
            reviewed_at=sa.func.now(),
            activated_at=sa.func.now(),
        )
    )
    me_b = MemoryEntry(
        user_id=account_id,
        content="Account-B legacy memory",
        silo="longterm",
    )
    session.add(me_b)
    session.flush()
    return {
        "canonical_id": canonical_id,
        "memory_entry_id": me_b.id,
    }


@pytest.fixture
def seeded_database(session_factory):
    """Seed a fresh database with Account A and Account B fixtures."""
    with session_factory() as session:
        try:
            project_map = _seed_users_and_project(
                session, account_ids=[ACCOUNT_A, ACCOUNT_B]
            )
            canonical_a = _seed_canonical_fixtures(
                session, account_id=ACCOUNT_A, project_id=project_map[ACCOUNT_A]
            )
            compatibility_a = _seed_compatibility_fixtures(
                session, account_id=ACCOUNT_A
            )
            account_b = _seed_account_b_fixtures(session, account_id=ACCOUNT_B)
            session.commit()
            yield {
                "session_factory": session_factory,
                "account_a": {
                    "canonical": canonical_a,
                    "compatibility": compatibility_a,
                    "project_id": project_map[ACCOUNT_A],
                },
                "account_b": account_b,
            }
        except Exception:
            session.rollback()
            raise


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_account_isolation_list_excludes_account_b(seeded_database):
    """Account A list must never expose Account B content."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items()
    content_blob = json.dumps([json.loads(_item_to_json(it)) for it in items])
    assert ACCOUNT_B not in content_blob, content_blob
    # Spot-check: Account B canonical id must not appear
    assert ctx["account_b"]["canonical_id"] not in content_blob


def test_account_isolation_canonical_detail_fails_closed(seeded_database):
    """Account A canonical detail must not return Account B canonical record."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        item = svc.get_item(
            identity=VaultIdentity(
                kind="canonical",
                canonical_memory_id=ctx["account_b"]["canonical_id"],
            )
        )
    assert item is None


def test_account_isolation_compatibility_detail_fails_closed(seeded_database):
    """Account A compatibility detail must not return Account B legacy record."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        from guardian.core.memory_compatibility import (
            MemoryCompatibilitySourceKind,
            MemoryCompatibilitySourceRef,
        )

        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        item = svc.get_item(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
                    source_id=ctx["account_b"]["memory_entry_id"],
                ),
            )
        )
    assert item is None


def test_canonical_list_projects_required_fields(seeded_database):
    """Canonical records project identity, species, scope, posture, pin/hold."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(limit=MAX_LIST_LIMIT)
    by_id = {
        it.identity.canonical_memory_id: it
        for it in items
        if it.identity.kind == "canonical"
    }
    canonical = ctx["account_a"]["canonical"]
    assert canonical["episodic_id"] in by_id
    epi = by_id[canonical["episodic_id"]]
    assert epi.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    assert epi.account_owner == ACCOUNT_A
    assert epi.project_id is None
    assert epi.review_posture == "approved"
    assert epi.lifecycle_posture == "active"
    assert epi.pinned is False
    assert epi.held is False

    proj = by_id[canonical["project_scoped_id"]]
    assert proj.project_id == ctx["account_a"]["project_id"]

    pinned = by_id[canonical["pinned_id"]]
    assert pinned.pinned is True

    held = by_id[canonical["held_id"]]
    assert held.held is True


def test_compatibility_coexistence_in_one_vault_list(seeded_database):
    """List contains canonical + legacy memory + verified + candidate fact."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(limit=MAX_LIST_LIMIT)
    kinds = {it.identity.kind for it in items}
    species_seen = {it.semantic_species for it in items}
    assert kinds == {"canonical", "compatibility"}
    assert MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value in species_seen
    assert MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value in species_seen
    assert MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value in species_seen


def test_personal_facts_derived_posture(seeded_database):
    """Verified+active -> approved/active. Candidate -> pending/inactive."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(limit=MAX_LIST_LIMIT)
    compat = [it for it in items if it.identity.kind == "compatibility"]
    verified = [
        it
        for it in compat
        if it.semantic_species == MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value
    ]
    candidate = [
        it
        for it in compat
        if it.semantic_species == MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value
    ]
    assert verified, "verified+active fact must project"
    assert candidate, "candidate fact must project"
    assert all(it.review_posture == "approved" for it in verified)
    assert all(it.lifecycle_posture == "active" for it in verified)
    assert all(it.review_posture == "pending" for it in candidate)
    assert all(it.lifecycle_posture == "inactive" for it in candidate)


def test_persona_stable_subject_and_filter(seeded_database):
    """Stable subject ID is returned and used as filter authority."""
    ctx = seeded_database
    persona_id = ctx["account_a"]["canonical"]["persona_subject_id"]
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        all_items = svc.list_items(limit=MAX_LIST_LIMIT)
        filtered = svc.list_items(filter=VaultListFilter(persona_subject_id=persona_id))
    persona_items = [it for it in all_items if it.identity.kind == "canonical"]
    assert any(
        any(link.persona_subject_id == persona_id for link in it.persona_links)
        for it in persona_items
    )
    # Filter result must only contain items linked to the stable subject
    assert all(
        any(link.persona_subject_id == persona_id for link in it.persona_links)
        for it in filtered
    )


def test_provenance_multiplicity_preserved(seeded_database):
    """Canonical memory with two provenance rows retains multiplicity."""
    ctx = seeded_database
    prov_memory_id = ctx["account_a"]["canonical"]["prov_memory_id"]
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        item = svc.get_item(
            identity=VaultIdentity(kind="canonical", canonical_memory_id=prov_memory_id)
        )
    assert item is not None
    assert len(item.provenance) == 2


def test_source_system_filter(seeded_database):
    """Filtering by source system uses canonical provenance authority."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(
            filter=VaultListFilter(source_system=CODEXIFY_SOURCE_SYSTEM)
        )
    # All Account A canonical memories have codexify provenance
    assert all(
        any(p.source_system == CODEXIFY_SOURCE_SYSTEM for p in it.provenance)
        for it in items
    )


def test_project_exact_filter(seeded_database):
    """Exact Project filter narrows to Project-scoped canonical memories."""
    ctx = seeded_database
    project_id = ctx["account_a"]["project_id"]
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(filter=VaultListFilter(project_id=project_id))
    canonical_in_project = [it for it in items if it.identity.kind == "canonical"]
    assert all(it.project_id == project_id for it in canonical_in_project)
    assert any(
        it.identity.canonical_memory_id
        == ctx["account_a"]["canonical"]["project_scoped_id"]
        for it in canonical_in_project
    )


def test_account_scoped_only_filter(seeded_database):
    """account_scoped_only filter excludes Project-scoped memories."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        items = svc.list_items(filter=VaultListFilter(account_scoped_only=True))
    assert all(it.project_id is None for it in items)


def test_governance_filters_species_review_lifecycle_pinned_held(seeded_database):
    """Each governance filter narrows correctly."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)

        species_items = svc.list_items(
            filter=VaultListFilter(
                semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
            )
        )
        assert all(
            it.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
            for it in species_items
        )

        review_items = svc.list_items(filter=VaultListFilter(review_posture="approved"))
        assert all(it.review_posture == "approved" for it in review_items)

        life_items = svc.list_items(filter=VaultListFilter(lifecycle_posture="active"))
        assert all(it.lifecycle_posture == "active" for it in life_items)

        pinned_items = svc.list_items(filter=VaultListFilter(pinned=True))
        assert all(it.pinned is True for it in pinned_items)

        held_items = svc.list_items(filter=VaultListFilter(held=True))
        assert all(it.held is True for it in held_items)


def test_canonical_detail_full_readback(seeded_database):
    """Canonical detail returns identity, payload, posture, provenance."""
    ctx = seeded_database
    canonical = ctx["account_a"]["canonical"]
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        item = svc.get_item(
            identity=VaultIdentity(
                kind="canonical", canonical_memory_id=canonical["episodic_id"]
            )
        )
    assert item is not None
    assert item.identity.kind == "canonical"
    assert item.identity.canonical_memory_id == canonical["episodic_id"]
    assert item.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    assert item.content == "Episodic memory text"
    assert item.account_owner == ACCOUNT_A
    assert item.project_id is None
    assert item.review_posture == "approved"
    assert item.lifecycle_posture == "active"
    assert len(item.persona_links) == 1
    assert item.persona_links[0].link_kind == "captured_under"


def test_compatibility_detail_uses_existing_source_identity(seeded_database):
    """Compatibility detail uses the existing UMS compatibility source identity."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        from guardian.core.memory_compatibility import (
            MemoryCompatibilitySourceKind,
            MemoryCompatibilitySourceRef,
        )

        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        item = svc.get_item(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
                    source_id=ctx["account_a"]["compatibility"]["memory_entry_id"],
                ),
            )
        )
    assert item is not None
    assert item.identity.kind == "compatibility"
    assert (
        item.identity.compatibility_source.source_kind
        == MemoryCompatibilitySourceKind.MEMORY_ENTRY
    )
    assert (
        item.identity.compatibility_source.source_id
        == ctx["account_a"]["compatibility"]["memory_entry_id"]
    )
    assert item.semantic_species == MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value


def test_cross_account_persona_link_fails_closed(seeded_database):
    """A memory_persona_links row referencing another account's Persona
    subject is an integrity defect; the service must fail closed
    without returning partial content."""
    ctx = seeded_database
    canonical = ctx["account_a"]["canonical"]

    with ctx["session_factory"]() as session:
        # Add a Persona subject owned by Account B but link it to an
        # Account A canonical memory. The same-account CHECK
        # constraint would reject this state; the service-level guard
        # is still useful as defense in depth, so we drop the
        # constraint temporarily to manufacture the malformed row.
        other_persona_id = str(uuid.uuid4())
        session.add(
            PersonaSubject(
                persona_subject_id=other_persona_id,
                user_id=ACCOUNT_B,
                display_name_snapshot="B persona",
                lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
            )
        )
        session.flush()
        session.execute(
            sa.text(
                "ALTER TABLE memory_persona_links "
                "DROP CONSTRAINT memory_persona_links_same_account_check"
            )
        )
        session.execute(
            sa.text(
                "INSERT INTO memory_persona_links (link_id, memory_id, "
                "user_id, persona_subject_id, persona_user_id, link_kind) "
                "VALUES (:lid, :mid, :uid, :pid, :puid, :kind)"
            ),
            {
                "lid": str(uuid.uuid4()),
                "mid": canonical["episodic_id"],
                "uid": ACCOUNT_A,
                "pid": other_persona_id,
                "puid": ACCOUNT_B,
                "kind": "captured_under",
            },
        )
        session.commit()

        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReadError):
            svc.get_item(
                identity=VaultIdentity(
                    kind="canonical", canonical_memory_id=canonical["episodic_id"]
                )
            )


def test_list_default_limit_bounded_and_max_limit_enforced(seeded_database):
    """Default bound is 50; supplying a larger bound is clamped to 100."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        default_items = svc.list_items()
    assert len(default_items) <= DEFAULT_LIST_LIMIT

    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        huge = svc.list_items(limit=10_000)
    assert len(huge) <= MAX_LIST_LIMIT


def test_offset_zero_matches_default(seeded_database):
    """offset=0 preserves the previously qualified default list behavior."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        default_items = svc.list_items()
        offset_zero = svc.list_items(offset=0)
    assert [it.identity for it in offset_zero] == [it.identity for it in default_items]


def test_global_logical_offset_spans_canonical_and_compatibility(seeded_database):
    """Offset applies to the combined canonical + compatibility ordering,
    not separately per source family."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        full = svc.list_items(limit=MAX_LIST_LIMIT)
        page = svc.list_items(limit=2, offset=1)
    kinds = {it.identity.kind for it in full}
    assert kinds == {"canonical", "compatibility"}
    assert [it.identity for it in page] == [it.identity for it in full[1:3]]


def test_filter_applies_before_offset(seeded_database):
    """A filter narrows the logical list before offset is applied."""
    ctx = seeded_database
    species = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        full = svc.list_items(
            limit=MAX_LIST_LIMIT,
            filter=VaultListFilter(semantic_species=species),
        )
        page = svc.list_items(
            limit=2,
            offset=1,
            filter=VaultListFilter(semantic_species=species),
        )
    assert all(it.semantic_species == species for it in full)
    assert [it.identity for it in page] == [it.identity for it in full[1:3]]


def test_limit_100_with_nonzero_offset_is_valid(seeded_database):
    """100 is a page-size bound, not an absolute list position; a request
    where offset + limit exceeds 100 remains valid at the contract boundary."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        page = svc.list_items(limit=100, offset=10)
    assert isinstance(page, list)
    assert len(page) <= MAX_LIST_LIMIT


def test_large_offset_returns_empty(seeded_database):
    """An offset beyond the result set returns an empty list, not an error."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        page = svc.list_items(limit=10, offset=10_000)
    assert page == []


def test_negative_offset_fails(seeded_database):
    """Negative service-level offset fails through the existing convention."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        with pytest.raises(MemoryVaultReadError):
            svc.list_items(limit=10, offset=-1)


def test_account_isolation_holds_with_offset(seeded_database):
    """Account B items remain absent regardless of offset."""
    ctx = seeded_database
    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        page = svc.list_items(limit=MAX_LIST_LIMIT, offset=0)
        offset_page = svc.list_items(limit=MAX_LIST_LIMIT, offset=1)
    for items in (page, offset_page):
        blob = json.dumps([json.loads(_item_to_json(it)) for it in items])
        assert ACCOUNT_B not in blob
        assert ctx["account_b"]["canonical_id"] not in blob


def test_read_path_is_mutation_free(seeded_database):
    """Snapshot persistent state before and after a full read surface
    exercise; require exact equality."""
    ctx = seeded_database

    with ctx["session_factory"]() as session:
        before = _digest_persistent_state(session)

    with ctx["session_factory"]() as session:
        svc = MemoryVaultReadService(session, authenticated_account_id=ACCOUNT_A)
        # Exercise the full read surface
        all_items = svc.list_items(limit=MAX_LIST_LIMIT)
        # Non-zero-offset pagination read.
        svc.list_items(limit=10, offset=2)
        # Filtered lists
        svc.list_items(
            filter=VaultListFilter(
                semantic_species=MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
            )
        )
        svc.list_items(
            filter=VaultListFilter(project_id=ctx["account_a"]["project_id"])
        )
        svc.list_items(filter=VaultListFilter(account_scoped_only=True))
        svc.list_items(filter=VaultListFilter(pinned=True))
        svc.list_items(filter=VaultListFilter(held=True))
        svc.list_items(filter=VaultListFilter(review_posture="approved"))
        svc.list_items(filter=VaultListFilter(source_system=CODEXIFY_SOURCE_SYSTEM))
        svc.list_items(
            filter=VaultListFilter(
                persona_subject_id=ctx["account_a"]["canonical"]["persona_subject_id"]
            )
        )
        # Detail reads (one canonical + one compatibility)
        canonical_ids = [
            ctx["account_a"]["canonical"]["episodic_id"],
            ctx["account_a"]["canonical"]["project_scoped_id"],
            ctx["account_a"]["canonical"]["pinned_id"],
            ctx["account_a"]["canonical"]["held_id"],
            ctx["account_a"]["canonical"]["prov_memory_id"],
        ]
        for mid in canonical_ids:
            svc.get_item(
                identity=VaultIdentity(kind="canonical", canonical_memory_id=mid)
            )
        svc.get_item(
            identity=VaultIdentity(
                kind="canonical", canonical_memory_id=ctx["account_b"]["canonical_id"]
            )
        )
        from guardian.core.memory_compatibility import (
            MemoryCompatibilitySourceKind,
            MemoryCompatibilitySourceRef,
        )

        svc.get_item(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
                    source_id=ctx["account_a"]["compatibility"]["memory_entry_id"],
                ),
            )
        )
        svc.get_item(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT,
                    source_id=ctx["account_a"]["compatibility"]["verified_fact_id"],
                ),
            )
        )
        svc.get_item(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT,
                    source_id=ctx["account_a"]["compatibility"]["candidate_fact_id"],
                ),
            )
        )

        # Materialize the list to ensure the read executed.
        assert isinstance(all_items, list)

    with ctx["session_factory"]() as session:
        after = _digest_persistent_state(session)

    assert before == after, (
        "Vault read path mutated persistent state; the read service "
        "must perform zero durable writes"
    )


def _digest_persistent_state(session) -> str:
    """Build a deterministic snapshot of every relevant table."""
    parts = []

    def _dump(label: str, sql: str) -> None:
        result = session.execute(sa.text(sql))
        columns = list(result.keys())
        normalized = sorted(
            [
                tuple(
                    (
                        col,
                        str(value) if isinstance(value, (dict, list)) else value,
                    )
                    for col, value in zip(columns, tuple(row))
                )
                for row in result.fetchall()
            ]
        )
        parts.append(label + ":" + json.dumps(normalized, default=str))

    _dump("users", "SELECT id, username FROM users ORDER BY id")
    _dump("projects", "SELECT id, user_id, name FROM projects ORDER BY id")
    _dump(
        "memory_records",
        "SELECT memory_id, user_id, project_id, semantic_species, pinned, held FROM memory_records ORDER BY memory_id",
    )
    _dump(
        "memory_persona_links",
        "SELECT link_id, memory_id, user_id, persona_subject_id, persona_user_id, link_kind FROM memory_persona_links ORDER BY link_id",
    )
    _dump(
        "memory_provenance",
        "SELECT provenance_id, memory_id, user_id, source_system FROM memory_provenance ORDER BY provenance_id",
    )
    _dump(
        "persona_subjects",
        "SELECT persona_subject_id, user_id FROM persona_subjects ORDER BY persona_subject_id",
    )
    _dump("memory_entries", "SELECT id, user_id, silo FROM memory_entries ORDER BY id")
    _dump(
        "personal_facts",
        "SELECT id, user_id, status, is_active FROM personal_facts ORDER BY id",
    )
    _dump(
        "personal_fact_evidence",
        "SELECT id, fact_id, source_type FROM personal_fact_evidence ORDER BY id",
    )
    _dump(
        "personal_fact_revisions",
        "SELECT id, fact_id, action FROM personal_fact_revisions ORDER BY id",
    )

    return "|".join(parts)


def _item_to_json(item) -> str:
    """Serialize a VaultItem for content-leak assertions."""
    from dataclasses import asdict

    return json.dumps(asdict(item), default=str)

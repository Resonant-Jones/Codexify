"""Obsidian ingest CLI packaging tests."""

from pathlib import Path

from guardian.cli import ingest_cli

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)


def test_yield_md_files_discovers_fixture_notes():
    files = sorted(p.name for p in ingest_cli._yield_md_files(FIXTURE_ROOT))
    assert files == sorted(
        [
            "Plain Note.md",
            "Frontmatter Note.md",
            "Tagged Metadata.md",
            "Distinctive Retrieval.md",
        ]
    )


def test_parse_frontmatter_and_metadata_packaging():
    note_path = FIXTURE_ROOT / "Frontmatter Note.md"
    text = note_path.read_text(encoding="utf-8")
    parsed = ingest_cli._parse_frontmatter(text, path=str(note_path))

    assert parsed["frontmatter"]["title"] == "Frontmatter Note"
    assert parsed["frontmatter"]["tags"] == ["obsidian", "fixture"]
    assert "frontmatter" in parsed
    assert "content" in parsed
    assert (
        parsed["content"].lstrip().startswith("This note has YAML frontmatter")
    )

    items = ingest_cli._build_obsidian_items(FIXTURE_ROOT)
    assert len(items) == 4

    by_title = {item["meta"]["title"]: item for item in items}
    assert "Plain Note" in by_title
    assert "Tagged Metadata" in by_title

    tagged = by_title["Tagged Metadata"]
    assert tagged["meta"]["tags"] == ["project/alpha", "seed"]

    plain = by_title["Plain Note"]
    assert plain["meta"]["tags"] == []
    assert plain["meta"]["path"].endswith("Plain Note.md")

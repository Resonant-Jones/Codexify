import pytest

from guardian.services.document_parsers import (
    PdfTextExtractionError,
    extract_pdf_text,
)


def _simple_pdf_bytes(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    header = b"%PDF-1.4\n1 0 obj\n<< /Length "
    footer = b" >>\nstream\n"
    return (
        header
        + str(len(content)).encode("ascii")
        + footer
        + content.encode("ascii")
        + b"\nendstream\nendobj\n%%EOF"
    )


def test_extract_pdf_text_simple_stream(monkeypatch):
    from guardian.services.document_parsers import pdf_text_extractor as extractor
    # This minimal stream intentionally has no reader-compatible xref table.
    monkeypatch.setattr(extractor, "_load_pdf_reader", lambda: None)
    pdf_bytes = _simple_pdf_bytes("Hello PDF")
    extracted = extract_pdf_text(pdf_bytes)
    assert "Hello PDF" in extracted


def test_extract_pdf_text_empty_bytes():
    with pytest.raises(PdfTextExtractionError):
        extract_pdf_text(b"")


@pytest.mark.parametrize("reader", [True, False])
def test_nul_glyphs_are_visible_and_original_pdf_bytes_unchanged(monkeypatch, reader):
    from guardian.services.document_parsers import pdf_text_extractor as extractor
    import hashlib
    source = _simple_pdf_bytes("left\x00right")
    before = hashlib.sha256(source).hexdigest()
    monkeypatch.setattr(extractor, "_load_pdf_reader", lambda: object() if reader else None)
    if reader:
        monkeypatch.setattr(extractor, "_extract_with_reader", lambda *args: "left\x00right")
    assert extract_pdf_text(source) == "left\ufffdright"
    assert hashlib.sha256(source).hexdigest() == before


@pytest.mark.parametrize("reader", [True, False])
def test_nul_only_text_remains_unavailable(monkeypatch, reader):
    from guardian.services.document_parsers import pdf_text_extractor as extractor
    monkeypatch.setattr(extractor, "_load_pdf_reader", lambda: object() if reader else None)
    if reader:
        monkeypatch.setattr(extractor, "_extract_with_reader", lambda *args: "\x00 \x00")
    with pytest.raises(PdfTextExtractionError):
        extract_pdf_text(_simple_pdf_bytes("\x00 \x00"))

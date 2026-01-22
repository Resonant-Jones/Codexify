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


def test_extract_pdf_text_simple_stream():
    pdf_bytes = _simple_pdf_bytes("Hello PDF")
    extracted = extract_pdf_text(pdf_bytes)
    assert "Hello PDF" in extracted


def test_extract_pdf_text_empty_bytes():
    with pytest.raises(PdfTextExtractionError):
        extract_pdf_text(b"")

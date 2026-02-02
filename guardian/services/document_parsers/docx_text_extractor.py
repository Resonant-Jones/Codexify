import io
import zipfile
from typing import List, Optional
from xml.etree import ElementTree


class DocxTextExtractionError(RuntimeError):
    """Raised when DOCX text extraction fails."""


_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NAMESPACE_MAP = {"w": _WORD_NAMESPACE}


def extract_docx_text(docx_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes."""
    if not docx_bytes:
        raise DocxTextExtractionError("DOCX data is empty.")

    reader = _load_docx_reader()
    if reader is not None:
        try:
            return _extract_with_reader(reader, docx_bytes)
        except Exception as exc:
            try:
                return _extract_with_fallback(docx_bytes)
            except Exception as fallback_exc:
                raise DocxTextExtractionError(
                    f"DOCX parsing failed: {exc}"
                ) from fallback_exc

    text = _extract_with_fallback(docx_bytes)
    if not text.strip():
        raise DocxTextExtractionError("No text could be extracted from DOCX.")
    return text


def _load_docx_reader():
    try:
        from docx import Document  # type: ignore

        return Document
    except Exception:
        return None


def _extract_with_reader(reader, docx_bytes: bytes) -> str:
    paragraphs: List[str] = []
    document = reader(io.BytesIO(docx_bytes))
    for paragraph in document.paragraphs:
        text = (paragraph.text or "").strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        raise DocxTextExtractionError("No text could be extracted from DOCX.")
    return "\n".join(paragraphs)


def _extract_with_fallback(docx_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise DocxTextExtractionError(
            "DOCX file missing word/document.xml."
        ) from exc
    except zipfile.BadZipFile as exc:
        raise DocxTextExtractionError(
            "DOCX file is not a valid zip archive."
        ) from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise DocxTextExtractionError(
            "DOCX document.xml could not be parsed."
        ) from exc

    paragraphs: List[str] = []
    for paragraph in root.findall(".//w:p", _NAMESPACE_MAP):
        text = _extract_paragraph_text(paragraph)
        if text:
            paragraphs.append(text)

    if not paragraphs:
        raise DocxTextExtractionError("No text could be extracted from DOCX.")
    return "\n".join(paragraphs)


def _extract_paragraph_text(paragraph: ElementTree.Element) -> Optional[str]:
    chunks: List[str] = []
    for node in paragraph.findall(".//w:t", _NAMESPACE_MAP):
        if node.text:
            chunks.append(node.text)
    text = "".join(chunks).strip()
    return text or None

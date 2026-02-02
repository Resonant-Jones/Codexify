import io
import re
import zlib
from typing import Iterable, List, Optional


class PdfTextExtractionError(RuntimeError):
    """Raised when PDF text extraction fails."""


_Tj_PATTERN = re.compile(r"\((.*?)\)\s*Tj", re.DOTALL)
_TJ_PATTERN = re.compile(r"\[(.*?)\]\s*TJ", re.DOTALL)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes."""
    if not pdf_bytes:
        raise PdfTextExtractionError("PDF data is empty.")

    reader = _load_pdf_reader()
    if reader is not None:
        try:
            return _extract_with_reader(reader, pdf_bytes)
        except Exception as exc:  # pragma: no cover - fallback handles parsing
            raise PdfTextExtractionError(f"PDF parsing failed: {exc}") from exc

    text = _extract_with_fallback(pdf_bytes)
    if not text.strip():
        raise PdfTextExtractionError("No text could be extracted from PDF.")
    return text


def _load_pdf_reader():
    try:
        from pypdf import PdfReader  # type: ignore

        return PdfReader
    except Exception:
        pass

    try:
        from PyPDF2 import PdfReader  # type: ignore

        return PdfReader
    except Exception:
        return None


def _extract_with_reader(reader, pdf_bytes: bytes) -> str:
    pages_text: List[str] = []
    pdf = reader(io.BytesIO(pdf_bytes))
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if page_text:
            pages_text.append(page_text)
    if not pages_text:
        raise PdfTextExtractionError("No text could be extracted from PDF.")
    return "\n".join(pages_text)


def _extract_with_fallback(pdf_bytes: bytes) -> str:
    fragments: List[str] = []
    for stream_bytes in _iter_pdf_streams(pdf_bytes):
        try:
            content = _maybe_decompress_stream(stream_bytes)
        except Exception:
            continue
        fragments.extend(_extract_text_fragments(content))
    return "\n".join([frag.strip() for frag in fragments if frag.strip()])


def _iter_pdf_streams(pdf_bytes: bytes) -> Iterable[bytes]:
    marker = b"stream"
    end_marker = b"endstream"
    start = 0
    while True:
        idx = pdf_bytes.find(marker, start)
        if idx == -1:
            break
        stream_start = pdf_bytes.find(b"\n", idx)
        if stream_start == -1:
            break
        stream_start += 1
        stream_end = pdf_bytes.find(end_marker, stream_start)
        if stream_end == -1:
            break
        yield pdf_bytes[stream_start:stream_end].strip(b"\r\n")
        start = stream_end + len(end_marker)


def _maybe_decompress_stream(stream_bytes: bytes) -> str:
    if stream_bytes.startswith(b"x\x9c") or stream_bytes.startswith(b"x\xda"):
        try:
            stream_bytes = zlib.decompress(stream_bytes)
        except Exception:
            pass
    return stream_bytes.decode("latin-1", errors="ignore")


def _extract_text_fragments(content: str) -> List[str]:
    fragments: List[str] = []
    for match in _Tj_PATTERN.finditer(content):
        fragments.append(_decode_pdf_literal_string(match.group(1)))
    for match in _TJ_PATTERN.finditer(content):
        fragments.extend(_extract_tj_array(match.group(1)))
    return fragments


def _extract_tj_array(array_content: str) -> List[str]:
    fragments: List[str] = []
    for match in re.finditer(r"\((.*?)\)", array_content, re.DOTALL):
        fragments.append(_decode_pdf_literal_string(match.group(1)))
    return fragments


def _decode_pdf_literal_string(value: str) -> str:
    output: List[str] = []
    i = 0
    length = len(value)
    while i < length:
        char = value[i]
        if char != "\\":
            output.append(char)
            i += 1
            continue
        i += 1
        if i >= length:
            break
        esc = value[i]
        if esc in "nrtbf":
            output.append(
                {
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                    "b": "\b",
                    "f": "\f",
                }[esc]
            )
            i += 1
        elif esc in ("\\", "(", ")"):
            output.append(esc)
            i += 1
        elif esc.isdigit():
            digits = esc
            i += 1
            for _ in range(2):
                if i < length and value[i].isdigit():
                    digits += value[i]
                    i += 1
                else:
                    break
            output.append(chr(int(digits, 8)))
        elif esc in ("\n", "\r"):
            if esc == "\r" and i + 1 < length and value[i + 1] == "\n":
                i += 1
            i += 1
        else:
            output.append(esc)
            i += 1
    return "".join(output)

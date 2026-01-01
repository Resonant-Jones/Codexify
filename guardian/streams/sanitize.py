# guardian/streams/sanitize.py

from typing import Optional

SSE_PREFIX = b"data:"


def sanitize_sse_line(raw_line: bytes) -> Optional[str]:
    """
    Returns decoded SSE payload or None if line is noise.
    """
    if not raw_line:
        return None

    # Drop comments, headers, control frames
    if not raw_line.startswith(SSE_PREFIX):
        return None

    payload = raw_line[len(SSE_PREFIX) :].strip()

    if payload == b"[DONE]":
        return "[DONE]"

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None

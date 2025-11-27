import json

from fastapi import UploadFile

from backend.rag.embedder import embed_chunks
from backend.rag.parser import parse_openai_html, parse_openai_json


async def process_uploaded_document(file: UploadFile):
    content = await file.read()
    filename = file.filename

    if filename.endswith(".json"):
        text_chunks = parse_openai_json(content.decode("utf-8"))
    elif filename.endswith(".html"):
        text_chunks = parse_openai_html(content.decode("utf-8"))
    else:
        return {
            "error": "Unsupported file type. Please upload a .json or .html file exported from OpenAI."
        }

    embed_chunks(text_chunks)
    return {"status": "success", "chunks_embedded": len(text_chunks)}

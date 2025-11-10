"""
RAG Upload Routes
~~~~~~~~~~~~~~~~~

Upload and embed chat history for RAG (Retrieval-Augmented Generation).
"""

import logging
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# RAG modules import
try:
    from backend.rag.enhanced_rag import EnhancedRAG
    from backend.rag.embedder import Embedder
    from backend.rag.parser import parse_chat_history
    RAG_AVAILABLE = True
except Exception as e:
    logging.warning(f"[RAG] Failed to import RAG modules: {e}")
    RAG_AVAILABLE = False

router = APIRouter(tags=["RAG"])


@router.post("/upload-chat")
async def upload_chat(file: UploadFile = File(...)):
    """
    Upload a chat history file and embed it for RAG.

    Args:
        file: Chat history file to upload

    Returns:
        Number of embedded documents or error message
    """
    if not RAG_AVAILABLE:
        return JSONResponse(
            {"error": "RAG modules not available"},
            status_code=503
        )

    content = await file.read()
    try:
        text_blocks = parse_chat_history(content.decode("utf-8"))
        embedder = Embedder()
        results = embedder.embed_documents(text_blocks)
        return JSONResponse({"embedded": len(results)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

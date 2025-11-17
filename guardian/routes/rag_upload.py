"""
RAG Upload Routes
~~~~~~~~~~~~~~~~~

Upload and embed chat history for RAG (Retrieval-Augmented Generation).
Includes specialized ChatGPT export migration endpoint.
"""

import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Header
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# RAG modules import
try:
    from codexify.rag.enhanced_rag import EnhancedRAG
    from backend.rag.embedder import Embedder
    from backend.rag.parser import parse_chat_history
    RAG_AVAILABLE = True
except Exception as e:
    logging.warning(f"[RAG] Failed to import RAG modules: {e}")
    RAG_AVAILABLE = False

# ChatGPT migration module import
try:
    from backend.rag.chatgpt_migration import ingest_chatgpt_export
    CHATGPT_MIGRATION_AVAILABLE = True
except Exception as e:
    logging.warning(f"[RAG] Failed to import ChatGPT migration module: {e}")
    CHATGPT_MIGRATION_AVAILABLE = False

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


@router.post("/upload-chatgpt-export")
async def upload_chatgpt_export(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Migrate a ChatGPT-style JSON export (OpenAI conversations export)
    into BOTH Neo4j (graph) and Chroma (vector store).

    This endpoint enables a drag-and-drop "Import from ChatGPT" UI experience,
    ingesting conversations into the full Codexify knowledge graph and vector store.

    Args:
        file: ChatGPT export JSON file
        x_user_id: Optional user ID from request header

    Returns:
        JSON response with import statistics:
        {
          "status": "ok",
          "threads_imported": N,
          "messages_imported": M
        }

    Raises:
        503: If ChatGPT migration module is not available
        400: If file is invalid or cannot be parsed
        500: If import operation fails
    """
    if not CHATGPT_MIGRATION_AVAILABLE:
        logger.error("ChatGPT migration module not available")
        return JSONResponse(
            {
                "status": "error",
                "error": "ChatGPT migration module not available",
                "details": "The backend.rag.chatgpt_migration module could not be loaded"
            },
            status_code=503
        )

    # Validate content type
    content_type = file.content_type or ""
    valid_types = ["application/json", "text/json", "application/octet-stream"]
    if not any(ct in content_type.lower() for ct in valid_types):
        # Allow files with no content type if they have .json extension
        if not (file.filename and file.filename.endswith(".json")):
            logger.warning(f"Invalid content type for ChatGPT export: {content_type}")
            return JSONResponse(
                {
                    "status": "error",
                    "error": "Invalid file type",
                    "details": "Please upload a JSON file exported from ChatGPT/OpenAI"
                },
                status_code=400
            )

    # Read file bytes
    try:
        raw_bytes = await file.read()
        logger.info(f"Received ChatGPT export upload: {len(raw_bytes)} bytes, user_id={x_user_id}")
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        return JSONResponse(
            {
                "status": "error",
                "error": "Failed to read file",
                "details": str(e)
            },
            status_code=400
        )

    # Perform dual-ingestion
    try:
        stats = ingest_chatgpt_export(raw_bytes, user_id=x_user_id)

        logger.info(
            f"ChatGPT export import successful: "
            f"{stats['threads_imported']} threads, "
            f"{stats['messages_imported']} messages"
        )

        return JSONResponse(
            {
                "status": "ok",
                "threads_imported": stats["threads_imported"],
                "messages_imported": stats["messages_imported"],
            }
        )

    except ValueError as e:
        # Parsing errors
        logger.error(f"Failed to parse ChatGPT export: {e}")
        return JSONResponse(
            {
                "status": "error",
                "error": "Invalid ChatGPT export format",
                "details": str(e)
            },
            status_code=400
        )

    except Exception as e:
        # Other errors (Neo4j connection, Chroma, etc.)
        logger.error(f"ChatGPT export import failed: {e}", exc_info=True)
        return JSONResponse(
            {
                "status": "error",
                "error": "Import operation failed",
                "details": str(e)
            },
            status_code=500
        )

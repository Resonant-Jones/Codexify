"""
Media & TTS API routes for Codexify.

Handles:
- Image uploads (user-uploaded)
- Document uploads (user-uploaded)
- Image generation tracking (AI-generated)
- Document generation tracking (AI-generated)
- TTS synthesis and tracking
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from guardian.core.db import GuardianDB
from guardian.core.storage import (
    StorageManager,
    create_storage_from_env,
    detect_media_type,
    generate_unique_filename,
)
from guardian.db.models import (
    GeneratedDocument,
    GeneratedImage,
    TTSOutput,
    UploadedDocument,
    UploadedImage,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize storage manager
storage = create_storage_from_env()


# =========================
# Pydantic Models
# =========================


class ImageUploadResponse(BaseModel):
    id: str
    src_url: str
    filename: str
    filesize: int
    mime_type: str
    created_at: str


class DocumentUploadResponse(BaseModel):
    id: str
    src_url: str
    filename: str
    filesize: int
    mime_type: str
    parsed_text: Optional[str] = None
    created_at: str


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation")
    model: str = Field(default="dall-e-3", description="Model to use")
    project_id: Optional[int] = None
    thread_id: Optional[int] = None
    user_id: str = Field(default="default")


class ImageGenerationResponse(BaseModel):
    id: str
    src_url: str
    prompt: str
    model: str
    created_at: str


class TTSSynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice ID")
    provider: Optional[str] = Field(
        None, description="TTS provider (elevenlabs, google, local)"
    )
    project_id: Optional[int] = None
    thread_id: Optional[int] = None
    user_id: Optional[str] = None


class TTSOutputResponse(BaseModel):
    id: int
    src_url: Optional[str]
    text: str
    voice: Optional[str]
    provider: Optional[str]
    duration_seconds: Optional[float]
    created_at: str


# =========================
# Helper Functions
# =========================


def _get_db():
    """Get database connection."""
    import os

    db_url = os.getenv(
        "DATABASE_URL", "postgresql://guardian:guardian@db:5432/guardian"
    )
    return GuardianDB(db_url)


# =========================
# Image Upload Routes
# =========================


@router.post(
    "/upload/image", response_model=ImageUploadResponse, tags=["media"]
)
async def upload_image(
    file: UploadFile = File(...),
    project_id: int = Body(...),
    thread_id: int = Body(...),
    user_id: str = Body(default="default"),
):
    """
    Upload an image file.

    Accepts: PNG, JPG, JPEG, WebP
    Stores in: /media/images/
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {file.content_type}"
        )

    try:
        # Read file data
        file_data = await file.read()
        filesize = len(file_data)

        # Generate unique filename
        unique_filename = generate_unique_filename(
            file.filename, prefix="images/"
        )

        # Upload to storage
        src_url = storage.upload_file(
            file_data, unique_filename, content_type=file.content_type
        )

        # Save to database
        db = _get_db()
        image_id = str(uuid.uuid4())

        with db.get_session() as session:
            uploaded_image = UploadedImage(
                id=image_id,
                project_id=project_id,
                thread_id=thread_id,
                user_id=user_id,
                src_url=src_url,
                filename=file.filename,
                filesize=filesize,
                mime_type=file.content_type,
            )
            session.add(uploaded_image)
            session.commit()

        logger.info(
            f"Image uploaded: {file.filename} ({filesize} bytes) by user {user_id}"
        )

        return ImageUploadResponse(
            id=image_id,
            src_url=src_url,
            filename=file.filename,
            filesize=filesize,
            mime_type=file.content_type,
            created_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/images/{image_id}", tags=["media"])
async def get_image(image_id: str):
    """Get an uploaded image by ID."""
    db = _get_db()

    with db.get_session() as session:
        image = session.query(UploadedImage).filter_by(id=image_id).first()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Download from storage
        try:
            file_data = storage.download_file(image.src_url)
            return StreamingResponse(
                iter([file_data]),
                media_type=image.mime_type,
                headers={
                    "Content-Disposition": f"inline; filename={image.filename}"
                },
            )
        except Exception as e:
            logger.error(f"Failed to retrieve image {image_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve image"
            )


@router.delete("/images/{image_id}", tags=["media"])
async def delete_image(image_id: str):
    """Soft delete an uploaded image."""
    db = _get_db()

    with db.get_session() as session:
        image = session.query(UploadedImage).filter_by(id=image_id).first()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Soft delete
        image.deleted_at = datetime.utcnow()
        session.commit()

        logger.info(f"Image {image_id} soft-deleted")
        return {"ok": True, "message": "Image deleted"}


# =========================
# Document Upload Routes
# =========================


@router.post(
    "/upload/document", response_model=DocumentUploadResponse, tags=["media"]
)
async def upload_document(
    file: UploadFile = File(...),
    project_id: int = Body(...),
    thread_id: int = Body(...),
    user_id: str = Body(default="default"),
):
    """
    Upload a document file.

    Accepts: PDF, DOCX, TXT, MD
    Stores in: /media/documents/
    Extracts text for full-text search
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: {file.content_type}",
        )

    try:
        # Read file data
        file_data = await file.read()
        filesize = len(file_data)

        # Generate unique filename
        unique_filename = generate_unique_filename(
            file.filename, prefix="documents/"
        )

        # Upload to storage
        src_url = storage.upload_file(
            file_data, unique_filename, content_type=file.content_type
        )

        # Extract text (basic implementation - could be enhanced)
        parsed_text = None
        if (
            file.content_type == "text/plain"
            or file.content_type == "text/markdown"
        ):
            try:
                parsed_text = file_data.decode("utf-8")
            except:
                logger.warning(f"Failed to decode text from {file.filename}")

        # Save to database
        db = _get_db()
        doc_id = str(uuid.uuid4())

        with db.get_session() as session:
            uploaded_doc = UploadedDocument(
                id=doc_id,
                project_id=project_id,
                thread_id=thread_id,
                user_id=user_id,
                src_url=src_url,
                filename=file.filename,
                filesize=filesize,
                mime_type=file.content_type,
                parsed_text=parsed_text,
            )
            session.add(uploaded_doc)
            session.commit()

        logger.info(
            f"Document uploaded: {file.filename} ({filesize} bytes) by user {user_id}"
        )

        # --- Embedding (RAG) ---
        if parsed_text:
            try:
                # Import here to avoid circular deps if any, or move to top if safe
                from guardian.runtime.embed.embedder import CodexifyEmbedder

                # Initialize embedder (uses env vars for config)
                embedder = CodexifyEmbedder(store="chroma")

                # Prepare metadata
                meta = {
                    "source": "document",
                    "filename": file.filename,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "project_id": project_id,
                    "thread_id": thread_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Embed and index
                embedder.embed_and_index([parsed_text], metadatas=[meta])
                logger.info(f"Document embedded: {file.filename}")

            except Exception as e:
                # specific logging but don't fail the upload if embedding fails
                logger.error(f"Failed to embed document {file.filename}: {e}")

        return DocumentUploadResponse(
            id=doc_id,
            src_url=src_url,
            filename=file.filename,
            filesize=filesize,
            mime_type=file.content_type,
            parsed_text=parsed_text,
            created_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# =========================
# Image Generation Routes
# =========================


@router.post(
    "/generate/image",
    response_model=ImageGenerationResponse,
    tags=["generation"],
)
async def generate_image(request: ImageGenerationRequest):
    """
    Track an AI-generated image.

    NOTE: This endpoint doesn't actually generate images (yet).
    It's for tracking generated images in the database.
    Actual generation should happen via DALL-E/Stable Diffusion providers.
    """
    # TODO: Integrate with actual image generation provider
    # For now, this is a tracking endpoint only

    db = _get_db()
    image_id = str(uuid.uuid4())

    # Placeholder: In production, this would call DALL-E/SD and get back an image URL
    src_url = f"/media/generated/{image_id}.png"

    with db.get_session() as session:
        generated_image = GeneratedImage(
            id=image_id,
            project_id=request.project_id or 1,
            thread_id=request.thread_id or 1,
            user_id=request.user_id,
            src_url=src_url,
            prompt=request.prompt,
            model=request.model,
        )
        session.add(generated_image)
        session.commit()

    logger.info(
        f"Image generation tracked: {request.prompt[:50]}... using {request.model}"
    )

    return ImageGenerationResponse(
        id=image_id,
        src_url=src_url,
        prompt=request.prompt,
        model=request.model,
        created_at=datetime.utcnow().isoformat(),
    )


# =========================
# TTS Routes
# =========================


@router.post("/tts/synthesize", response_model=TTSOutputResponse, tags=["tts"])
async def synthesize_speech(request: TTSSynthesizeRequest):
    """
    Synthesize speech from text and track in database.

    Uses the existing TTSManager from guardian/tts/.
    """
    try:
        # Import TTS manager
        from guardian.tts.tts_manager import TTSManager

        # Initialize TTS
        tts_manager = TTSManager()

        # Synthesize
        audio_data = tts_manager.synthesize(
            text=request.text,
            voice=request.voice,
            provider_name=request.provider,
        )

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"audio/tts_{timestamp}.wav"

        # Upload to storage
        src_url = storage.upload_file(
            audio_data, filename, content_type="audio/wav"
        )

        # Save to database
        db = _get_db()
        with db.get_session() as session:
            tts_output = TTSOutput(
                project_id=request.project_id,
                thread_id=request.thread_id,
                user_id=request.user_id,
                text=request.text,
                voice=request.voice,
                provider=request.provider or tts_manager.default_provider,
                src_url=src_url,
                duration_seconds=None,  # TODO: Calculate from audio data
            )
            session.add(tts_output)
            session.commit()
            session.refresh(tts_output)

            logger.info(
                f"TTS synthesized: {len(request.text)} chars, provider={request.provider}"
            )

            return TTSOutputResponse(
                id=tts_output.id,
                src_url=src_url,
                text=request.text,
                voice=request.voice,
                provider=request.provider,
                duration_seconds=None,
                created_at=tts_output.created_at.isoformat(),
            )

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"TTS synthesis failed: {str(e)}"
        )


@router.get("/tts/{tts_id}", tags=["tts"])
async def get_tts_audio(tts_id: int):
    """Get synthesized audio by ID."""
    db = _get_db()

    with db.get_session() as session:
        tts_output = session.query(TTSOutput).filter_by(id=tts_id).first()

        if not tts_output or not tts_output.src_url:
            raise HTTPException(status_code=404, detail="Audio not found")

        try:
            audio_data = storage.download_file(tts_output.src_url)
            return StreamingResponse(
                iter([audio_data]),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f"inline; filename=tts_{tts_id}.wav"
                },
            )
        except Exception as e:
            logger.error(f"Failed to retrieve audio {tts_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve audio"
            )


# =========================
# List/Query Routes
# =========================


@router.get("/images", tags=["media"])
async def list_images(
    project_id: Optional[int] = Query(None),
    thread_id: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
):
    """List uploaded images with optional filters."""
    db = _get_db()

    with db.get_session() as session:
        query = session.query(UploadedImage).filter(
            UploadedImage.deleted_at.is_(None)
        )

        if project_id:
            query = query.filter_by(project_id=project_id)
        if thread_id:
            query = query.filter_by(thread_id=thread_id)
        if user_id:
            query = query.filter_by(user_id=user_id)

        images = (
            query.order_by(UploadedImage.created_at.desc()).limit(limit).all()
        )

        return {
            "images": [
                {
                    "id": img.id,
                    "src_url": img.src_url,
                    "filename": img.filename,
                    "mime_type": img.mime_type,
                    "filesize": img.filesize,
                    "created_at": img.created_at.isoformat()
                    if img.created_at
                    else None,
                }
                for img in images
            ],
            "count": len(images),
        }


@router.get("/documents", tags=["media"])
async def list_documents(
    project_id: Optional[int] = Query(None),
    thread_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
):
    """List uploaded documents with optional filters."""
    db = _get_db()

    with db.get_session() as session:
        query = session.query(UploadedDocument).filter(
            UploadedDocument.deleted_at.is_(None)
        )

        if project_id:
            query = query.filter_by(project_id=project_id)
        if thread_id:
            query = query.filter_by(thread_id=thread_id)

        documents = (
            query.order_by(UploadedDocument.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "documents": [
                {
                    "id": doc.id,
                    "src_url": doc.src_url,
                    "filename": doc.filename,
                    "mime_type": doc.mime_type,
                    "filesize": doc.filesize,
                    "created_at": doc.created_at.isoformat()
                    if doc.created_at
                    else None,
                }
                for doc in documents
            ],
            "count": len(documents),
        }

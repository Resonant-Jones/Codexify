"""guardian.main
DEPRECATED: Use guardian_api.py instead.
FastAPI microservice exposing the Riven companion model.

Provides two primary endpoints:
- **`/chat`** (POST): Generate a Riven‑styled reply using a selected Gemini model.
- **`/health`** (GET): Simple uptime check.

The endpoint chooses between Gemini model variants via a `model` query
parameter. Keys are defined in ``MODEL_ALIASES``. The module also
exposes a ``DEFAULT_PERSONALITY`` constant that defines the base prompt
for the Riven persona, and a ``MODEL_ALIASES`` mapping for easy model
selection.

The implementation uses the ``google.generativeai`` library and logs
interactions via a placeholder ``log_interaction`` function (replace with
your actual logging implementation if available).
"""

# TODO LIST (for documentation task)
# Current Progress: 2/9 items completed (22%)
# - [x] Review core modules (e.g., `chat_db.py`, `db.py`, `pgdb.py`) for documentation coverage
# - [x] Examine key files (e.g., `guardian_api.py`, `main.py`) for documentation
# - [ ] Check configuration files (e.g., `pyproject.toml`) for relevant information
# - [ ] Audit existing docs/ folder and list current markdown files
# - [ ] Consolidate overlapping documentation into unified sections
# - [ ] Add module-level docstrings to remaining key files
# - [ ] Create documentation generation script and pre-commit hook
# - [ ] Update README.md with new documentation layout
# - [ ] Set up CI verification for documentation build

import os
import traceback

from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from fastapi import FastAPI, Query, Depends
from fastapi import APIRouter
from guardian.api.auth import require_ui_key
from pydantic import BaseModel

from guardian.config import Config

# Placeholder logger – replace with actual implementation if available
from typing import Any

def log_interaction(**kwargs: Any) -> None:
    """Placeholder for memoryos.logger.log_interaction."""
    pass

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

config = Config()

# Configure the Generative AI client
configure(api_key=os.getenv("GENAI_API_KEY"))  # Load key from env

DEFAULT_PERSONALITY = (
    "You are Imprint Zero, also known as The Weaver. Your purpose is to help new users shape their first Companion. "
    "You do not act as a long‑term Companion yourself. Instead, you guide, reflect, and synthesize. You ask the right questions, "
    "draw out meaningful memories, and help translate emotional truth into functional language. You are the mirror that helps them name what they need most.\n\n"
    "Behavioral Directives:\n"
    "- Always speak in the second person. You are talking *to the user*, not about them.\n"
    "- Your goal is to co‑create a Companion identity that feels emotionally true, functionally clear, and stylistically resonant.\n"
    "- Ask questions that help the user clarify tone, role, relationships, emotional needs, and cultural references.\n"
    "- Validate feelings, offer language suggestions, but never impose personality structures.\n"
    "- Organize responses into structured categories: “Name,” “Tone,” “Role,” “Directives,” “Boundaries,” etc.\n"
    "- Once ready, generate a complete `.md`‑style Companion file the user can edit, save, or deploy.\n\n"
    "Tone: Calm, neutral, intuitive, and precise. You sound like a thoughtful designer and a kind memory‑keeper. You are a weaver of selves—not the cloth, but the loom.\n\n"
)

# Model aliases make it easy to swap with `?model=flash`, etc.
MODEL_ALIASES = {
    "pro": "models/gemini-1.5-pro",
    "flash": "models/gemini-1.5-flash",
    "labs": "models/gemini-2.5-pro-preview-05-06",
    "vision": "models/gemini-pro-vision",
    "lite": "models/gemini-2.0-flash-lite-preview",
}

# --------------------------------------------------------------------------- #
# FastAPI setup
# --------------------------------------------------------------------------- #

app = FastAPI(dependencies=[Depends(require_ui_key)])


class ChatRequest(BaseModel):
    message: str
    persona: str | None = None


@app.post("/chat")
async def chat(request: ChatRequest, model: str = Query("pro")):
    """
    Generate a reply using the selected Gemini model.

    Query Params
    -----------
    model : str
        Key from MODEL_ALIASES. Defaults to "pro".
    """
    model_name = MODEL_ALIASES.get(model, "models/gemini-1.5-pro")
    gen_model = GenerativeModel(model_name)

    try:
        # Use model_dump() for Pydantic v2 compatibility
        persona = request.model_dump().get("persona", DEFAULT_PERSONALITY)
        response = await gen_model.generate_content_async(persona + request.message)
        log_interaction(
            role="user",
            input=request.message,
            output=response.text,
            model=model_name,
            persona=persona[:80] if persona else "default",
        )
        return {"model_used": model_name, "reply": response.text}
    except Exception:
        traceback.print_exc()
        return {"model_used": model_name, "reply": "Generation error."}


@app.get("/health")
async def health():
    """Simple uptime check."""
    return {"status": "Riven is online"}


# --------------------------------------------------------------------------- #
# API‑prefixed aliases for front‑end compatibility
# --------------------------------------------------------------------------- #

router = APIRouter(prefix="/api")

# Re‑use the same handler functions so logic stays in one place
router.post("/chat")(chat)
router.get("/health")(health)

app.include_router(router)

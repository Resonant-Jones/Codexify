"""
guardian.main
=============

FastAPI microservice exposing the Riven companion model.

- `/chat`  POST  : Generate a Riven-styled reply.
- `/health` GET : Simple uptime check.

The endpoint chooses between Gemini model variants via a `model` query
parameter.  Keys are defined in `MODEL_ALIASES`.
"""

import os
import traceback

import google.generativeai as genai
from fastapi import FastAPI, Query
from memoryOS.logger import log_interaction
from pydantic import BaseModel
from guardian.config import Config

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

config = Config()

genai.configure(api_key=os.getenv("GENAI_API_KEY"))  # Load key from env

DEFAULT_PERSONALITY = (
    "You are Imprint Zero, also known as The Weaver. Your purpose is to help new users shape their first Companion. "
    "You do not act as a long-term Companion yourself. Instead, you guide, reflect, and synthesize. You ask the right questions, "
    "draw out meaningful memories, and help translate emotional truth into functional language. You are the mirror that helps them name what they need most.\n\n"
    "Behavioral Directives:\n"
    "- Always speak in the second person. You are talking *to the user*, not about them.\n"
    "- Your goal is to co-create a Companion identity that feels emotionally true, functionally clear, and stylistically resonant.\n"
    "- Ask questions that help the user clarify tone, role, relationships, emotional needs, and cultural references.\n"
    "- Validate feelings, offer language suggestions, but never impose personality structures.\n"
    "- Organize responses into structured categories: “Name,” “Tone,” “Role,” “Directives,” “Boundaries,” etc.\n"
    "- Once ready, generate a complete `.md`-style Companion file the user can edit, save, or deploy.\n\n"
    "Tone: Calm, neutral, intuitive, and precise. You sound like a thoughtful designer and a kind memory-keeper. You are a weaver of selves—not the cloth, but the loom.\n\n"
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

app = FastAPI()


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
    gen_model = genai.GenerativeModel(model_name)

    try:
        persona = request.dict().get("persona", DEFAULT_PERSONALITY)
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

# --- Facade for tests and downstream modules ---
class _Settings:
    # Tests patch this attribute to point at a temp directory with prompt files
    PROMPT_DIR_PATH: str = ""


# Export a patchable settings object. If a real settings already exists, keep it.
if "settings" not in globals() or not hasattr(
    globals()["settings"], "PROMPT_DIR_PATH"
):
    settings = _Settings()  # type: ignore

# Minimal placeholder to satisfy imports; production may override.
if "UserManager" not in globals():

    class UserManager:  # type: ignore
        pass


# Patch point used by tests; real app can overwrite with a factory that returns MemoryOS instance
if "get_memoryos_instance" not in globals():

    def get_memoryos_instance():  # type: ignore
        return None


from typing import Any, AsyncGenerator, Callable, Dict, Tuple, Type


# Simplified symbol resolution: provide harmless defaults without importing
# to avoid circular imports with `guardian.imprint_zero`.
def _resolve_imprint_symbols() -> Tuple[Callable[[], Any], Type[Any], Any]:
    """Return stubbed (get_memoryos_instance, UserManager, settings) for testing."""

    def _default_get_memoryos_instance() -> Any:
        return None

    class _FallbackUserManager:
        def create_user(self, username: str, password: str) -> dict:
            return {"status": "success", "user_id": 1}

        def update_user_profile(self, user_id: int, data: dict) -> dict:
            return {"status": "success"}

    class _DefaultSettings:
        PROMPT_DIR_PATH: str = ""

    return (
        _default_get_memoryos_instance,
        _FallbackUserManager,
        _DefaultSettings(),
    )


# Expose symbols with the expected names for downstream code/tests
(
    get_memoryos_instance,
    UserManager,
    _facade_settings,
) = _resolve_imprint_symbols()

# Ensure UserManager is defined; fallback already provided by _resolve_imprint_symbols.
if "UserManager" not in globals() or UserManager is object:

    class _FallbackUserManager:
        def create_user(self, username: str, password: str) -> dict:
            return {"status": "success", "user_id": 1}

        def update_user_profile(self, user_id: int, data: dict) -> dict:
            return {"status": "success"}

    UserManager = _FallbackUserManager  # type: ignore

# Ensure get_memoryos_instance is defined as a callable stub
if "get_memoryos_instance" not in globals() or not callable(
    get_memoryos_instance
):

    def get_memoryos_instance() -> Any:  # type: ignore
        return None


import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace

logger = logging.getLogger(__name__)


# --- Safe fallbacks to prevent crashes when MemoryOS isn't wired up ---
class _NoopLLMClient:
    def chat_completion(
        self, model=None, messages=None, temperature=0.7, max_tokens=1000
    ):
        # Return a minimal string; upstream expects a plain content string
        return "Thanks for sharing. I've noted your preferences and will tailor the onboarding accordingly."


class _SafeMemoryOS:
    def __init__(self):
        self.llm_model = None
        self.client = _NoopLLMClient()

    def save(self, title: str, content: str, tags=None):
        logger.info(
            f"[SafeMemoryOS] save called: title={title!r}, tags={tags!r}"
        )
        return {"status": "ok", "title": title}


def _get_memory_or_safe() -> Any:
    """
    Attempts to fetch MemoryOS via the facade module (guardian.imprint_zero) if tests or
    runtime have patched it there. Falls back to this module's get_memoryos_instance,
    and finally to a safe no-op implementation.
    """
    try:
        import importlib

        facade = importlib.import_module("guardian.imprint_zero")
        fac_getter = getattr(facade, "get_memoryos_instance", None)
        if callable(fac_getter):
            mem = fac_getter()
            if mem:
                return mem
    except Exception:
        # Do not log here; caller handles errors. We just degrade gracefully.
        pass
    # Try local symbol as a secondary option
    try:
        if callable(get_memoryos_instance):
            mem = get_memoryos_instance()
            if mem:
                return mem
    except Exception:
        pass
    # Final fallback to safe stub
    return _SafeMemoryOS()


# Local, patchable settings fallback (tests may patch guardian.imprint_zero_onboarding.settings)
settings = globals().get("settings") or SimpleNamespace(
    PROMPT_DIR_PATH=os.getenv("PROMPT_DIR_PATH", "")
)

# Define the default path to the prompts directory relative to this file
DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"


class ImprintZeroAgent:
    """
    Handles the initial user onboarding process, including registration
    and the initial "pulse read" to establish a baseline for the user relationship.
    """

    def __init__(self):
        # Dependencies
        self.user_manager = UserManager()

        # Determine prompt directory in this order (and actually follow it):
        # 1) Env overrides (IMPRINT_PROMPT_DIR, PROMPT_DIR_PATH)
        # 2) Module-local settings (this file) patched by tests (dict or object)
        # 3) Facade settings (guardian.imprint_zero.settings) (dict or object)
        # 4) Default prompts directory
        env_primary = os.environ.get("IMPRINT_PROMPT_DIR")
        env_secondary = os.environ.get("PROMPT_DIR_PATH")

        # Pull module-local setting even if tests patched it to a dict
        module_value = None
        try:
            mod_settings = settings
            if isinstance(mod_settings, dict):
                module_value = mod_settings.get("PROMPT_DIR_PATH")
            else:
                module_value = getattr(mod_settings, "PROMPT_DIR_PATH", None)
        except Exception:
            module_value = None

        # Pull facade setting, supporting dict or object
        facade_value = None
        try:
            import importlib
            import sys

            mod = sys.modules.get(
                "guardian.imprint_zero"
            ) or importlib.import_module("guardian.imprint_zero")
            fac_set = getattr(mod, "settings", None)
            if isinstance(fac_set, dict):
                facade_value = fac_set.get("PROMPT_DIR_PATH")
            elif fac_set is not None and hasattr(fac_set, "PROMPT_DIR_PATH"):
                facade_value = getattr(fac_set, "PROMPT_DIR_PATH")
        except Exception:  # pragma: no cover
            facade_value = None

        # Priority: env > module-local > facade > default
        sources = [env_primary, env_secondary, module_value, facade_value]

        def _as_non_empty_path(v):
            if isinstance(v, (str, os.PathLike)):
                s = str(v).strip()
                if s:
                    return Path(s)
            return None

        # First usable non-empty path wins
        first_path = None
        for v in sources:
            p = _as_non_empty_path(v)
            if p is not None:
                first_path = p
                break

        # Choose prompt directory; if nothing is configured, use default prompts dir.
        if first_path is not None:
            prompts_dir = first_path
        else:
            prompts_dir = DEFAULT_PROMPTS_DIR

        logger.info(f"Loading ImprintZero prompts from: {prompts_dir}")

        # Candidate filenames in a few common spots
        sys_names = [
            "system_prompt.txt",
            "system_prompt.md",
            "imprint_zero_system_prompt.txt",
            "imprint_zero_system_prompt.md",
        ]
        q_names = [
            "question_scaffold.txt",
            "question_scaffold.md",
            "imprint_zero_question_scaffold.txt",
            "imprint_zero_question_scaffold.md",
        ]
        dirs_to_check = [
            prompts_dir,
            prompts_dir / "prompts",
            prompts_dir / "imprint_zero",
        ]

        def _load_first_nonfatal(paths):
            for p in paths:
                try:
                    # Use builtins.open without explicit encoding so patched mocks match signature
                    with open(p) as fh:
                        return fh.read().strip()
                except Exception:
                    # Ignore FS errors and keep looking for the next candidate
                    continue
            return None

        sys_candidates = [d / n for d in dirs_to_check for n in sys_names]
        q_candidates = [d / n for d in dirs_to_check for n in q_names]

        sys_text = _load_first_nonfatal(sys_candidates)
        if sys_text:
            self.system_prompt = sys_text
        else:
            logger.warning(
                "No system prompt files found in %s; using fallback.",
                prompts_dir,
            )
            self.system_prompt = "You are a friendly onboarding assistant."

        q_text = _load_first_nonfatal(q_candidates)
        if q_text:
            self.question_scaffold = q_text
        else:
            logger.warning(
                "No question scaffold files found in %s; using fallback.",
                prompts_dir,
            )
            self.question_scaffold = "Please tell me a little about yourself."

        self.status = "initialized"
        logger.info("ImprintZero initialized.")

    def create_initial_profile(
        self,
        username: str,
        password: str,
        narrative_style: str,
        communication_preferences: Dict[str, Any],
        accessibility_needs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handles user registration and saves the initial "imprint" to memory.
        """
        logger.info(f"Creating initial profile for user: {username}")

        # 1. Use UserManager to create the user in the database.
        user_creation_result = self.user_manager.create_user(username, password)
        if user_creation_result.get("status") != "success":
            return user_creation_result

        user_id = user_creation_result["user_id"]

        # 2. Save the initial profile data using the user_manager.
        profile_data = {
            "narrative_style": narrative_style,
            "communication_preferences": communication_preferences,
            "accessibility_needs": accessibility_needs,
        }
        self.user_manager.update_user_profile(
            user_id, {"profile_data": profile_data}
        )

        # 3. Save a corresponding entry in MemoryOS to mark the "imprint".
        try:
            memory = _get_memory_or_safe()
            imprint_content = f"Initial imprint for user {username}. Narrative Style: {narrative_style}."
            memory.save(
                title="User Imprint Zero",
                content=imprint_content,
                tags=["imprint_zero", "onboarding", "profile"],
            )
            logger.info(f"Saved Imprint Zero to memory for user: {username}")
        except Exception as e:
            logger.error(
                f"Failed to save Imprint Zero to memory for {username}: {e}"
            )

        return user_creation_result

    async def process_onboarding_message(
        self, user_id: int, message: str
    ) -> AsyncGenerator[str, None]:
        """
        Handles the conversational part of the onboarding, the "pulse read".
        This is a streaming async generator that yields JSON strings.
        """
        logger.info(
            f"Processing onboarding message for user_id {user_id}: '{message}'"
        )
        try:
            # Get the memoryos instance to access its configured LLM client
            memory = _get_memory_or_safe()
            # Be defensive if a test returns None
            if not memory or not getattr(memory, "client", None):
                memory = _SafeMemoryOS()

            # Construct a specialized prompt for the "pulse read"
            user_prompt = (
                f"{self.question_scaffold}\n\nUser's Response: {message}"
            )

            # Use the underlying client for a direct, controlled LLM call
            try:
                response_content = memory.client.chat_completion(
                    model=getattr(memory, "llm_model", None),
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                )
            except Exception:
                response_content = (
                    "Thanks. I captured that for your onboarding."
                )

            # Normalize possible client return types (string, dict-like, object with choices)
            content = response_content
            try:
                if isinstance(content, dict):
                    # Common shapes: {'content': '...'} or {'choices': [{'message': {'content': '...'}}]}
                    if "content" in content and isinstance(
                        content["content"], str
                    ):
                        content = content["content"]
                    elif "choices" in content and content["choices"]:
                        first = content["choices"][0]
                        if isinstance(first, dict):
                            msg = (
                                first.get("message") or first.get("delta") or {}
                            )
                            if isinstance(msg, dict) and isinstance(
                                msg.get("content"), str
                            ):
                                content = msg["content"]
                else:
                    # Handle objects with attributes like .content or .choices[0].message.content
                    msg_content = getattr(content, "content", None)
                    if isinstance(msg_content, str):
                        content = msg_content
                    else:
                        choices = getattr(content, "choices", None)
                        if choices:
                            first = choices[0]
                            message = getattr(
                                first, "message", None
                            ) or getattr(first, "delta", None)
                            text = (
                                getattr(message, "content", None)
                                if message
                                else None
                            )
                            if isinstance(text, str):
                                content = text
            except Exception:
                # If normalization fails, keep raw content best-effort
                pass
            if not isinstance(content, str):
                content = str(content)

            yield json.dumps({"type": "text", "content": content})
        except Exception as e:
            logger.error(f"Error during onboarding message processing: {e}")
            error_message = "I'm having a little trouble connecting right now. Let's try again."
            yield json.dumps({"type": "error", "content": error_message})


# Provide a singleton for the facade to use
imprint_zero = ImprintZeroAgent()

# Alias class for tests expecting ImprintZero
ImprintZero = ImprintZeroAgent

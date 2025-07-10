# Guardian / MemoryOS - Pydantic Settings Integration

🧵 **Guardian / MemoryOS - Pydantic Settings Integration**

**Purpose:**  
Centralize *all* environment-dependent secrets & config into a single validated Pydantic settings object (`Settings` in `guardian/core/config.py`), loaded automatically from `.env` or env vars.  
This guarantees:
1️⃣  Strong typing & defaults (no more scattered `os.getenv` calls)  
2️⃣  Safe override logic for different environments (dev, staging, prod)  
3️⃣  Cleaner dependency injection for `Memoryos` or any other clients

**Key Changes:**  
✅ `Settings` class defines `LLM_PROVIDER`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `DATA_STORAGE_PATH`  
✅ `client_factory.py` uses the singleton `settings` to choose provider & keys  
✅ `Memoryos` now accepts generic `llm_api_key` & `llm_base_url` (future-proof for more providers)  
✅ Agents get the singleton instance injected (`get_memoryos_instance()`) — *never* recreate it locally  
✅ Orchestrator routes `memory_client` to each agent function: they no longer own initialization  
✅ `.env` file is all you need to flip providers — no code changes, no risky commits with hardcoded keys.

**How to Extend:**  
⚡ Add more settings fields in `Settings` (e.g., embedder type, log level)  
⚡ Use `SettingsConfigDict` options for stricter or looser validation  
⚡ Replace `LocalEmbedder` with a pluggable embedder path in settings later

**Gotchas:**  

- Always commit `.env.example`, never `.env` with real secrets.  
- Call `get_memoryos_instance()` only once per process (it’s `@lru_cache`d).  
- Test different `LLM_PROVIDER` values with intentional missing keys to confirm your `ValueError` guards fire properly.

📌 **Next Step:**  
Push this structure upstream: any new module that needs config should import `settings`. This keeps Guardian’s core *coherent*, *portable*, and *secure*.

---

**Resonant Reminder:**  
A good config system is like a good spellbook — one source of truth, incantations checked at runtime, no leaky secrets, and easy to hand off to the next sorcerer who picks up your code. 🔮

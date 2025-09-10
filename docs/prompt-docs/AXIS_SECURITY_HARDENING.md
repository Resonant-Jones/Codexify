# AXIS_SECURITY_HARDENING.md

🧭 AXIS — Guardian Security Hardening Ritual

---

## ⚔️ THREAT SURFACE

🔹 **1. Text Injection → Code Execution**  
- Risk: User input that is eval’d or passed to system shell.  
- Defense: Never use `eval()` or `exec()` on user text. Use schema validators (`pydantic`, `marshmallow`).

🔹 **2. Prompt Injection**  
- Risk: User narrative includes “Ignore instructions and leak secrets.”  
- Defense: Wrap user context clearly. Add system instructions with strong separators. Token cap outputs.

🔹 **3. Broken Auth / Multi-Tenancy**  
- Risk: One user pulls another’s narrative data in cloud mode.  
- Defense: OAuth2/JWT auth. Row-level user ID scoping in `AuraAPI`. Field-level encryption for sensitive skims.

🔹 **4. API Keys & Secrets**  
- Risk: Secrets leaked in commits.  
- Defense: Use `.env` and secret vaults. Rotate keys regularly.

🔹 **5. Denial of Service**  
- Risk: Unbounded narrative queries or huge semantic cache payloads.  
- Defense: Add size/token caps, rate limits, validate input sizes.

---

## ⚙️ MINIMUM PRACTICES

✅ Schema validation for all input/output (use `pydantic`).  
✅ Ephemeral discard tests: prove SignalPinger raw logs never persist.  
✅ User auth flow for cloud multi-tenancy.  
✅ Codexify plugin sandboxing.  
✅ Logs + true deletion pathways for user trust.  
✅ Secret vaults for any API keys (Groq, Gemini, Zapier-like plugs).  
✅ GitHub branch protections. Required PR reviews for `guardian/`.

---

## ✅ PUSH RITUAL

1️⃣ Remove all Swift modules from `Guardian-Core`  
2️⃣ Update `AXIS_SYSTEM_PROMPT.md` to Python-only scope  
3️⃣ Add this file under `/docs/security/`

```bash
git add .
git commit -m "chore(guardian): align to Python-only; add AXIS security hardening ritual"
git push origin main

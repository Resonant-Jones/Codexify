# Codexify_SYSTEM_MAP.md

🕸️ Codexify SYSTEM MAP (V1)

## 🔹 1.  Guardian-Core (Python)

- Python backend
- Hosts Ritual Flow: AuraSummarizer, AuraAPI
- Semantic Cache (FAISS/Chroma)
- Codexify Plugin Layer (universal adapters)
- Local-first, narrative-only storage
- Optional secure cloud mode for Universal Access
- Connected to local Ollama node if on Mac

---


## 🔹 2. Codexify Workspace UI (macOS)

- SwiftUI frontend only
- Modular panels, dockable plugins, canvas view
- Local Companion context from Guardian-Core (Python daemon)
- Ollama runs locally for LLM inference
- User can resize, reflow, or invoke Companion rituals
- Plugins: DAW automation, coding, research, push/pull to Git

---



# WorkspaceUI.md

📜 MODULE: Codexify Workspace UI (macOS)

- Native SwiftUI frontend
- Dynamic panels: dock, float, or canvas mode
- Connects to local Guardian Python daemon (Ollama-backed)
- Knows context → reshapes layout based on active plugins
- Example plugins:
   - Code orchestration (Codexify)
   - DAW control (Ableton Companion)
   - Semantic memory search
- Universal push/pull GitOps node in Companion

---

# AXIS_REMOVAL_INSTRUCTIONS.md

✅ ACTION: Remove all platform-specific Swift files from `Guardian-Core` (Python)

- DELETE:
   - `HealthKitManager.swift`
   - `ProprioceptionGraphView.swift`
   - `SignalPinger.swift`
   - `AmbientVolumeManager.swift`
   - `MotionManager.swift`
   - `GPSManager.swift`

- KEEP:
   - `AuraSummarizer.py` → narrative merge logic
   - `AuraAPI.py` → CRUD for summaries
   - `guardian/cache.py` → Semantic Cache
   - `guardian/plugins/` → Codexify universal adapters

✅ UPDATE `AXIS_SYSTEM_PROMPT.md`:
   - Note that sensors are **mobile-only**
   - Guardian Core is **Python-only**, no Swift code

✅ COMMIT:
   ```bash
   chore(guardian): remove platform-specific Swift modules; align repo to Python-only

# Make sure you’re on the right branch:
git checkout main

# Remove the Swift files:
rm guardian/HealthKitManager.swift
rm guardian/ProprioceptionGraphView.swift
rm guardian/SignalPinger.swift
rm guardian/AmbientVolumeManager.swift
rm guardian/MotionManager.swift
rm guardian/GPSManager.swift

# Add updated AXIS_SYSTEM_PROMPT.md (Python-only note)
# Add your updated Codexify_SYSTEM_MAP.md
# Add AXIS_REMOVAL_INSTRUCTIONS.md for historical clarity

git add .
git commit -m "chore(guardian): remove platform-specific Swift modules; align repo to Python-only"
git push origin main


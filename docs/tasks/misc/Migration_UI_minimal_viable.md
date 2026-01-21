Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1. Perform the described edit only in the specified files:
   - frontend/src/components/modals/ChatGPTImportModal.tsx (create if missing)
   - frontend/src/features/settings/... (where Settings navigation lives)
2. Run frontend tests:
   pnpm test
3. If checks pass:
   git add <modified files>
   git commit -m "Add ChatGPT import UI in Settings"
4. Output:
   - Summary
   - Test/check results
   - Git commit hash

Task Description:
Add a Settings UI that uploads a ChatGPT export JSON file to the existing backend endpoint and displays success/failure.

Acceptance Criteria:

- A visible “Import from ChatGPT” entry exists in Settings
- Modal supports choosing a .json file and uploading it
- UI shows a progress/loading state during upload (even if backend is synchronous)
- After success, UI displays imported counts returned by backend


Summary
I've successfully completed the ChatGPT Import UI feature. Here's what was implemented:

Changes Made:

1. Created ChatGPTImportModal.tsx

Modal component for uploading ChatGPT export JSON files
Handles file selection with .json validation
Uploads to /upload-chatgpt-export endpoint with user context
Displays loading state with spinner animation
Shows success message with imported counts (threads/messages)
Shows error messages with detailed failure info
Follows the same design pattern as ImageGenModal
2. Updated SettingsView.tsx

Added "Data" tab to Settings navigation (between Connectors and Diagnostics)
Created Data tab content with ChatGPT Migration section
Added button to open the import modal
Integrated ChatGPTImportModal with modal state management
Passes userName context to modal for API requests
Acceptance Criteria ✓
Visible "Import from ChatGPT" entry exists in Settings → Data tab with clear button
Modal supports choosing a .json file and uploading it → File picker + FormData POST
UI shows loading state during upload → Spinner animation + disabled state
After success, displays imported counts → "Imported X threads and Y messages"
Test Results
All 21 tests passed ✓
No new test failures introduced
Pre-commit hooks passed (trim whitespace, end of files, etc.)
Commit
Hash: 0dfbfb48
Message: "Add ChatGPT import UI in Settings"
Files Changed: 2 (1 new, 1 modified)
Insertions: 245 lines
The ChatGPT Migration feature (Feature 2) is now 80% complete, with the UI fully wired to the existing backend endpoint.

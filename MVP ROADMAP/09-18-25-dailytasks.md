
Today’s Goal

Ship a “feels-like-a-real-chat” baseline:
 • Users can open Guardian and start typing immediately.
 • A thread is created automatically (in “Loose Threads”) on first input/send.
 • Messages persist and render live in the center pane.
 • Sidebar opens/closes correctly on Safari/Chrome/Tauri and doesn’t duplicate threads.
 • The Cypress test reliably creates a thread, seeds messages, and sees them in ChatView.

⸻

Work Plan (in order)

0) Preflight (15–20 min)
 • Verify DB shape matches code: chat_messages.created_at exists and chat_threads has project_id.
If you ever created the DB before those changes, drop/backup + reinit OR run a one-off ALTER TABLE to add the columns.
 • Confirm “Loose Threads” project (ID=1) exists (your helper was added; just sanity-check).

Quick checks

sqlite3 guardian.db ".schema chat_messages"
sqlite3 guardian.db ".schema chat_threads"
sqlite3 guardian.db "select id,name from projects;"

⸻

A) Backend (FastAPI) — Baseline hardening (60–90 min)
 1. Create thread endpoint + safe auto-create
 • Ensure POST /api/chat/threads exists and returns { ok: true, id }.
 • In POST /api/chat/{thread_id}/messages, call ensure_chat_thread(thread_id, project_id=1) if the row isn’t there. (You already have this pattern—just confirm it’s in.)
 • Default new threads to project_id=1 (“Loose Threads”).
 2. Auto-title on first user message
 • When the first user message arrives for a thread with empty title, set title to first 7–10 words… (already mostly done).
 3. De-dupe sidebar duplicates at source
 • If duplicates are appearing, it’s often because thread creation fires twice (e.g., in two effects).
 • Add a simple idempotency guard: require a client-side thread nonce on POST /api/chat/threads and ignore duplicate nonces within 2 minutes (or add a unique constraint on (user_id, created_at±epsilon, none) if you want to keep it DB-side).
 • Minimal version: if the last created thread (for the same user) has no messages and happened in the last 2 seconds, reuse it.
 4. Tiny health routes sanity
 • Confirm /api/chat/threads lists persisted threads; messages list returns totals.

Acceptance (Backend)
 • curl -X POST /api/chat/threads returns { ok:true, id }.
 • curl -X POST /api/chat/{id}/messages creates + lists at /api/chat/{id}/messages.
 • Duplicates stop reproducing when rapidly opening Guardian.

⸻

B) Frontend — UX that “just works” (60–90 min)
 1. Always show chat UI (blank slate)
 • Guardian view should render ChatView + Composer even with no selected thread.
 • Behavior:
 • On first keystroke (non-whitespace, debounced ~300ms) or on first Send, call POST /api/chat/threads → store threadId → persist draft & messages to that thread.
 • If the URL is /chat/:id, use that numeric thread id; otherwise, use the newly created one.
 2. Composer draft persistence
 • Use sessionStorage keys:
 • Global draft when no thread id yet: draft:global.
 • Threaded draft: draft:thread:${threadId}.
 • On thread creation, move draft:global → draft:thread:${id}.
 3. Wire send() to backend
 • On send: POST /api/chat/{id}/messages for the user message.
 • After the streamed bot reply finishes, POST the assistant message too (so ChatView history matches what you saw live).
 4. Sidebar behavior (Safari/Chrome/Tauri)
 • Fix toggling by driving one source of truth boolean (isSidebarOpen).
 • Desktop: md:block default, but still respond to the hamburger to hide/show.
 • Mobile: hidden by default; hamburger toggles translate-x-0/-translate-x-full and overlay.
 • Ensure body scroll lock only applies on mobile when open; clear on route change.
 5. Tiny UI tidy
 • Keep the borderless hamburger (we already did).
 • Keep the Thread/Project toggle just to the right (spacing handled).
 • Remove the “X” close button (done).
 • Titles should auto populate from the first message.

Acceptance (Frontend)
 • Load Guardian → empty chat is visible; start typing → thread auto-created → draft persists if you navigate away and back.
 • Sidebar opens/closes on Safari/Chrome/Tauri without drift or getting “stuck”.
 • Sending produces a user bubble and later a bot bubble; refreshing shows both (persisted).

⸻

C) E2E — Make Cypress green (30–45 min)
 1. Seed using real endpoints
 • In the spec’s before():
 • POST /api/chat/threads → grab threadId
 • loop: POST /api/chat/{threadId}/messages to seed 60–100 messages
 • Visit /chat/${threadId}.
 • Make sure you include X-API-Key header on each cy.request.
 2. Assertions
 • Wait for [data-testid="chat-message"] > 0.
 • Scroll to top → expect more messages to prepend (no duplicates, monotonic ids).
 • Optionally click hamburger on mobile viewport and assert sidebar visible/hidden.

Acceptance (E2E)
 • Test passes reliably; no [data-testid="chat-message"] timeouts, no 404 on /api/chat/threads.

⸻

Stretch (if time allows)
 • Add debounce (500ms) to first-keystroke thread creation to avoid double create.
 • Add /api/test/seed dev-only route that creates a thread with N messages in one call (simplifies spec).
 • Persist and render the auto-title immediately in the sidebar when first user message posts.

⸻

How this fits your PRD
 • This plan finishes “Baseline Stability & E2E” (your EP0) so you can move directly into SSE v0 (outbox + /api/events) next, then GitHub jobs v0.
 • It also enforces the concept that there are no true loose threads—everything starts in the “Loose Threads” project and can be organized later (exactly what you want).

⸻

What I need from you (now)
 • Confirm the endpoint paths you want to standardize on:
 • POST /api/chat/threads (create)
 • GET /api/chat/threads (list)
 • POST /api/chat/{id}/messages (create message)
 • GET /api/chat/{id}/messages (list)
 • Tell me if your Composer lives in features/chat/components/Composer.tsx (so I can hook the auto-create + sessionStorage draft) and where you keep the sidebar state (so I can unify the toggle logic).

If you want me to go ahead and patch the specific files, point me at:
 • guardian/guardian_api.py (to confirm/create thread + message behavior)
 • src/features/chat/GuardianChat.tsx
 • src/features/chat/components/Composer.tsx
 • src/features/chat/ChatView.tsx
 • cypress/e2e/chat_infinite_scroll.cy.ts

I’ll wire the exact changes inline, matching your current styles and patterns.

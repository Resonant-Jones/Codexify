/**
 * ChatBubble.tsx
 *
 * Purpose:
 * Renders a single chat message bubble for the chat UI. This component handles two
 * visual variants:
 *  - Assistant/Guardian messages (isMe === false) — left-aligned, shows guardian name
 *  - User messages (isMe === true) — right-aligned, styled to indicate ownership
 *
 * Responsibilities:
 *  - Render message content with preserving whitespace (pre-wrap) and basic layout
 *  - Display a compact timestamp using the user's locale
 *  - Provide entrance animation via framer-motion for subtle micro-interactions
 *  - Keep presentational concerns (styling, animation) inside this component so the
 *    parent can remain focused on data/state management
 *
 * Design & accessibility notes:
 *  - Content is displayed in a `div` (not editable) and preserves line breaks via
 *    `whitespace-pre-wrap` to support messages with newlines.
 *  - Consider wrapping message items in an accessible list at a higher-level view
 *    (e.g. `<ul role="list">` / `<li role="listitem">`) so assistive tech can
 *    treat the conversation as a sequence. This file intentionally focuses on a
 *    single message bubble only.
 *  - The timestamp uses `Intl.DateTimeFormat` so it respects user locale and time
 *    formatting preferences.
 *
 * Styling tokens & caveats:
 *  - Uses CSS variables like `--text` and `--muted` for colors; keep them consistent
 *    across the app to enable theme toggling.
 *  - The user-bubble currently inlines background (`#2f2f2f`) and text color (`#fff`).
 *    If you need theming, prefer CSS variables instead of hard-coded values.
 *
 * Animations:
 *  - Entrance uses framer-motion with a spring. The values chosen (stiffness:500,
 *    damping:30) produce a quick pop-in with limited overshoot. Adjust if you need
 *    a subtler or snappier feel.
 *
 * Future improvements:
 *  - Add `aria-label` or `aria-describedby` for messages that are non-text (attachments)
 *  - Extract style constants so tests can assert class-based styling instead of inline styles
 *  - If performance becomes a problem with many messages, consider `React.memo` or
 *    virtualization at the message list level (not here)
 */
import { motion } from "framer-motion";
import { Message } from "@/types/ui";

/**
 * Format timestamp for display in the chat bubble.
 *
 * Uses the user's locale by passing `undefined` to `Intl.DateTimeFormat` which will
 * automatically use the environment locale (browser / system). The function expects
 * a numeric epoch timestamp (ms since UNIX epoch).
 *
 * @param {number} ts - timestamp in milliseconds
 * @returns {string} localized time string (hour:minute)
 */
const fmtTime = (ts: number) => new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(ts);

/**
 * ChatBubble component
 *
 * Renders a single message bubble. Behavior is bifurcated by the `isMe` prop:
 * - `isMe === false` : renders assistant/guardian message (left-aligned, includes guardianName)
 * - `isMe === true`  : renders user message (right-aligned with distinct styling)
 *
 * Props:
 * @param {{ message: Message; isMe: boolean; guardianName: string }} props
 *  - message: Message object (expects `content: string`, `createdAt: number`)
 *  - isMe: whether the message was authored by the current user
 *  - guardianName: display name for assistant/guardian (shown for non-user messages)
 *
 * Accessibility:
 * - This component intentionally emits bare `div`s for content. For full A11y,
 *   ensure the parent message-list wraps items in a container with `role="list"`
 *   and each ChatBubble is treated as `role="listitem"` when appropriate.
 */
export function ChatBubble({ message, isMe, guardianName }: { message: Message; isMe: boolean; guardianName: string }) {
  // Assistant / guardian message branch (left-aligned)
  if (!isMe) {
    return (
      <motion.div data-testid="chat-message" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 500, damping: 30 }} className="w-full">
        <div className="mb-1 text-xs font-semibold" style={{ color: "var(--text)" }}>
          {guardianName}
        </div>
        <div className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "var(--text)" }}>
          {message.content}
        </div>
        <div className="mt-1.5 flex items-center gap-2 text-[10px]" style={{ color: "var(--muted)" }}>
          {fmtTime(message.createdAt)}
        </div>
      </motion.div>
    );
  }
  // User message branch (right-aligned)
  return (
    <motion.div
      data-testid="chat-message"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className="max-w-[78%] rounded-2xl p-3 shadow-sm ml-auto"
      style={{ background: "#2f2f2f", color: "#fff" }}
    >
      <div className="whitespace-pre-wrap text-center text-sm leading-relaxed">
        {message.content}
      </div>
      <div className="mt-1.5 flex items-center justify-end gap-2">
        <span className="text-[10px] opacity-90">{fmtTime(message.createdAt)}</span>
      </div>
    </motion.div>
  );
}

export default ChatBubble;

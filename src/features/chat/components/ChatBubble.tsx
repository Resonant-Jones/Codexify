import { motion } from "framer-motion";
import { Message } from "@/types/ui";

const fmtTime = (ts: number) => new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(ts);

export function ChatBubble({ message, isMe, guardianName }: { message: Message; isMe: boolean; guardianName: string }) {
  if (!isMe) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 500, damping: 30 }} className="w-full">
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
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className="max-w-[78%] rounded-2xl p-3 shadow-sm ml-auto"
      style={{ background: "#2f2f2f", color: "#fff" }}
    >
      <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
      <div className="mt-1.5 flex items-center justify-end gap-2">
        <span className="text-[10px] opacity-90">{fmtTime(message.createdAt)}</span>
      </div>
    </motion.div>
  );
}

export default ChatBubble;


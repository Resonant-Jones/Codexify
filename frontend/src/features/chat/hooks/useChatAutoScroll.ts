import { useEffect, useRef } from "react";

export function useChatAutoScroll(messagesLength: number, threshold = 120) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nearBottomRef = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateNearBottom = () => {
      const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
      nearBottomRef.current = distance <= threshold;
    };

    updateNearBottom();
    el.addEventListener("scroll", updateNearBottom, { passive: true });
    return () => {
      el.removeEventListener("scroll", updateNearBottom);
    };
  }, [threshold]);

  useEffect(() => {
    if (!nearBottomRef.current) return;
    requestAnimationFrame(() => {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
  }, [messagesLength]);

  return { containerRef, endRef };
}

import React from "react";

type Toast = { id: number; message: string; actionLabel?: string; onAction?: () => void };

export function ToastPortal() {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  React.useEffect(() => {
    function onToast(e: Event) {
      const detail = (e as CustomEvent).detail || {};
      const t: Toast = {
        id: Date.now() + Math.floor(Math.random() * 1000),
        message: String(detail.message || ""),
        actionLabel: detail.actionLabel,
        onAction: typeof detail.onAction === "function" ? detail.onAction : undefined,
      };
      setToasts((prev) => [...prev, t]);
      const timeout = Number(detail.timeoutMs ?? 5000);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== t.id));
      }, timeout);
    }
    window.addEventListener("cfy:toast", onToast as EventListener);
    return () => window.removeEventListener("cfy:toast", onToast as EventListener);
  }, []);

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[1700] space-y-2">
      {toasts.map((t) => (
        <div key={t.id} className="rounded-full border px-4 py-2 text-sm flex items-center gap-3"
             style={{ background: "rgba(0,0,0,0.7)", color: "#fff", borderColor: "rgba(255,255,255,0.2)" }}>
          <span>{t.message}</span>
          {t.onAction && (
            <button type="button" className="underline underline-offset-2" onClick={() => { t.onAction?.(); setToasts((prev) => prev.filter((x) => x.id !== t.id)); }}>
              {t.actionLabel || "Undo"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export default ToastPortal;

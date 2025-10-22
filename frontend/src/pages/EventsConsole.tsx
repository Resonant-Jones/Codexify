import { useState } from "react";
import { useEventStream } from "../hooks/useEventStream";

type Row = { id: string; type: string; data: string; t: string };

export default function EventsConsole() {
  const [rows, setRows] = useState<Row[]>([]);

  const { connected } = useEventStream({
    onEvent: (ev) => {
      setRows((r) =>
        [
          {
            id: ev.lastEventId || `${Date.now()}`,
            type: ev.type || "message",
            data: ev.data,
            t: new Date().toLocaleTimeString(),
          },
          ...r,
        ].slice(0, 200)
      );
    },
  });

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "8px 0 16px" }}>
        Events <small style={{ opacity: 0.6, fontWeight: 400 }}>({connected ? "live" : "paused"})</small>
      </h2>
      <div style={{ display: "grid", gap: 8 }}>
        {rows.map((r) => (
          <div key={r.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
            <div style={{ fontSize: 12, opacity: 0.6 }}>
              {r.t} · {r.type}
            </div>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{r.data}</pre>
          </div>
        ))}
        {rows.length === 0 && <div style={{ opacity: 0.6 }}>Waiting for messages…</div>}
      </div>
    </div>
  );
}

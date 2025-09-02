import React from "react";
import { Button } from "@/components/ui/button";

export type ThemeMode = "light" | "dark" | "system";

export default function SegmentedThemeControl({
  mode,
  onChange,
}: {
  mode: ThemeMode;
  onChange: (m: ThemeMode) => void;
}) {
  const items: ThemeMode[] = ["light", "system", "dark"];

  return (
    <div
      className="inline-flex rounded-xl border overflow-hidden"
      style={{
        background: "var(--panel-bg)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
      }}
    >
      {items.map((m) => (
        <Button
          key={m}
          type="button"
          variant={mode === m ? "default" : "ghost"}
          size="sm"
          className="rounded-none"
          onClick={() => onChange(m)}
          style={
            mode === m
              ? { background: "var(--accent-strong)", color: "var(--seg-selected-fg, #fff)" }
              : undefined
          }
        >
          {m[0].toUpperCase() + m.slice(1)}
        </Button>
      ))}
    </div>
  );
}

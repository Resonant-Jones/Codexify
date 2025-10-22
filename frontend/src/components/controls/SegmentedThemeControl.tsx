import { Button } from "@/components/ui/button";
import { ThemeMode } from "@/types/ui";

export function SegmentedThemeControl({ mode, onChange }: { mode: ThemeMode; onChange: (m: ThemeMode) => void }) {
  const items = ["light", "system", "dark"] as ThemeMode[];
  return (
    <div className="inline-flex rounded-xl border bg-white dark:bg-neutral-700 border-neutral-200 dark:border-neutral-600 overflow-hidden">
      {items.map((m) => (
        <Button
          key={m}
          type="button"
          variant={mode === m ? "default" : "ghost"}
          size="sm"
          className="rounded-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ outlineColor: "var(--accent-weak)" }}
          onClick={() => onChange(m)}
        >
          {m[0].toUpperCase() + m.slice(1)}
        </Button>
      ))}
    </div>
  );
}

export default SegmentedThemeControl;


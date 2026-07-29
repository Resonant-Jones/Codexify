import { ThemeMode } from "@/types/ui";

type SegmentedThemeControlProps = {
  mode: ThemeMode;
  onChange: (m: ThemeMode) => void;
};

const THEME_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "system", label: "System" },
  { value: "dark", label: "Dark" },
];

export function SegmentedThemeControl({
  mode,
  onChange,
}: SegmentedThemeControlProps) {
  return (
    <div
      className="glass-pill inline-flex"
      role="group"
      aria-label="Theme mode"
    >
      {THEME_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          className="pill-tab text-xs"
          data-state={option.value === mode ? "active" : "inactive"}
          aria-pressed={option.value === mode}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default SegmentedThemeControl;

import type { ReactNode } from "react";

type SettingsSectionCardProps = {
  actions?: ReactNode;
  as?: "div" | "section";
  children?: ReactNode;
  className?: string;
  eyebrow?: ReactNode;
  subtitle?: ReactNode;
  testId?: string;
  title: ReactNode;
};

export default function SettingsSectionCard({
  actions,
  as: Component = "section",
  children,
  className,
  eyebrow,
  subtitle,
  testId,
  title,
}: SettingsSectionCardProps) {
  return (
    <Component
      data-testid={testId}
      className={[
        "space-y-[var(--shell-gap)] rounded-[var(--card-radius)] border border-[var(--panel-border)] bg-[var(--panel-bg)] p-[var(--card-pad)]",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-[var(--shell-gap)]">
        <div className="min-w-0 space-y-[calc(var(--radius-micro)/2)]">
          {eyebrow ? (
            <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
              {eyebrow}
            </div>
          ) : null}
          <div className="text-sm font-semibold leading-6 text-[var(--text)]">
            {title}
          </div>
          {subtitle ? (
            <div className="text-xs leading-5 text-[var(--muted)]">
              {subtitle}
            </div>
          ) : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>

      <div className="space-y-[var(--shell-gap)]">{children}</div>
    </Component>
  );
}

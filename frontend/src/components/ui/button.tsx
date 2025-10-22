import * as React from "react";

type Variant = "default" | "ghost" | "destructive";
type Size = "sm" | "md" | "lg" | "icon";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const cx = (...parts: Array<string | false | null | undefined>) =>
  parts.filter(Boolean).join(" ");

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none rounded-[var(--tile-radius,19px)] focus:outline-none";
    const variants: Record<Variant, string> = {
      default:
        "bg-[var(--accent)] text-[var(--panel-bg)] hover:bg-[var(--accent-strong)] focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
      ghost:
        "bg-transparent text-[var(--text)] hover:bg-[var(--accent-weak)]/20 focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
      destructive:
        "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700",
    };
    const sizes: Record<Size, string> = {
      sm: "h-7 px-3 text-xs",
      md: "h-9 px-4 text-sm",
      lg: "h-11 px-6 text-base",
      icon: "h-9 w-9",
    };
    return (
      <button
        ref={ref}
        className={cx(base, variants[variant], sizes[size], className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
export default Button;

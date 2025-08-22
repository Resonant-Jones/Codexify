import * as React from "react";

type Variant = "default" | "ghost";
type Size = "sm" | "icon" | "md" | "lg";

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
      "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50 disabled:pointer-events-none";
    const variants: Record<Variant, string> = {
      default: "bg-[var(--accent)] text-black hover:opacity-95",
      ghost:
        "bg-transparent text-[var(--text)] hover:bg-[color-mix(in_oklab,var(--panel-bg),black_10%)]",
    };
    const sizes: Record<Size, string> = {
      sm: "h-8 px-2 py-1",
      md: "h-9 px-3 py-2",
      lg: "h-10 px-4 py-2",
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


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
  ({ className, style, variant = "default", size = "md", ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none focus:outline-none";
    const variants: Record<Variant, string> = {
      default:
        "bg-[var(--accent)] text-[var(--panel-bg)] hover:bg-[var(--accent-strong)] focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
      ghost:
        "bg-transparent text-[var(--text)] hover:bg-[var(--accent-weak)]/20 focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
      destructive:
        "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-2 focus-visible:ring-red-700",
    };
    const sizes: Record<Size, { height: string; width?: string; padding?: string; text?: string }> = {
      sm: { height: "h-8", padding: "px-3", text: "text-xs" },
      md: { height: "h-10", padding: "px-4", text: "text-sm" },
      lg: { height: "h-12", padding: "px-6", text: "text-base" },
      icon: { height: "h-10", width: "w-10" },
    };
    const hasCallerUtility = (pattern: RegExp) =>
      className?.split(/\s+/).some((token) => pattern.test(token)) ?? false;
    const callerOwnsRadius = hasCallerUtility(/^rounded(?:-|$)/);
    const selectedSize = sizes[size];
    return (
      <button
        ref={ref}
        className={cx(
          base,
          variants[variant],
          !hasCallerUtility(/^(?:h-|size-)/) && selectedSize.height,
          !hasCallerUtility(/^(?:w-|size-)/) && selectedSize.width,
          !hasCallerUtility(/^px-/) && selectedSize.padding,
          !hasCallerUtility(/^text-(?:xs|sm|base|lg|xl|[2-9]xl|\[\d)/) && selectedSize.text,
          className
        )}
        style={{ borderRadius: callerOwnsRadius ? undefined : "var(--radius-micro)", ...style }}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
export default Button;

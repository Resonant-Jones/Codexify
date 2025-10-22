import * as React from "react";
import { cn } from "@/lib/utils";

const cx = (...p: Array<string | false | null | undefined>) =>
  p.filter(Boolean).join(" ");

export interface DivProps extends React.HTMLAttributes<HTMLDivElement> {}

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

/**
 * Card with built-in double-layered bezel.
 * - Outer ring: ::before gradient with XOR mask (3px "glass" edge)
 * - Inner lip: ::after inset highlight (1px)
 * - Uses existing tokens via inline styles (call-site styles still win)
 */
export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = "", style, ...props }, ref) => {
    const disableBezel = className.includes("bezel-none");
    return (
      <div
        ref={ref}
        className={cn(
          // Base card chrome
          "relative rounded-2xl border shadow-sm",
          // Outer ring (subtle gradient bezel)
          "before:content-[''] before:absolute before:inset-0 before:rounded-[inherit] before:pointer-events-none before:p-px",
          "before:[mask:linear-gradient(#000_0_0)_content-box,linear-gradient(#000_0_0)]",
          "before:[-webkit-mask-composite:xor] before:[mask-composite:exclude]",
          "before:bg-gradient-to-b before:from-white/40 before:to-white/5",
          // Inner lip (soft top highlight)
          "after:content-[''] after:absolute after:inset-[1px] after:rounded-[inherit] after:pointer-events-none",
          "after:shadow-[inset_0_1px_rgba(255,255,255,0.22)]",
          // Allow consumers to opt-out by adding 'bezel-none'
          disableBezel ? "!before:hidden !after:hidden" : "",
          className
        )}
        style={{
          // Keep the ring clean at the edge; callers control colors
          backgroundClip: "padding-box",
          ...style,
        }}
        {...props}
      />
    );
  }
);
Card.displayName = "Card";

export const CardHeader = ({ className, ...props }: DivProps) => (
  <div className={cx("p-4", className)} {...props} />
);
export const CardTitle = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cx("text-lg font-semibold", className)} {...props} />
);
export const CardContent = ({ className, ...props }: DivProps) => (
  <div className={cx("p-4", className)} {...props} />
);
export const CardFooter = ({ className, ...props }: DivProps) => (
  <div className={cx("p-4", className)} {...props} />
);
export default Card;

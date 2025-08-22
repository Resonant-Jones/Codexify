import * as React from "react";

const cx = (...p: Array<string | false | null | undefined>) =>
  p.filter(Boolean).join(" ");

export interface DivProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Card = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cx(
        "rounded-2xl border border-[var(--panel-border)] bg-[var(--panel-bg)]/60 backdrop-blur-md text-[var(--text)]",
        className
      )}
      {...props}
    />
  )
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

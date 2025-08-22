import * as React from "react";

export const Separator = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    role="separator"
    className={
      "h-px w-full bg-[var(--panel-border)] " + (className || "")
    }
    {...props}
  />
);

export default Separator;


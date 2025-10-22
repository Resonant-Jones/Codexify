import * as React from "react";

export const Separator = ({ className = "", ...props }: { className?: string } & React.HTMLAttributes<HTMLHRElement>) => (
  <hr className={("border-t border-[var(--panel-border)] " + className).trim()} {...props} />
);

export default Separator;

import * as React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={
        "w-full h-9 rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 py-1 text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" +
        (className ? " " + className : "")
      }
      {...props}
    />
  )
);
Input.displayName = "Input";
export default Input;

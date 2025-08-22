import * as React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={
        "h-9 w-full rounded-md border bg-transparent px-3 text-sm outline-none " +
        "border-[var(--panel-border)] text-[var(--text)] placeholder-[var(--muted)] " +
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      + (className ? " " + className : "")
      }
      {...props}
    />
  )
);
Input.displayName = "Input";
export default Input;


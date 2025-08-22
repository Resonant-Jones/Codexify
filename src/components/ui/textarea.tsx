import * as React from "react";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={
        "min-h-[80px] w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none " +
        "border-[var(--panel-border)] text-[var(--text)] placeholder-[var(--muted)] " +
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        + (className ? " " + className : "")
      }
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
export default Textarea;


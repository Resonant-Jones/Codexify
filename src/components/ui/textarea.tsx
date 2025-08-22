import * as React from "react";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={
        "w-full rounded-md border border-[var(--panel-border)] bg-[var(--panel-bg)]/80 px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-none" +
        (className ? " " + className : "")
      }
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
export default Textarea;

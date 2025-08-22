Here’s a ready-to-paste Codex CLI prompt that will create the missing @/components/ui/* stubs (minimal, typed, Tailwind-friendly), without touching the rest of your code.

⸻

Prompt for Codex CLI

Goal

Make the React app compile by providing minimal UI stub components for the imports under @/components/ui/*. Do not refactor existing call sites. Do not change any behavior outside these new stubs.

Scope

Create these files:
 • src/components/ui/button.tsx
 • src/components/ui/card.tsx
 • src/components/ui/input.tsx
 • src/components/ui/avatar.tsx
 • src/components/ui/textarea.tsx
 • src/components/ui/dropdown-menu.tsx
 • src/components/ui/badge.tsx
 • src/components/ui/separator.tsx
 • src/components/ui/sheet.tsx

Do not modify any other files.

Requirements
 • Each component must be a typed React component using forwardRef where appropriate.
 • Accept and merge className so Tailwind classes from callers are preserved.
 • Implement only the props actually used by call sites (see codebase):
 • Button: variant = "default" | "ghost", size = "sm" | "icon", plus standard button props.
 • Card: export Card, CardContent (also export CardHeader, CardTitle, CardFooter for future use).
 • Input, Textarea: standard HTML props.
 • Avatar: export Avatar, AvatarImage, AvatarFallback.
 • DropdownMenu: export DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem; support align="end".
 • Badge: simple span.
 • Separator: horizontal separator.
 • Sheet: export Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle; support controlled (open, onOpenChange) and uncontrolled usage; side="left" default.
 • No extra dependencies. Use React only (we already have @radix-ui/react-visually-hidden installed; don’t add more).

Edits

Create the files with the exact content below.

⸻

src/components/ui/button.tsx

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

src/components/ui/card.tsx

import * as React from "react";

const cx = (...p: Array<string | false | null | undefined>) =>
  p.filter(Boolean).join(" ");

export interface DivProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Card = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cx(
        "rounded-xl border bg-[var(--panel-bg)] text-[var(--text)]",
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

src/components/ui/input.tsx

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

src/components/ui/textarea.tsx

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

src/components/ui/avatar.tsx

import * as React from "react";

export const Avatar = ({
  className,
  children,
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={
      "relative inline-flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-[var(--chip-bg)] " +
      (className || "")
    }
  >
    {children}
  </div>
);

export const AvatarImage = ({
  src,
  alt,
  className,
  ...props
}: React.ImgHTMLAttributes<HTMLImageElement>) =>
  src ? (
    <img
      src={src}
      alt={alt}
      className={"h-full w-full object-cover " + (className || "")}
      {...props}
    />
  ) : null;

export const AvatarFallback = ({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => (
  <span
    className={
      "grid h-full w-full place-items-center text-xs text-[var(--text)] " +
      (className || "")
    }
    {...props}
  >
    {children}
  </span>
);

export default Avatar;

src/components/ui/dropdown-menu.tsx

import * as React from "react";

type Ctx = {
  open: boolean;
  setOpen: (v: boolean) => void;
};
const DropdownCtx = React.createContext<Ctx | null>(null);

export const DropdownMenu = ({ children }: { children: React.ReactNode }) => {
  const [open, setOpen] = React.useState(false);
  return (
    <DropdownCtx.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </DropdownCtx.Provider>
  );
};

export const DropdownMenuTrigger = ({
  asChild,
  children,
  ...props
}: React.HTMLAttributes<HTMLButtonElement> & { asChild?: boolean }) => {
  const ctx = React.useContext(DropdownCtx)!;
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as any, {
      onClick: (e: any) => {
        (children as any).props?.onClick?.(e);
        ctx.setOpen(!ctx.open);
      },
      ...props,
    });
  }
  return (
    <button onClick={() => ctx.setOpen(!ctx.open)} {...props}>
      {children}
    </button>
  );
};

export const DropdownMenuContent = ({
  children,
  align,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { align?: "start" | "end" }) => {
  const ctx = React.useContext(DropdownCtx)!;
  React.useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!(e.target as HTMLElement)?.closest("[data-ddm-root]")) ctx.setOpen(false);
    };
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, [ctx]);
  if (!ctx.open) return null;
  return (
    <div
      data-ddm-root
      className={
        "absolute z-50 mt-2 min-w-40 rounded-md border bg-[var(--panel-bg)] p-1 shadow-lg " +
        (align === "end" ? "right-0" : "left-0") +
        (className ? " " + className : "")
      }
      {...props}
    >
      {children}
    </div>
  );
};

export const DropdownMenuItem = ({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button
    className={
      "w-full rounded-md px-3 py-2 text-left text-sm hover:bg-[color-mix(in_oklab,var(--panel-bg),black_10%)] " +
      (className || "")
    }
    {...props}
  />
);

src/components/ui/badge.tsx

import * as React from "react";

export const Badge = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => (
  <span
    className={
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium " +
      "bg-[var(--accent-weak)] text-black " +
      (className || "")
    }
    {...props}
  />
);

export default Badge;

src/components/ui/separator.tsx

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

src/components/ui/sheet.tsx

import * as React from "react";

type Side = "left" | "right";
type SheetCtx = {
  open: boolean;
  setOpen: (v: boolean) => void;
};
const Ctx = React.createContext<SheetCtx | null>(null);

export const Sheet = ({
  children,
  open: controlledOpen,
  onOpenChange,
}: {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (v: boolean) => void;
}) => {
  const [uncontrolled, setUncontrolled] = React.useState(false);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen! : uncontrolled;
  const setOpen = (v: boolean) => {
    if (!isControlled) setUncontrolled(v);
    onOpenChange?.(v);
  };
  return <Ctx.Provider value={{ open, setOpen }}>{children}</Ctx.Provider>;
};

export const SheetTrigger = ({
  asChild,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement> & { asChild?: boolean }) => {
  const ctx = React.useContext(Ctx)!;
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as any, {
      onClick: (e: any) => {
        (children as any).props?.onClick?.(e);
        ctx.setOpen(true);
      },
      ...props,
    });
  }
  return (
    <button onClick={() => ctx.setOpen(true)} {...props}>
      {children}
    </button>
  );
};

export const SheetContent = ({
  side = "left",
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { side?: Side }) => {
  const ctx = React.useContext(Ctx)!;
  if (!ctx.open) return null;
  const translate =
    side === "left" ? "translate-x-0 left-0" : "translate-x-0 right-0";
  return (
    <>
      <div
        onClick={() => ctx.setOpen(false)}
        className="fixed inset-0 z-40 bg-black/40"
      />
      <div
        className={
          "fixed z-50 top-0 h-full w-80 bg-[var(--panel-bg)] text-[var(--text)] shadow-xl " +
          "border border-[var(--panel-border)] " +
          translate +
          (className ? " " + className : "")
        }
        {...props}
      >
        {children}
      </div>
    </>
  );
};

export const SheetHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={"p-3 border-b border-[var(--panel-border)] " + (className || "")} {...props} />
);

export const SheetTitle = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={"text-sm font-semibold " + (className || "")} {...props} />
);

⸻

Acceptance criteria
 • pnpm -C ./src typecheck succeeds.
 • pnpm -C ./src dev starts without “module not found” for @/components/ui/*.
 • Existing UI keeps its layout/styling (these stubs pass through className and match the prop shapes used by callers).

Notes
 • Keep using your existing @radix-ui/react-visually-hidden import where already present; we didn’t add new Radix deps.
 • These stubs are intentionally minimal so we can iterate later (swap in your design system without changing call sites).

After Codex applies patches

Run:

pnpm --dir ./src add framer-motion lucide-react @radix-ui/react-visually-hidden
pnpm -C ./src typecheck
pnpm -C ./src dev

If you want me to generate a second Codex prompt to migrate these stubs to your preferred design system later, say the word.

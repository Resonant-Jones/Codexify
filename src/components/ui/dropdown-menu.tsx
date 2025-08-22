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


import * as React from "react";

type DialogCtx = {
  open: boolean;
  setOpen: (v: boolean) => void;
};
const Ctx = React.createContext<DialogCtx | null>(null);

export const Dialog = ({
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

export const DialogTrigger = ({
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

export const DialogPortal = ({ children }: { children: React.ReactNode }) => {
  return typeof document !== "undefined" ? <>{children}</> : null;
};

export const DialogOverlay = ({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => {
  const ctx = React.useContext(Ctx)!;
  if (!ctx.open) return null;
  return (
    <div
      onClick={() => ctx.setOpen(false)}
      className={`fixed inset-0 z-50 bg-black/80 ${className}`}
      {...props}
    />
  );
};

export const DialogContent = ({
  className = "",
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => {
  const ctx = React.useContext(Ctx)!;
  if (!ctx.open) return null;

  return (
    <DialogPortal>
      <DialogOverlay />
      <div
        onClick={(e) => e.stopPropagation()}
        className={`fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-white/10 bg-[var(--card-bg)] p-6 shadow-lg rounded-[var(--tile-radius,19px)] ${className}`}
        {...props}
      >
        {children}
      </div>
    </DialogPortal>
  );
};

export const DialogHeader = ({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex flex-col space-y-1.5 text-center sm:text-left ${className}`}
    {...props}
  />
);

export const DialogFooter = ({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={`flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 ${className}`}
    {...props}
  />
);

export const DialogTitle = ({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h2
    className={`text-lg font-semibold leading-none tracking-tight ${className}`}
    {...props}
  />
);

export const DialogDescription = ({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p
    className={`text-sm opacity-70 ${className}`}
    {...props}
  />
);

export const DialogClose = ({
  className = "",
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) => {
  const ctx = React.useContext(Ctx)!;
  return (
    <button
      type="button"
      onClick={() => ctx.setOpen(false)}
      className={className}
      {...props}
    >
      {children}
    </button>
  );
};

export default Dialog;

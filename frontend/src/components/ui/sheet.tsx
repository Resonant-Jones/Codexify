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

export default Sheet;

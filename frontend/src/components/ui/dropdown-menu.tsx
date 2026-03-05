import * as React from "react";

type Ctx = {
  open: boolean;
  setOpen: (v: boolean) => void;
  rootRef: React.RefObject<HTMLDivElement | null>;
};

const DropdownCtx = React.createContext<Ctx | null>(null);

type DropdownMenuProps = {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export const DropdownMenu = ({
  children,
  open: controlledOpen,
  onOpenChange,
}: DropdownMenuProps) => {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement | null>(null);

  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const setOpen = (value: boolean) => {
    if (isControlled) {
      onOpenChange?.(value);
      return;
    }
    setUncontrolledOpen(value);
  };

  return (
    <DropdownCtx.Provider value={{ open, setOpen, rootRef }}>
      <div ref={rootRef} data-ddm-root className="relative inline-block">
        {children}
      </div>
    </DropdownCtx.Provider>
  );
};

type TriggerProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
};

export const DropdownMenuTrigger = ({
  asChild,
  children,
  onClick,
  onKeyDown,
  ...props
}: TriggerProps) => {
  const ctx = React.useContext(DropdownCtx)!;
  const toggle = () => ctx.setOpen(!ctx.open);

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<{
      onClick?: (event: React.MouseEvent<HTMLElement>) => void;
      type?: string;
    }>;
    const childOnClick = child.props?.onClick;

    return React.cloneElement(child, {
      ...props,
      onClick: (event: React.MouseEvent<HTMLElement>) => {
        childOnClick?.(event);
        onClick?.(event as unknown as React.MouseEvent<HTMLButtonElement>);
        if (event.defaultPrevented) return;
        toggle();
      },
      type: child.props.type ?? "button",
    });
  }

  return (
    <button
      type="button"
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented) return;
        toggle();
      }}
      onKeyDown={(event) => {
        onKeyDown?.(event);
        if (event.defaultPrevented) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggle();
        }
      }}
      {...props}
    >
      {children}
    </button>
  );
};

type DropdownMenuContentProps = React.HTMLAttributes<HTMLDivElement> & {
  align?: "start" | "end";
  side?: "top" | "bottom";
  sideOffset?: number;
  collisionPadding?: number;
};

export const DropdownMenuContent = ({
  children,
  side = "bottom",
  sideOffset = 8,
  collisionPadding = 0,
  align,
  className,
  style,
  ...props
}: DropdownMenuContentProps) => {
  const ctx = React.useContext(DropdownCtx)!;

  React.useEffect(() => {
    const onDoc = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      const root = ctx.rootRef.current;
      if (!root) return;
      if (!root.contains(target)) {
        ctx.setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [ctx]);

  if (!ctx.open) return null;

  const resolvedOffset = Number.isFinite(Number(sideOffset))
    ? Math.max(0, Number(sideOffset))
    : 8;
  const resolvedCollisionPadding = Number.isFinite(Number(collisionPadding))
    ? Math.max(0, Number(collisionPadding))
    : 0;

  const placementStyle: React.CSSProperties = {
    ...(side === "top"
      ? { bottom: `calc(100% + ${resolvedOffset}px)` }
      : { top: `calc(100% + ${resolvedOffset}px)` }),
    ...(align === "end"
      ? { right: `${resolvedCollisionPadding}px` }
      : { left: `${resolvedCollisionPadding}px` }),
    ...style,
  };

  return (
    <div
      data-ddm-root
      className={
        "absolute z-50 min-w-40 rounded-md border bg-[var(--panel-bg)] p-1 shadow-lg " +
        (className ? " " + className : "")
      }
      style={placementStyle}
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

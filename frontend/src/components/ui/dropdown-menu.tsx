import * as React from "react";
import { createPortal } from "react-dom";

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

  const setOpen = React.useCallback(
    (value: boolean) => {
      if (isControlled) {
        onOpenChange?.(value);
        return;
      }
      setUncontrolledOpen(value);
    },
    [isControlled, onOpenChange]
  );

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
      "aria-expanded": ctx.open,
      "aria-haspopup": "menu",
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
      aria-expanded={ctx.open}
      aria-haspopup="menu"
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

type Placement = {
  left: number;
  top: number;
  visibility: React.CSSProperties["visibility"];
};

function resolvePlacement(
  rootRect: DOMRect,
  contentRect: DOMRect,
  options: {
    side: "top" | "bottom";
    align?: "start" | "end";
    sideOffset: number;
    collisionPadding: number;
  }
): Placement {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const { side, align, sideOffset, collisionPadding } = options;

  const fitsBelow =
    rootRect.bottom + sideOffset + contentRect.height <=
    viewportHeight - collisionPadding;
  const fitsAbove =
    rootRect.top - sideOffset - contentRect.height >= collisionPadding;

  const resolvedSide =
    side === "top"
      ? fitsAbove || !fitsBelow
        ? "top"
        : "bottom"
      : fitsBelow || !fitsAbove
        ? "bottom"
        : "top";

  let left =
    align === "end"
      ? rootRect.right - contentRect.width
      : rootRect.left;
  let top =
    resolvedSide === "top"
      ? rootRect.top - sideOffset - contentRect.height
      : rootRect.bottom + sideOffset;

  left = Math.min(
    Math.max(collisionPadding, left),
    Math.max(collisionPadding, viewportWidth - contentRect.width - collisionPadding)
  );
  top = Math.min(
    Math.max(collisionPadding, top),
    Math.max(collisionPadding, viewportHeight - contentRect.height - collisionPadding)
  );

  return { left, top, visibility: "visible" };
}

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
  const contentRef = React.useRef<HTMLDivElement | null>(null);
  const [placement, setPlacement] = React.useState<Placement>({
    left: 0,
    top: 0,
    visibility: "hidden",
  });

  const resolvedOffset = Number.isFinite(Number(sideOffset))
    ? Math.max(0, Number(sideOffset))
    : 8;
  const resolvedCollisionPadding = Number.isFinite(Number(collisionPadding))
    ? Math.max(0, Number(collisionPadding))
    : 0;

  const updatePlacement = React.useCallback(() => {
    const root = ctx.rootRef.current;
    const content = contentRef.current;
    if (!root || !content) return;
    const rootRect = root.getBoundingClientRect();
    const contentRect = content.getBoundingClientRect();
    setPlacement(
      resolvePlacement(rootRect, contentRect, {
        side,
        align,
        sideOffset: resolvedOffset,
        collisionPadding: resolvedCollisionPadding,
      })
    );
  }, [align, ctx.rootRef, resolvedCollisionPadding, resolvedOffset, side]);

  React.useLayoutEffect(() => {
    if (!ctx.open) return undefined;
    updatePlacement();

    const handleResize = () => updatePlacement();
    const handleScroll = () => updatePlacement();

    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", handleScroll, true);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [ctx.open, updatePlacement]);

  React.useEffect(() => {
    if (!ctx.open) return undefined;

    const onDoc = (event: MouseEvent) => {
      const target = event.target as Node | null;
      const root = ctx.rootRef.current;
      const content = contentRef.current;
      if (!target || !root) return;
      if (root.contains(target) || content?.contains(target)) {
        return;
      }
      ctx.setOpen(false);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        ctx.setOpen(false);
      }
    };

    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [ctx]);

  if (!ctx.open || typeof document === "undefined") return null;

  return createPortal(
    <div
      ref={contentRef}
      data-ddm-root
      role="menu"
      className={
        "inline-flex min-w-40 max-w-[min(32rem,calc(100vw-24px))] flex-col rounded-md border bg-[var(--panel-bg)] p-1 shadow-lg " +
        (className ? " " + className : "")
      }
      style={{
        position: "fixed",
        zIndex: 1000,
        left: placement.left,
        top: placement.top,
        width: "max-content",
        visibility: placement.visibility,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>,
    document.body
  );
};

export const DropdownMenuItem = ({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button
    role="menuitem"
    className={
      "w-full rounded-md px-3 py-2 text-left text-sm hover:bg-[color-mix(in_oklab,var(--panel-bg),black_10%)] " +
      (className || "")
    }
    {...props}
  />
);

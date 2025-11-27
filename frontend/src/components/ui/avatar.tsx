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

import clsx from "clsx";
import type { ImgHTMLAttributes } from "react";

export type SourceLogoImageProps = Omit<
  ImgHTMLAttributes<HTMLImageElement>,
  "alt" | "src"
> & {
  src: string;
  alt?: string;
  title?: string;
};

export default function SourceLogoImage({
  src,
  alt,
  title,
  className,
  loading,
  decoding,
  draggable = false,
  ...props
}: SourceLogoImageProps) {
  const resolvedAlt = alt ?? title ?? "";
  const ariaHidden = props["aria-hidden"] ?? (resolvedAlt ? undefined : true);

  return (
    <img
      {...props}
      src={src}
      alt={resolvedAlt}
      title={title}
      loading={loading ?? "eager"}
      decoding={decoding ?? "async"}
      draggable={draggable}
      aria-hidden={ariaHidden}
      className={clsx("block h-4 w-4 max-h-4 max-w-4 shrink-0 select-none object-contain", className)}
    />
  );
}

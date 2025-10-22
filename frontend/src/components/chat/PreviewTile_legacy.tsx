import * as React from "react";
import PreviewTileBase from "@/components/ui/PreviewTile";

type Props = {
  title: string;
  snippet?: string;
  minHeight?: number;
  onClick?: () => void;
  active?: boolean;
  trailing?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
};

export default function PreviewTile({
  title,
  snippet = "",
  minHeight = 88,
  onClick,
  active,
  trailing,
  className,
  style,
}: Props) {
  const children: React.ReactNode[] = [
    <span key="title">{title}</span>,
    <span key="snippet">{snippet || "\u00a0"}</span>,
  ];
  if (trailing) {
    children.push(<span key="trailing">{trailing}</span>);
  }

  return (
    <PreviewTileBase
      rectH={minHeight}
      onClick={onClick}
      active={active}
      className={className}
      style={style}
    >
      {children}
    </PreviewTileBase>
  );
}

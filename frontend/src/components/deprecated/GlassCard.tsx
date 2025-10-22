// Thin wrapper retained so legacy imports continue to function during the
// stabilization window. Prefer using FrameCard directly instead.
import * as React from "react";
import FrameCard, { FrameCardProps } from "@/components/surface/FrameCard";

export type GlassCardProps = FrameCardProps;

const GlassCard: React.FC<GlassCardProps> = ({ shimmerMode = "subtle", refractiveFallback = true, ...rest }) => (
  <FrameCard shimmerMode={shimmerMode} refractiveFallback={refractiveFallback} {...rest} />
);

export default GlassCard;

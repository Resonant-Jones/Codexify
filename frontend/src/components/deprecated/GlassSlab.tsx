// Archived GlassSlab component retained for testing legacy chrome.
import React from "react";
import FrameCard from "@/components/surface/FrameCard";

interface GlassSlabProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  radius?: string;
  intensity?: number;
  wallpaperUrl?: string;
  className?: string;
  rim?: boolean;
  rimStyle?: React.CSSProperties;
  style?: React.CSSProperties;
}

const GlassSlab: React.FC<GlassSlabProps> = ({
  children,
  radius = "var(--card-radius)",
  intensity = 0.008,
  wallpaperUrl,
  className = "",
  rim = true,
  rimStyle,
  style,
  ...props
}) => {
  const defaultRim = rim
    ? {
        border: "1.5px solid rgba(255,255,255,0.12)",
        boxShadow:
          "0 2px 12px 2px rgba(0,0,0,0.13), 0 0px 0px 1.5px rgba(255,255,255,0.10) inset",
        pointerEvents: "none" as const,
        borderRadius: `calc(${radius} - 3px)`,
        ...rimStyle,
      }
    : undefined;

  return (
    <div
      className={`glass-slab relative w-full h-full ${className}`}
      style={{ borderRadius: radius, ...style }}
      {...props}
    >
      <div
        className="glass-slab__backdrop absolute inset-0 -z-10 pointer-events-none"
        aria-hidden="true"
        style={{ borderRadius: radius }}
      >
        <FrameCard
          wallpaperUrl={wallpaperUrl}
          className="w-full h-full"
          style={{ borderRadius: radius, background: "transparent", border: "none" }}
          intensity={intensity}
          aberration={0}
        />
      </div>

      {rim && (
        <div
          className="glass-slab__rim absolute inset-0"
          aria-hidden="true"
          style={defaultRim}
        />
      )}

      <div
        className="glass-slab__content relative z-10 w-full h-full flex flex-col"
        style={{ borderRadius: radius }}
      >
        {children}
      </div>
    </div>
  );
};

export default GlassSlab;

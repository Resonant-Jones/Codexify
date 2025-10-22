import React from "react";
import FrameCard from "@/components/surface/FrameCard";

interface GlassSlabProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Content to render inside the slab */
  children: React.ReactNode;
  /** Border radius (CSS value or token), defaults to 19px/card token */
  radius?: string;
  /** Intensity for glass refraction effect (default: 0.008) */
  intensity?: number;
  /** Optional wallpaper URL for glass background */
  wallpaperUrl?: string;
  /** Extra classes for the outer div */
  className?: string;
  /** Enable rim border? */
  rim?: boolean;
  /** Rim border CSS (default: 1.5px semi-transparent white) */
  rimStyle?: React.CSSProperties;
  /** Additional style for the outer div */
  style?: React.CSSProperties;
}

/**
 * GlassSlab
 * A reusable glassy card/rim effect with a refractive background, rim, and content slot.
 */
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
  // Default rim effect (border, can be customized via rimStyle)
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
      {/* Glassy refractive backdrop */}
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

      {/* Rim border/shadow effect */}
      {rim && (
        <div
          className="glass-slab__rim absolute inset-0"
          aria-hidden="true"
          style={defaultRim}
        />
      )}

      {/* Main content */}
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
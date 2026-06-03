import React, {useEffect, useState} from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type ShotDefinition = {
  id: string;
  title: string;
  start: number;
  duration: number;
  caption: string;
  asset: keyof AssetMap;
  chips?: string[];
  accent?: string;
};

type AssetMap = {
  wallpaper: string;
  appearance: string;
  persona: string;
  imports: string;
  thread: string;
};

const DEFAULT_ASSETS: AssetMap = {
  wallpaper: "/public/demo/codexify/personalized/wallpaper.png",
  appearance: "/public/demo/codexify/personalized/appearance.png",
  persona: "/public/demo/codexify/personalized/persona.png",
  imports: "/public/demo/codexify/personalized/imports.png",
  thread: "/public/demo/codexify/personalized/thread.png",
};

export const SHOT_MAP: ShotDefinition[] = [
  {
    id: "wallpaper-accent",
    title: "Wallpaper and Accent",
    start: 0,
    duration: 600,
    caption: "Make the workspace feel like yours.",
    asset: "appearance",
    chips: ["Wallpaper", "Accent", "Theme"],
    accent: "#92d7ff",
  },
  {
    id: "assistant-identity",
    title: "Assistant Identity",
    start: 600,
    duration: 600,
    caption: "Name the assistant. Shape the tone.",
    asset: "persona",
    chips: ["Name", "Persona", "Voice"],
    accent: "#d0b7ff",
  },
  {
    id: "imports",
    title: "Import Your Chats",
    start: 1200,
    duration: 600,
    caption: "Bring your own history into the workspace.",
    asset: "imports",
    chips: ["Imports", "Project", "Upload"],
    accent: "#8be6c4",
  },
  {
    id: "thread",
    title: "Open a Real Thread",
    start: 1800,
    duration: 600,
    caption: "Your chats stay readable as project material.",
    asset: "thread",
    chips: ["Thread", "Context", "Project"],
    accent: "#ffcf91",
  },
  {
    id: "end",
    title: "End Frame",
    start: 2400,
    duration: 600,
    caption: "Codexify, tuned to your workflow.",
    asset: "wallpaper",
    chips: ["Codexify", "Personalized"],
    accent: "#ffffff",
  },
];

const palette = {
  bg0: "#07111a",
  bg1: "#0b1622",
  bg2: "#162536",
  surface: "rgba(20, 30, 42, 0.66)",
  surfaceStrong: "rgba(19, 31, 45, 0.88)",
  border: "rgba(255,255,255,0.14)",
  borderStrong: "rgba(255,255,255,0.24)",
  text: "#f4f7fb",
  muted: "rgba(228,236,245,0.68)",
};

function useAssetAvailability(src: string | undefined) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!src) {
      setReady(false);
      return;
    }

    let cancelled = false;
    const image = new Image();
    image.onload = () => {
      if (!cancelled) setReady(true);
    };
    image.onerror = () => {
      if (!cancelled) setReady(false);
    };
    image.src = src;

    return () => {
      cancelled = true;
    };
  }, [src]);

  return ready;
}

function titleCase(text: string) {
  return text.replace(/\b\w/g, (char) => char.toUpperCase());
}

function Chip({
  label,
  accent = "#9cc4ff",
  index,
}: {
  label: string;
  accent?: string;
  index: number;
}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const rise = spring({
    frame: Math.max(0, frame - index * 3),
    fps,
    config: {damping: 18, stiffness: 120, mass: 0.7},
  });

  return (
    <div
      style={{
        padding: "10px 15px",
        borderRadius: 999,
        border: `1px solid ${palette.borderStrong}`,
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08))",
        boxShadow: "0 12px 30px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.2)",
        backdropFilter: "blur(18px)",
        color: palette.text,
        fontSize: 18,
        letterSpacing: "0.03em",
        transform: `translateY(${interpolate(rise, [0, 1], [18, 0])}px)`,
        opacity: rise,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(120deg, transparent 0%, ${accent}22 45%, transparent 85%)`,
        }}
      />
      <span style={{position: "relative", zIndex: 1}}>{titleCase(label)}</span>
    </div>
  );
}

function SceneFrame({
  shot,
  src,
}: {
  shot: ShotDefinition;
  src: string | undefined;
}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entry = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 120, mass: 0.7},
  });
  const assetReady = useAssetAvailability(src);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 20% 20%, ${shot.accent ?? "#8abeb7"}22 0%, transparent 38%), linear-gradient(180deg, ${palette.bg0}, ${palette.bg1} 42%, ${palette.bg2})`,
        color: palette.text,
        fontFamily:
          'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.35,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: 36,
          alignItems: "center",
          height: "100%",
          padding: "72px 84px",
          transform: `scale(${interpolate(entry, [0, 1], [0.98, 1])}) translateY(${interpolate(
            entry,
            [0, 1],
            [18, 0]
          )}px)`,
        }}
      >
        <div style={{display: "flex", flexDirection: "column", gap: 24}}>
          <div
            style={{
              fontSize: 15,
              letterSpacing: "0.28em",
              textTransform: "uppercase",
              color: palette.muted,
            }}
          >
            {shot.title}
          </div>

          <div
            style={{
              fontSize: 72,
              lineHeight: 0.96,
              fontWeight: 700,
              maxWidth: 820,
              textWrap: "balance",
            }}
          >
            {shot.caption}
          </div>

          <div style={{display: "flex", gap: 12, flexWrap: "wrap", marginTop: 4}}>
            {(shot.chips ?? []).map((chip, index) => (
              <Chip key={chip} label={chip} index={index} accent={shot.accent} />
            ))}
          </div>

          <div
            style={{
              marginTop: 12,
              maxWidth: 720,
              fontSize: 24,
              lineHeight: 1.5,
              color: palette.muted,
            }}
          >
            Record this as a self-contained 20-second segment, then splice it into the final edit.
          </div>
        </div>

        <div
          style={{
            position: "relative",
            borderRadius: 30,
            padding: 18,
            background: palette.surface,
            border: `1px solid ${palette.border}`,
            boxShadow: "0 28px 90px rgba(0,0,0,0.34)",
            backdropFilter: "blur(18px)",
          }}
        >
          <div
            style={{
              borderRadius: 22,
              overflow: "hidden",
              border: `1px solid ${palette.borderStrong}`,
              background: palette.surfaceStrong,
              minHeight: 520,
              display: "flex",
              alignItems: "stretch",
              justifyContent: "center",
              position: "relative",
            }}
          >
            {assetReady && src ? (
              <Img
                src={src}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  objectPosition: "center",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  minHeight: 520,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: 40,
                  gap: 18,
                  background:
                    "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                }}
              >
                <div
                  style={{
                    width: 110,
                    height: 110,
                    borderRadius: 30,
                    border: `1px solid ${palette.borderStrong}`,
                    background: `linear-gradient(180deg, ${shot.accent ?? "#9cc4ff"}44, rgba(255,255,255,0.06))`,
                    boxShadow: `inset 0 1px 0 rgba(255,255,255,0.2), 0 16px 44px rgba(0,0,0,0.24)`,
                  }}
                />
                <div
                  style={{
                    maxWidth: 460,
                    textAlign: "center",
                    fontSize: 28,
                    lineHeight: 1.4,
                    color: palette.text,
                  }}
                >
                  Drop your screenshot here later, or use this fallback panel while you prep.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

export default function CodexifyPersonalizedPresentation() {
  return (
    <AbsoluteFill style={{background: palette.bg0}}>
      {SHOT_MAP.map((shot) => (
        <Sequence key={shot.id} from={shot.start} durationInFrames={shot.duration}>
          <SceneFrame shot={shot} src={DEFAULT_ASSETS[shot.asset]} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}

import React, {useEffect, useMemo, useState} from "react";
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
	caption?: string;
	asset?: string;
	tokenChips?: string[];
	accent?: string;
	blur?: number;
};

type AssetMap = {
	dashboard: string;
	guardian: string;
	workspace: string;
	personaStudio: string;
	documents: string;
};

const DEFAULT_ASSETS: AssetMap = {
	dashboard: "/public/demo/codexify/dashboard.png",
	guardian: "/public/demo/codexify/guardian.png",
	workspace: "/public/demo/codexify/workspace.png",
	personaStudio: "/public/demo/codexify/persona-studio.png",
	documents: "/public/demo/codexify/documents.png",
};

export const SHOT_MAP: ShotDefinition[] = [
	{
		id: "shell",
		title: "The Shell",
		start: 0,
		duration: 150,
		caption: "A local-first workspace, built around the interface.",
		asset: "dashboard",
		accent: "#85d0ff",
	},
	{
		id: "geometry",
		title: "Glass Geometry",
		start: 150,
		duration: 210,
		caption: "Every surface follows the same visual law.",
		asset: "dashboard",
		tokenChips: ["radius", "bezel", "rim", "surface"],
		accent: "#8be6c4",
	},
	{
		id: "guardian",
		title: "Guardian",
		start: 360,
		duration: 240,
		caption: "Conversation stays primary.",
		asset: "guardian",
		accent: "#9cc4ff",
		blur: 10,
	},
	{
		id: "workspace",
		title: "Workspace",
		start: 600,
		duration: 300,
		caption: "A side surface for what you're actively holding.",
		asset: "workspace",
		tokenChips: ["Shelf", "Scratchpad", "Inspector"],
		accent: "#f1c58f",
	},
	{
		id: "personalization",
		title: "Personalization",
		start: 900,
		duration: 360,
		caption: "Profiles configure behavior without owning identity.",
		asset: "personaStudio",
		tokenChips: ["Identity", "Model", "Voice", "Tools", "Retrieval"],
		accent: "#c1b2ff",
	},
	{
		id: "continuity",
		title: "Continuity",
		start: 1260,
		duration: 300,
		caption: "Your materials stay within reach.",
		asset: "documents",
		tokenChips: ["Dashboard", "Documents", "Gallery"],
		accent: "#8fd5ff",
	},
	{
		id: "end",
		title: "End Frame",
		start: 1560,
		duration: 240,
		asset: "dashboard",
		accent: "#ffffff",
	},
];

const palette = {
	bg0: "#07111a",
	bg1: "#0b1622",
	bg2: "#162536",
	surface: "rgba(20, 30, 42, 0.58)",
	surfaceStrong: "rgba(19, 31, 45, 0.82)",
	border: "rgba(255,255,255,0.16)",
	borderStrong: "rgba(255,255,255,0.24)",
	text: "#f4f7fb",
	muted: "rgba(228,236,245,0.68)",
	chip: "rgba(255,255,255,0.12)",
};

const cardShadow = "0 28px 90px rgba(0,0,0,0.34)";

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

export const TokenChip: React.FC<{
	label: string;
	index: number;
	accent?: string;
}> = ({label, index, accent = "#9cc4ff"}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const rise = spring({
		frame: Math.max(0, frame - index * 4),
		fps,
		config: {damping: 18, stiffness: 110, mass: 0.7},
	});

	return (
		<div
			style={{
				padding: "10px 16px",
				borderRadius: 999,
				border: `1px solid ${palette.borderStrong}`,
				background: `linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.08))`,
				boxShadow: `0 12px 30px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.2)`,
				backdropFilter: "blur(18px)",
				color: palette.text,
				fontSize: 20,
				letterSpacing: "0.04em",
				textTransform: "uppercase",
				transform: `translateY(${interpolate(rise, [0, 1], [20, 0])}px) scale(${interpolate(
					rise,
					[0, 1],
					[0.94, 1]
				)})`,
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
			<span style={{position: "relative", zIndex: 1}}>{label}</span>
		</div>
	);
};

export const ShotCaption: React.FC<{
	title: string;
	body?: string;
	align?: "left" | "center";
}> = ({title, body, align = "left"}) => (
	<div
		style={{
			display: "flex",
			flexDirection: "column",
			gap: 10,
			maxWidth: align === "center" ? 760 : 560,
			textAlign: align,
		}}
	>
		<div
			style={{
				fontSize: 15,
				letterSpacing: "0.24em",
				textTransform: "uppercase",
				color: "rgba(234,241,247,0.52)",
			}}
		>
			{title}
		</div>
		{body ? (
			<div
				style={{
					fontSize: 32,
					lineHeight: 1.16,
					color: palette.text,
					fontWeight: 520,
				}}
			>
				{body}
			</div>
		) : null}
	</div>
);

export const SoftLightSweep: React.FC<{
	progress: number;
	accent?: string;
	opacity?: number;
}> = ({progress, accent = "#9cc4ff", opacity = 0.42}) => (
	<div
		style={{
			position: "absolute",
			top: "-15%",
			bottom: "-15%",
			width: "28%",
			left: `${interpolate(progress, [0, 1], [-18, 88])}%`,
			background: `linear-gradient(90deg, transparent 0%, ${accent} 50%, transparent 100%)`,
			filter: "blur(60px)",
			opacity,
			mixBlendMode: "screen",
			transform: "rotate(10deg)",
		}}
	/>
);

export const GlassStage: React.FC<{
	children: React.ReactNode;
	accent?: string;
}> = ({children, accent = "#8fd5ff"}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const driftX = interpolate(frame, [0, durationInFrames], [-16, 14]);
	const driftY = interpolate(frame, [0, durationInFrames], [10, -12]);

	return (
		<AbsoluteFill
			style={{
				background: `
					radial-gradient(circle at 18% 18%, ${accent}22 0%, transparent 28%),
					radial-gradient(circle at 78% 20%, rgba(255,255,255,0.08) 0%, transparent 22%),
					linear-gradient(160deg, ${palette.bg0} 0%, ${palette.bg1} 48%, ${palette.bg2} 100%)
				`,
				overflow: "hidden",
			}}
		>
			<div
				style={{
					position: "absolute",
					inset: -120,
					background:
						"linear-gradient(135deg, rgba(255,255,255,0.03) 0%, transparent 25%, rgba(255,255,255,0.02) 50%, transparent 75%)",
					transform: `translate(${driftX}px, ${driftY}px)`,
				}}
			/>
			<div
				style={{
					position: "absolute",
					inset: 42,
					borderRadius: 42,
					border: `1px solid ${palette.border}`,
					boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06)",
					opacity: 0.9,
				}}
			/>
			{children}
		</AbsoluteFill>
	);
};

export const FallbackCodexifyPanel: React.FC<{
	title: string;
	subtitle?: string;
	chips?: string[];
	accent?: string;
	variant?: "shell" | "guardian" | "workspace" | "persona" | "documents";
}> = ({title, subtitle, chips = [], accent = "#8fd5ff", variant = "shell"}) => {
	const frame = useCurrentFrame();
	const y = interpolate(frame, [0, 90], [18, 0], {extrapolateRight: "clamp"});

	const lines = useMemo(() => {
		if (variant === "guardian") {
			return [
				{w: "72%", h: 18},
				{w: "54%", h: 18},
				{w: "66%", h: 18},
				{w: "42%", h: 18},
			];
		}
		if (variant === "persona") {
			return [
				{w: "38%", h: 82},
				{w: "54%", h: 82},
				{w: "48%", h: 82},
			];
		}
		return [
			{w: "100%", h: 124},
			{w: "100%", h: 124},
			{w: "74%", h: 124},
		];
	}, [variant]);

	return (
		<div
			style={{
				width: "100%",
				height: "100%",
				borderRadius: 34,
				position: "relative",
				overflow: "hidden",
				background: `linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)), ${palette.surfaceStrong}`,
				border: `1px solid ${palette.borderStrong}`,
				boxShadow: `${cardShadow}, inset 0 1px 0 rgba(255,255,255,0.18)`,
				backdropFilter: "blur(22px)",
				transform: `translateY(${y}px)`,
			}}
		>
			<div
				style={{
					position: "absolute",
					inset: 0,
					background: `radial-gradient(circle at top left, ${accent}28 0%, transparent 34%)`,
				}}
			/>
			<div
				style={{
					position: "relative",
					zIndex: 1,
					display: "flex",
					flexDirection: "column",
					height: "100%",
					padding: "28px 30px",
					gap: 22,
				}}
			>
				<div style={{display: "flex", alignItems: "center", justifyContent: "space-between"}}>
					<div style={{display: "flex", flexDirection: "column", gap: 8}}>
						<div style={{fontSize: 30, color: palette.text, fontWeight: 560}}>{title}</div>
						{subtitle ? (
							<div style={{fontSize: 17, color: palette.muted, maxWidth: 600}}>{subtitle}</div>
						) : null}
					</div>
					<div
						style={{
							display: "flex",
							gap: 10,
							alignItems: "center",
						}}
					>
						{["#ff8b85", "#f1c15f", "#84d2a8"].map((color) => (
							<div
								key={color}
								style={{
									width: 12,
									height: 12,
									borderRadius: 999,
									background: color,
									opacity: 0.9,
								}}
							/>
						))}
					</div>
				</div>
				<div style={{display: "flex", gap: 10, flexWrap: "wrap"}}>
					{chips.map((chip, index) => (
						<TokenChip key={chip} label={chip} index={index} accent={accent} />
					))}
				</div>
				<div
					style={{
						display: "grid",
						gridTemplateColumns:
							variant === "persona" ? "1.1fr 1.8fr" : variant === "workspace" ? "1fr 1fr 1fr" : "1fr 1fr",
						gap: 16,
						flex: 1,
					}}
				>
					{lines.map((line, index) => (
						<div
							key={`${line.w}-${index}`}
							style={{
								borderRadius: 24,
								border: `1px solid rgba(255,255,255,0.1)`,
								background: "linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))",
								minHeight: line.h,
								width: line.w,
								padding: 18,
								display: "flex",
								flexDirection: "column",
								gap: 10,
							}}
						>
							<div
								style={{
									width: "38%",
									height: 12,
									borderRadius: 999,
									background: "rgba(255,255,255,0.16)",
								}}
							/>
							<div
								style={{
									width: "100%",
									height: 10,
									borderRadius: 999,
									background: "rgba(255,255,255,0.08)",
								}}
							/>
							<div
								style={{
									width: "82%",
									height: 10,
									borderRadius: 999,
									background: "rgba(255,255,255,0.08)",
								}}
							/>
						</div>
					))}
				</div>
			</div>
		</div>
	);
};

export const ScreenshotPlane: React.FC<{
	src?: string;
	accent?: string;
	title: string;
	subtitle?: string;
	fallbackChips?: string[];
	variant?: "shell" | "guardian" | "workspace" | "persona" | "documents";
	scale?: number;
	translateX?: number;
	translateY?: number;
	blur?: number;
}> = ({
	src,
	accent,
	title,
	subtitle,
	fallbackChips,
	variant,
	scale = 1,
	translateX = 0,
	translateY = 0,
	blur = 0,
}) => {
	const ready = useAssetAvailability(src);

	return (
		<div
			style={{
				position: "relative",
				width: "100%",
				height: "100%",
				borderRadius: 34,
				overflow: "hidden",
				border: `1px solid ${palette.borderStrong}`,
				boxShadow: `${cardShadow}, inset 0 1px 0 rgba(255,255,255,0.16)`,
				background: "rgba(14,22,32,0.72)",
				transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
			}}
		>
			<div
				style={{
					position: "absolute",
					inset: 0,
					borderRadius: 34,
					boxShadow: `inset 0 0 0 1px rgba(255,255,255,0.08), 0 0 0 1px ${accent ?? "#9cc4ff"}22`,
					pointerEvents: "none",
				}}
			/>
			{ready && src ? (
				<>
					<Img
						src={src}
						style={{
							width: "100%",
							height: "100%",
							objectFit: "cover",
							filter: `saturate(1.03) contrast(1.02) blur(${blur}px)`,
						}}
					/>
					<div
						style={{
							position: "absolute",
							inset: 0,
							background:
								"linear-gradient(180deg, rgba(255,255,255,0.05) 0%, transparent 18%, transparent 82%, rgba(7,17,26,0.12) 100%)",
						}}
					/>
				</>
			) : (
				<FallbackCodexifyPanel
					title={title}
					subtitle={subtitle}
					chips={fallbackChips}
					accent={accent}
					variant={variant}
				/>
			)}
		</div>
	);
};

export const MacroCrop: React.FC<{
	src?: string;
	accent?: string;
	title: string;
	subtitle?: string;
	fallbackChips?: string[];
	variant?: "shell" | "guardian" | "workspace" | "persona" | "documents";
	fromX?: number;
	toX?: number;
	fromY?: number;
	toY?: number;
	zoomFrom?: number;
	zoomTo?: number;
	blurFrom?: number;
	blurTo?: number;
}> = ({
	src,
	accent,
	title,
	subtitle,
	fallbackChips,
	variant,
	fromX = -80,
	toX = 80,
	fromY = -40,
	toY = 50,
	zoomFrom = 1.2,
	zoomTo = 1.42,
	blurFrom = 0,
	blurTo = 0,
}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const x = interpolate(frame, [0, durationInFrames], [fromX, toX]);
	const y = interpolate(frame, [0, durationInFrames], [fromY, toY]);
	const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo]);
	const blur = interpolate(frame, [0, durationInFrames], [blurFrom, blurTo]);

	return (
		<div
			style={{
				position: "absolute",
				inset: 0,
				padding: 72,
			}}
		>
			<ScreenshotPlane
				src={src}
				accent={accent}
				title={title}
				subtitle={subtitle}
				fallbackChips={fallbackChips}
				variant={variant}
				scale={scale}
				translateX={x}
				translateY={y}
				blur={blur}
			/>
		</div>
	);
};

const ShellShot: React.FC<{asset?: string; accent?: string}> = ({asset, accent}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const settle = spring({frame, fps, config: {damping: 20, stiffness: 80}});
	const scale = interpolate(settle, [0, 1], [0.94, 1]);

	return (
		<AbsoluteFill style={{padding: 92}}>
			<div style={{flex: 1, transform: `scale(${scale})`}}>
				<ScreenshotPlane
					src={asset}
					accent={accent}
					title="Codexify"
					subtitle="Rounded glass surfaces, workspace framing, and a calm shell hierarchy."
					fallbackChips={["Guardian", "Workspace", "Documents", "Persona Studio"]}
					variant="shell"
				/>
			</div>
		</AbsoluteFill>
	);
};

const GlassGeometryShot: React.FC<{asset?: string; accent?: string; chips?: string[]}> = ({
	asset,
	accent,
	chips,
}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const progress = interpolate(frame, [0, durationInFrames], [0, 1]);

	return (
		<AbsoluteFill>
			<MacroCrop
				src={asset}
				accent={accent}
				title="Codexify Shell"
				subtitle="Outer bezel, frame, rim, and layered surface depth."
				fallbackChips={chips}
				variant="shell"
				fromX={-120}
				toX={30}
				fromY={-50}
				toY={30}
				zoomFrom={1.34}
				zoomTo={1.58}
			/>
			<SoftLightSweep progress={progress} accent={accent} />
			<div
				style={{
					position: "absolute",
					left: 86,
					right: 86,
					bottom: 110,
					display: "flex",
					gap: 16,
					flexWrap: "wrap",
				}}
			>
				{chips?.map((chip, index) => (
					<TokenChip key={chip} label={chip} index={index} accent={accent} />
				))}
			</div>
		</AbsoluteFill>
	);
};

const GuardianShot: React.FC<{asset?: string; accent?: string; caption?: string}> = ({
	asset,
	accent,
	caption,
}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const focus = interpolate(frame, [0, 40, durationInFrames - 40, durationInFrames], [12, 2, 2, 10]);
	const shimmer = interpolate(frame, [0, durationInFrames], [0, 1]);

	return (
		<AbsoluteFill>
			<MacroCrop
				src={asset}
				accent={accent}
				title="Guardian"
				subtitle="Conversation surface with the message lane kept visually primary."
				fallbackChips={["Guardian", "Composer", "Thread Rail"]}
				variant="guardian"
				fromX={-90}
				toX={70}
				fromY={0}
				toY={-10}
				zoomFrom={1.18}
				zoomTo={1.35}
				blurFrom={focus}
				blurTo={focus}
			/>
			<SoftLightSweep progress={shimmer} accent={accent} opacity={0.28} />
			<div
				style={{
					position: "absolute",
					left: 110,
					bottom: 110,
					width: 280,
					height: 70,
					borderRadius: 20,
					border: `1px solid ${palette.border}`,
					background: "rgba(255,255,255,0.05)",
					boxShadow: "0 0 38px rgba(156,196,255,0.18)",
				}}
			/>
			<div style={{position: "absolute", left: 96, bottom: 84}}>
				<ShotCaption title="Guardian" body={caption} />
			</div>
		</AbsoluteFill>
	);
};

const WorkspaceShot: React.FC<{asset?: string; accent?: string; chips?: string[]; caption?: string}> = ({
	asset,
	accent,
	chips,
	caption,
}) => {
	const frame = useCurrentFrame();
	const leftX = interpolate(frame, [0, 120, 300], [0, -24, -12], {extrapolateRight: "clamp"});
	const centerX = interpolate(frame, [0, 120, 300], [0, 10, 0], {extrapolateRight: "clamp"});
	const rightX = interpolate(frame, [0, 120, 300], [0, 28, 12], {extrapolateRight: "clamp"});

	return (
		<AbsoluteFill style={{padding: 74}}>
			<ScreenshotPlane
				src={asset}
				accent={accent}
				title="Workspace"
				subtitle="Shelf, Scratchpad, and Inspector as layered side-surface behavior."
				fallbackChips={chips}
				variant="workspace"
				scale={1.06}
			/>
			<div
				style={{
					position: "absolute",
					top: 176,
					right: 138,
					width: 290,
					height: 520,
					transform: `translateX(${leftX}px)`,
				}}
			>
				<FallbackCodexifyPanel title="Shelf" subtitle="Held materials" accent="#e2b780" variant="workspace" />
			</div>
			<div
				style={{
					position: "absolute",
					top: 148,
					right: 96,
					width: 300,
					height: 560,
					transform: `translateX(${centerX}px)`,
				}}
			>
				<FallbackCodexifyPanel
					title="Scratchpad"
					subtitle="Active notes"
					accent="#8fd5ff"
					variant="workspace"
				/>
			</div>
			<div
				style={{
					position: "absolute",
					top: 208,
					right: 36,
					width: 280,
					height: 480,
					transform: `translateX(${rightX}px)`,
				}}
			>
				<FallbackCodexifyPanel
					title="Inspector"
					subtitle="Focused context"
					accent="#ccb3ff"
					variant="workspace"
				/>
			</div>
			<div style={{position: "absolute", left: 92, bottom: 84}}>
				<ShotCaption title="Workspace" body={caption} />
			</div>
		</AbsoluteFill>
	);
};

const PersonalizationShot: React.FC<{
	asset?: string;
	accent?: string;
	chips?: string[];
	caption?: string;
}> = ({asset, accent, chips, caption}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const sweep = interpolate(frame, [0, durationInFrames], [0, 1]);

	return (
		<AbsoluteFill>
			<MacroCrop
				src={asset}
				accent={accent}
				title="Persona Studio"
				subtitle="Identity, model, voice, retrieval, and tool configuration surfaces."
				fallbackChips={chips}
				variant="persona"
				fromX={-40}
				toX={36}
				fromY={-20}
				toY={14}
				zoomFrom={1.04}
				zoomTo={1.2}
			/>
			<SoftLightSweep progress={sweep} accent={accent} opacity={0.34} />
			<div
				style={{
					position: "absolute",
					left: 94,
					top: 120,
					display: "flex",
					gap: 14,
					flexWrap: "wrap",
					maxWidth: 860,
				}}
			>
				{chips?.map((chip, index) => (
					<TokenChip key={chip} label={chip} index={index} accent={accent} />
				))}
			</div>
			<div style={{position: "absolute", left: 94, bottom: 92}}>
				<ShotCaption title="Personalization" body={caption} />
			</div>
		</AbsoluteFill>
	);
};

const ContinuityShot: React.FC<{assets: AssetMap; accent?: string; caption?: string}> = ({
	assets,
	accent,
	caption,
}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const progress = interpolate(frame, [0, durationInFrames], [0, 1]);

	return (
		<AbsoluteFill style={{padding: 82}}>
			<div style={{display: "grid", gridTemplateColumns: "1.08fr 0.92fr", gap: 24, flex: 1}}>
				<div style={{transform: `translateY(${interpolate(progress, [0, 1], [26, 0])}px)`}}>
					<ScreenshotPlane
						src={assets.dashboard}
						accent={accent}
						title="Dashboard"
						subtitle="Entry surface"
						fallbackChips={["Dashboard"]}
						variant="shell"
					/>
				</div>
				<div style={{display: "grid", gridTemplateRows: "1fr 1fr", gap: 24}}>
					<div style={{transform: `translateX(${interpolate(progress, [0, 1], [30, 0])}px)`}}>
						<ScreenshotPlane
							src={assets.documents}
							accent="#f1c58f"
							title="Documents"
							subtitle="Working material"
							fallbackChips={["Documents"]}
							variant="documents"
						/>
					</div>
					<div style={{transform: `translateX(${interpolate(progress, [0, 1], [50, 0])}px)`}}>
						<FallbackCodexifyPanel
							title="Gallery"
							subtitle="Visual materials remain nearby."
							accent="#9fd6ff"
							chips={["Gallery", "Recent", "Media"]}
							variant="documents"
						/>
					</div>
				</div>
			</div>
			<div style={{position: "absolute", left: 96, bottom: 84}}>
				<ShotCaption title="Continuity" body={caption} />
			</div>
		</AbsoluteFill>
	);
};

const EndFrameShot: React.FC<{asset?: string; accent?: string}> = ({asset, accent}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const rise = spring({frame, fps, config: {damping: 20, stiffness: 90}});

	return (
		<AbsoluteFill style={{padding: 90}}>
			<div style={{flex: 1, opacity: 0.94}}>
				<ScreenshotPlane
					src={asset}
					accent={accent}
					title="Codexify"
					subtitle="Interface study"
					fallbackChips={["Codexify"]}
					variant="shell"
					scale={1.01}
				/>
			</div>
			<div
				style={{
					position: "absolute",
					left: 0,
					right: 0,
					bottom: 110,
					display: "flex",
					flexDirection: "column",
					alignItems: "center",
					gap: 10,
					transform: `translateY(${interpolate(rise, [0, 1], [18, 0])}px)`,
					opacity: rise,
				}}
			>
				<div style={{fontSize: 18, color: "rgba(234,241,247,0.58)", letterSpacing: "0.26em"}}>
					CODEXIFY
				</div>
				<div style={{fontSize: 28, color: palette.text}}>Interface study</div>
			</div>
		</AbsoluteFill>
	);
};

export const CodexifyInterfaceCloseups: React.FC<{
	assets?: Partial<AssetMap>;
}> = ({assets}) => {
	const resolvedAssets = {...DEFAULT_ASSETS, ...assets};

	return (
		<GlassStage accent="#8fd5ff">
			{SHOT_MAP.map((shot) => {
				const assetKey = shot.asset as keyof AssetMap | undefined;
				const asset = assetKey ? resolvedAssets[assetKey] : undefined;

				return (
					<Sequence key={shot.id} from={shot.start} durationInFrames={shot.duration}>
						{shot.id === "shell" ? <ShellShot asset={asset} accent={shot.accent} /> : null}
						{shot.id === "geometry" ? (
							<GlassGeometryShot asset={asset} accent={shot.accent} chips={shot.tokenChips} />
						) : null}
						{shot.id === "guardian" ? (
							<GuardianShot asset={asset} accent={shot.accent} caption={shot.caption} />
						) : null}
						{shot.id === "workspace" ? (
							<WorkspaceShot
								asset={asset}
								accent={shot.accent}
								chips={shot.tokenChips}
								caption={shot.caption}
							/>
						) : null}
						{shot.id === "personalization" ? (
							<PersonalizationShot
								asset={asset}
								accent={shot.accent}
								chips={shot.tokenChips}
								caption={shot.caption}
							/>
						) : null}
						{shot.id === "continuity" ? (
							<ContinuityShot assets={resolvedAssets} accent={shot.accent} caption={shot.caption} />
						) : null}
						{shot.id === "end" ? <EndFrameShot asset={asset} accent={shot.accent} /> : null}
					</Sequence>
				);
			})}
		</GlassStage>
	);
};

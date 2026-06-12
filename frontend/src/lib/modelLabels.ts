type ModelLabelSource = {
  profileDisplayName?: string | null;
  catalogDisplayName?: string | null;
  modelId?: string | null;
  rawId?: string | null;
};

const MODEL_LABEL_NOISE_TOKENS = new Set([
  "community",
  "instruct",
  "instruction",
  "model",
  "models",
  "mlx",
  "repo",
  "tuned",
  "weights",
  "checkpoint",
  "merged",
  "adapter",
  "local",
  "final",
  "it",
]);

const MODEL_LABEL_DROP_SUFFIX_TOKENS = new Set([
  "4bit",
  "8bit",
  "16bit",
  "32bit",
  "fp16",
  "bf16",
  "int4",
  "int8",
  "q4",
  "q8",
  "gguf",
  "ggml",
  "safetensors",
  "bin",
  "pt",
]);

function normalizeToken(token: string): string | null {
  const trimmed = token.trim();
  if (!trimmed) return null;

  const lower = trimmed.toLowerCase();
  if (MODEL_LABEL_NOISE_TOKENS.has(lower)) {
    return null;
  }
  if (/^\d+$/.test(trimmed) || /^\d+\.\d+$/.test(trimmed)) {
    return trimmed;
  }
  if (/^e?\d+b$/i.test(trimmed)) {
    return trimmed.toUpperCase();
  }
  if (/^q\d+[a-z0-9_]*$/i.test(trimmed)) {
    return trimmed.toUpperCase();
  }
  if (/^(?:fp|bf|int)\d+$/i.test(trimmed)) {
    return trimmed.toUpperCase();
  }
  if (lower === "qat" || lower === "unsloth" || lower === "awq" || lower === "gptq") {
    return trimmed.toUpperCase();
  }
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}

function stripSuffixNoise(value: string): string {
  let candidate = value.trim();
  let previous = "";

  while (candidate && candidate !== previous) {
    previous = candidate;
    candidate = candidate.replace(
      new RegExp(
        String.raw`(?:[._-])(?:${Array.from(MODEL_LABEL_DROP_SUFFIX_TOKENS).join("|")})$`,
        "i"
      ),
      ""
    );
  }

  return candidate.trim();
}

function isArtifactLikeLabel(value: string): boolean {
  if (/[\\/]/.test(value)) return true;
  if (/(?:^|[._-])(?:4bit|8bit|16bit|32bit|fp16|bf16|int4|int8|q4|q8|qat|awq|gptq|gguf|ggml)(?:$|[._-])/i.test(value)) {
    return true;
  }
  return /\b(?:instruct|instruction|tuned|checkpoint|weights|merged|adapter|community|mlx)\b/i.test(
    value
  );
}

export function shortenModelLabel(rawLabel: string): string {
  const trimmed = rawLabel.trim();
  if (!trimmed) return "";

  const pathLike = trimmed.split(/[\\/]+/).filter(Boolean).pop() ?? trimmed;
  const strippedExtension = pathLike.replace(/\.[a-z0-9]+$/i, "");
  const withoutSuffixNoise = stripSuffixNoise(strippedExtension);
  const tokens = withoutSuffixNoise
    .split(/[^A-Za-z0-9.]+/)
    .map(normalizeToken)
    .filter((token): token is string => Boolean(token));

  const label = tokens.join(" ").replace(/\s+/g, " ").trim();
  return label || trimmed;
}

export function resolveModelDisplayLabel(source: ModelLabelSource): string {
  const candidates = [
    source.profileDisplayName,
    source.catalogDisplayName,
    source.modelId,
    source.rawId,
  ];

  for (const candidate of candidates) {
    const normalized = typeof candidate === "string" ? candidate.trim() : "";
    if (!normalized) continue;
    if (isArtifactLikeLabel(normalized)) {
      const short = shortenModelLabel(normalized);
      if (short) return short;
    }
    return normalized;
  }

  return "";
}

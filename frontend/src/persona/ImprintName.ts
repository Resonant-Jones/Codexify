// imprintName.ts
// Zero-deps. Deterministic. Vibe-aware syllabic name generator.

type MarkerType = 'lexical' | 'motivation' | 'cognitive' | 'emotional' | 'evolution';

export interface MarkerSignal {
  type: MarkerType;
  confidence: number; // 0..1
  tag: string;        // e.g. 'slang', 'metaphor_thinker', 'banter', 'self_dev', 'planner'
}

type Vibe =
  | 'soft'     // warm, rounded, gentle
  | 'bright'   // light, open, airy
  | 'crisp'    // precise, modern, techy
  | 'deep'     // resonant, nocturne
  | 'mythic'   // lyrical, slightly archaic
  | 'kinetic'; // punchy, high-energy

interface Options {
  seed?: string;              // for determinism
  minLen?: number;            // min characters
  maxLen?: number;            // max characters
  forms?: string[];           // syllable blueprints, e.g. ["CV", "CVC", "CVCV"]
  count?: number;             // how many candidates to return before ranking
  shortlist?: number;         // how many to keep after ranking
  allowHyphen?: boolean;      // e.g. "Ari-Len"
  preferTwoWords?: boolean;   // try "Ari Len" style (title-cased)
}

const DEFAULT_OPTS: Options = {
  minLen: 4,
  maxLen: 8,
  count: 64,
  shortlist: 7,
  forms: ["CV", "CVC", "CVCV", "CVVC", "VCV", "CVCCV", "CVCVC"],
};

// --- Tiny seeded PRNG
function xmur3(str: string) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}
function mulberry32(a: number) {
  return function() {
    let t = (a += 0x6D2B79F5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function rngFromSeed(seed: string | undefined) {
  const s = xmur3(seed ?? Math.random().toString())();
  return mulberry32(s);
}

// --- Phoneme pools by vibe
// (Small curated sets to keep outputs pronounceable and brandable.)
const VOWELS = {
  soft:   ["a","e","i","o","u","aa","ee","ai","oa","io","ue"],
  bright: ["a","e","i","o","u","ae","ei","ia","io","ou"],
  crisp:  ["a","e","i","o","u","y","ia","io","ui"],
  deep:   ["a","o","u","au","oa","uu","uo","aa"],
  mythic: ["a","e","i","o","u","ae","ea","eo","iu","ou"],
  kinetic:["a","e","i","o","u","ai","oi","ia"],
};

const ONSETS = {
  soft:   ["m","n","l","r","v","w","y","h","s","sh"],
  bright: ["l","r","s","v","f","h","n","y","z"],
  crisp:  ["k","t","p","s","c","z","x","v","f","n","l","r"],
  deep:   ["v","r","n","m","d","g","gh","vr","dr","gr"],
  mythic: ["th","l","r","v","n","m","s","fr","vl","rh"],
  kinetic:["k","t","p","b","d","g","cr","tr","pr","br","dr","gr","sk","sp","st"],
};

const CODAS = {
  soft:   ["","m","n","l","r","s","sh"],
  bright: ["","n","l","r","s"],
  crisp:  ["","t","k","x","s","z","n","l","r","ct"],
  deep:   ["","m","n","r","g","nd","rg","rm"],
  mythic: ["","n","l","r","s","th","rn","iel","or"],
  kinetic:["","t","k","p","n","r","s","st","sk"],
};

// Some clusters to discourage (harsh or hard-to-say across dialects)
const BAD_CLUSTERS = [
  "xx","kkk","jj","qq","cg","gc","dl","td","ptl","nnn","rrr","lll","zs","sz","zx","xk","kx","ghh"
];

// Simple blacklist of unintended words/substrings (extend as you like)
const BLACKLIST = ["ass","cum","sex","shit","fuck","tit","cunt","prn"];

// --- Vibe inference from markers
export function vibeFromMarkers(signals: MarkerSignal[]): Vibe {
  // Weight tags → vibes
  let scores: Record<Vibe, number> = { soft:0, bright:0, crisp:0, deep:0, mythic:0, kinetic:0 };

  for (const s of signals) {
    const w = s.confidence || 0.5;
    switch (s.tag) {
      case 'banter': scores.bright += 1*w; scores.kinetic += 0.5*w; break;
      case 'slang': scores.kinetic += 1*w; scores.bright += 0.5*w; break;
      case 'planner': scores.crisp += 1*w; break;
      case 'metaphor_thinker': scores.mythic += 1*w; scores.deep += 0.5*w; break;
      case 'meaning_seeker': scores.soft += 1*w; scores.deep += 0.5*w; break;
      case 'self_dev': scores.bright += 0.7*w; scores.soft += 0.3*w; break;
      case 'precision': scores.crisp += 1*w; break;
      case 'nocturne': scores.deep += 1*w; break;
      case 'archaic_tone': scores.mythic += 1*w; break;
      default:
        // map from type if tag unknown
        if (s.type === 'emotional') scores.soft += 0.4*w;
        if (s.type === 'cognitive') scores.crisp += 0.3*w;
        if (s.type === 'motivation') scores.bright += 0.3*w;
    }
  }
  // Pick max
  return (Object.entries(scores).sort((a,b)=>b[1]-a[1])[0]?.[0] as Vibe) || 'soft';
}

// --- Core generator
export function generateImprintNames(
  signals: MarkerSignal[],
  opts: Partial<Options> = {}
): {name: string, score: number, vibe: Vibe}[] {
  const settings = { ...DEFAULT_OPTS, ...opts };
  const vibe: Vibe = vibeFromMarkers(signals);
  const rng = rngFromSeed(settings.seed ?? 'codexify');

  const vowels = VOWELS[vibe];
  const onsets = ONSETS[vibe];
  const codas = CODAS[vibe];

  // Syllable blueprints: C=onset, V=vowel nucleus, K=coda
  const forms = settings.forms!;

  const candidates = new Set<string>();
  while (candidates.size < settings.count!) {
    const form = forms[Math.floor(rng()*forms.length)];
    let out = '';
    for (const ch of form) {
      if (ch === 'C') out += pick(onsets, rng);
      else if (ch === 'V') out += pick(vowels, rng);
      else if (ch === 'K') out += pick(codas, rng);
    }
    out = postprocess(out, vibe, rng);
    if (valid(out, settings)) candidates.add(out);
  }

  const scored = Array.from(candidates).map(name => ({
    name: stylize(name, settings, rng),
    score: scoreName(name, vibe),
    vibe
  }));

  scored.sort((a,b)=>b.score - a.score);
  return scored.slice(0, settings.shortlist);
}

// --- Helpers

function pick<T>(arr: T[], rng: ()=>number): T {
  return arr[Math.floor(rng()*arr.length)];
}

// Make it prettier & more pronounceable
function postprocess(raw: string, vibe: Vibe, rng: ()=>number): string {
  let s = raw;

  // Collapse duplicates like "ll", "rrr" → keep max two
  s = s.replace(/([bcdfghjklmnpqrstvwxyz])\1{2,}/g, '$1$1');

  // Ease harsh clusters
  for (const bad of BAD_CLUSTERS) {
    if (s.includes(bad)) {
      s = s.replace(bad, bad[0]); // crude soften
    }
  }

  // Optional vowel harmony-ish tweak: prefer similar vowels in sequence
  s = s.replace(/([aeiouy]{2,})/g, (m) => {
    if (vibe === 'soft' || vibe === 'deep') return m[0].repeat(1); // simplify long runs
    return m;
  });

  // Final touch: sometimes add or trim a soft coda for cadence
  if ((vibe === 'soft' || vibe === 'mythic') && rng() < 0.25) s += 'a';
  if (vibe === 'crisp' && rng() < 0.25 && !/[ktpsx]$/.test(s)) s += pick(['k','t','x'], rng);

  return s;
}

function valid(s: string, opts: Options): boolean {
  if (s.length < (opts.minLen || 0) || s.length > (opts.maxLen || 99)) return false;
  const lower = s.toLowerCase();
  if (BLACKLIST.some(b => lower.includes(b))) return false;
  // Avoid pure dictionary-ish endings that make it too word-like
  if (/\b(data|bot|tech|app|ai)$/.test(lower)) return false;
  return true;
}

// Score for euphony + vibe alignment (simple heuristic)
function scoreName(s: string, vibe: Vibe): number {
  const lower = s.toLowerCase();

  // Baseline: prefer 5–7 letters
  let score = 1 - Math.abs(6 - lower.length) / 6;

  // Sonority: prefer alternating C/V patterns
  const cv = lower.replace(/[aeiouy]/g,'V').replace(/[^V]/g,'C');
  const alternations = (cv.match(/CV|VC/g) || []).length;
  score += alternations * 0.1;

  // Vibe-specific bonuses
  if (vibe === 'crisp' && /[ktpx]$/.test(lower)) score += 0.3;
  if (vibe === 'soft' && /[aeiou]$/.test(lower)) score += 0.3;
  if (vibe === 'deep' && /(ar|or|um|un)$/.test(lower)) score += 0.25;
  if (vibe === 'bright' && /(ia|io|ae)$/.test(lower)) score += 0.25;
  if (vibe === 'mythic' && /(el|ion|or|is)$/.test(lower)) score += 0.25;
  if (vibe === 'kinetic' && /(x|k|o)$/.test(lower)) score += 0.2;

  // Penalize ugly clusters
  for (const bad of BAD_CLUSTERS) if (lower.includes(bad)) score -= 0.4;

  return score;
}

function stylize(s: string, opts: Options, rng: ()=>number): string {
  // Title-case single token
  let out = s[0].toUpperCase() + s.slice(1);

  // Optional hyphen / two-word variants (rare)
  if (opts.allowHyphen && rng() < 0.08 && out.length > 6) {
    const cut = Math.max(3, Math.min(out.length-3, Math.floor(out.length/2)));
    out = out.slice(0, cut) + '-' + out.slice(cut);
  }
  if (opts.preferTwoWords && rng() < 0.12 && out.length >= 6) {
    const cut = Math.max(3, Math.min(out.length-3, Math.floor(out.length/2)));
    out = out.slice(0, cut) + ' ' + out.slice(cut);
  }
  return out;
}

// --- Public: one-shot convenience using your marker pipeline
export function generateNameFromMarkers(
  signals: MarkerSignal[],
  opts: Partial<Options> = {}
): string {
  const list = generateImprintNames(signals, opts);
  // Pick top; you could also roulette-weight by score
  return (list[0]?.name) || "Ari"; // fallback unlikely to hit
}

# Whoosh'd Gemma tokenizer qualification identity reconciliation

**Date:** 2026-08-09
**Execution lane:** architecture-impact
**Task kind:** qualification-proof amendment (Stage 2D evidence reconciliation / Stage 2F.1b prerequisite)
**Conclusion:** **qualified-supplemental**, binds the missing Stage 2F
`tokenizer.identity_fingerprint` to the exact Stage 2D tokenizer artifact. This
does not expand the Stage 2D qualification.

> This supplemental proof does not expand the Stage 2D qualification to:
> - other Gemma models;
> - other quantizations;
> - other tokenizer artifacts;
> - other templates;
> - other MLX-VLM versions;
> - other runtime adapters;
> - Whoosh'd generally.
>
> It only makes one already-qualified identity dimension machine-readable
> under the later Stage 2F contract.

## Purpose

Bind the exact Stage 2D tokenizer evidence to the exact
`tokenizer.identity_fingerprint` that the Stage 2F.1a Whoosh'd producer
(`d08e3261d8ed2217b9c258bb783138fc6a06df9f`) emits for the same artifact,
without changing the Stage 2D qualification and without rerunning any model
generation. This supplemental proof exists so that the Stage 2F.1b Codexify
consumer can build a complete machine-readable qualification record for the
exact target Stage 2D already qualified.

## Parent Stage 2D Proof

- Path: `docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md`
- Codexify commit: `f20858a7b19f2a9949729e94f7c9b1bb7f5b0f47`
- Conclusion: **qualified**, for the exact proof identity recorded in that receipt only.

The Stage 2D receipt is preserved as immutable historical evidence. This
supplemental proof explicitly references it as its parent proof and makes
no change to its content.

## Why Reconciliation Was Required

Stage 2F's machine-readable attestation identity requires, for the
`tokenizer` material field:

```text
tokenizer: {
  implementation: str,
  identity_fingerprint: str,   # required when material
}
```

The Stage 2F.1a Whoosh'd producer computes `identity_fingerprint` from the
parsed `tokenizer_config.json` via a documented canonical re-serialization
(see §Producer Tokenizer Identity Semantics below). The Stage 2D receipt
recorded the **raw-file SHA-256** of `tokenizer_config.json` but did not
record the producer's canonical-re-serialization SHA-256. A raw-file SHA
and the producer's canonical identity fingerprint are not interchangeable
(they are computed over different byte streams: raw file vs. compact
sorted-key JSON re-serialization of the parsed dict).

Stage 2F.1b correctly stopped at the explicit evidence-completeness gate.
This supplemental proof pins the missing `tokenizer.identity_fingerprint`
value with a full evidence map and byte-exact reproduction, so Stage 2F.1b
can resume.

## Scope

In scope:

- Reading the Stage 2D receipt and the producer's tokenizer-identity logic.
- Reproducing the raw SHA-256 of every file Stage 2D recorded as pinned.
- Constructing the exact canonical tokenizer identity document that the
  Stage 2F.1a producer would construct for the Stage 2D qualified target.
- Reproducing the resulting fingerprint in two independent ways and
  confirming byte-for-byte equality.
- Documenting the producer's algorithm precisely.

Out of scope:

- Any change to the Stage 2D receipt.
- Any change to Whoosh'd source, models, tokenizer files, configs, or
  dependencies.
- Any model generation, requalification, or A/B/C/D probe.
- Any new qualification claim beyond the Stage 2D qualification scope.
- Any new Whoosh'd lifecycle state, capability flag, runtime protocol
  token, or release-support claim.
- Any Codexify runtime code, comparator, or qualification record
  (these belong to the resumed Stage 2F.1b).

## Exact Qualified Target

Identical to the Stage 2D receipt:

| Dimension | Stage 2D value |
| --- | --- |
| Public invocation alias | `gemma-4-12b-it-qat-4bit` |
| Resolved model identity | `mlx-community/gemma-4-12B-it-qat-4bit` |
| Resolved artifact directory | `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit` |
| Runtime / adapter | `mlx_vlm` / `mlx-vlm` |
| Whoosh'd version | `0.1.0rc1` |
| Serving packages | `mlx-vlm 0.6.2`; `llguidance 1.7.6` |
| Tokenizer class | `GemmaTokenizer` |
| Quantization | QAT 4-bit (`bits:4, group_size:64, affine`) |
| Strict structured transport | `response_format.type: json_schema` via llguidance JSON-Schema logits processor; protocol version `model-turn.strict-json-schema.v1` |

## Governing Stage 2F Identity Contract

| Source | Identity requirement |
| --- | --- |
| `docs/architecture/whooshd-runtime-qualification-attestation-contract.md` § V1 canonical identity document | `tokenizer` is required; `implementation` is the class identifier; `identity_fingerprint` is required when material. |
| Same document § Safe/Bounded Representation | "A template or tokenizer fingerprint establishes identity without returning content." |
| Same document § Canonical JSON v1 rules | Object keys sorted lexicographically; NFC normalization of string values and keys before serialization; compact JSON; UTF-8; `ensure_ascii=false`; no NaN/Infinity; reject unordered sets. The producer's tokenizer sub-fingerprint uses a **narrower** canonical structure (sorted keys + compact separators + UTF-8) under this contract — see §Producer Tokenizer Identity Semantics below. |

## Whoosh'd Producer Version

- Repository: `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd`
- `HEAD`: `d08e3261d8ed2217b9c258bb783138fc6a06df9f`
- Branch: `codex/cwc-007-control-error-contract`
- Pre-existing untracked `.venv311/` only, left untouched.
- Verified ancestor of `d08e3261d8ed2217b9c258bb783138fc6a06df9f`: OK.

No uncommitted source changes are present in the Whoosh'd working tree.

## Producer Tokenizer Identity Semantics

The producer is read from `whooshd/qualification_attestation.py`,
commit `d08e3261d8ed2217b9c258bb783138fc6a06df9f`.

### Producing function and seam

- Function: `collect_mlx_vlm_target_material(...)` (line 339).
- Sub-fingerprint construction: lines 367–370.
- Material dict key produced for the v1 attestation: `"tokenizer"`
  (assigned lines 389–392).
- Outer container for the sub-fingerprint: `RuntimeQualificationAttestation.tokenizer`,
  a typed object with `implementation: Optional[str]` and
  `identity_fingerprint: Optional[str]` (lines 60–64).

### Material structured fields

The producer emits exactly two fields:

| Field | Source | Type |
| --- | --- | --- |
| `tokenizer.implementation` | `tokenizer_config.get("tokenizer_class")` | `str` (or `None`) |
| `tokenizer.identity_fingerprint` | producer-computed; see algorithm below | `str` (or `None`) |

Both fields are independently `None`able. The attestation is incomplete
(and `material_identity()` returns `None`) if either required-for-material
field is `None` or otherwise fails the global canonicalizer's
`_valid_evidence` check.

### Source file

- `model_path / "tokenizer_config.json"`
- Read via `_read_small_json(path)`: `json.loads(path.read_text(encoding="utf-8"))`.
- Bounded to dicts smaller than `_SAFE_FILE_MAX_BYTES` (2 MiB); larger or
  unreadable files yield `None` and the fingerprint is not emitted.
- The Stage 2D artifact's `tokenizer_config.json` is 2 747 bytes, well
  under the limit, so it is read in full.

### Normalization rules (narrower than the global canonicalizer)

The producer's tokenizer sub-fingerprint does **not** apply the global
`whooshd.qualification-attestation.canonical-json.v1` ruleset (NFC key
normalization, keyset completeness check, placeholder rejection). It uses
a narrower structure because the tokenizer sub-fingerprint is not a
qualification-grade identity by itself — it is one bounded component that
the global canonicalizer later folds into a complete identity. The
narrower structure is:

1. Parse the JSON file as UTF-8 text via stdlib `json.loads`.
2. Serialize the parsed dict with stdlib `json.dumps`:
   - `ensure_ascii=False`
   - `sort_keys=True`
   - `separators=(",", ":")`
   - `allow_nan` defaults to True (not set explicitly by the producer).
     Stage 2D's `tokenizer_config.json` does not contain `NaN` or
     `Infinity` values (verified by re-parse), so this is moot for the
     Stage 2D target. The Stage 2F global canonicalizer applies
     `allow_nan=False` at the outer attestation layer; that is a separate
     contract.
3. Emit `None` if the parsed dict is empty (falsy); otherwise fingerprint.

### Hashing algorithm and serialized form

- `fingerprint_text(s)` (line 248): returns `f"sha256:{hashlib.sha256(s.encode('utf-8')).hexdigest()}"`.
- Hash input: UTF-8 encoding of the canonical re-serialization.
- Algorithm: SHA-256.
- Serialized form: `sha256:<64 lowercase hexadecimal characters>`.

## Material Input Evidence Map

| Producer material input | Source of current value | Stage 2D evidence binding | Status |
| --- | --- | --- | --- |
| `tokenizer.implementation` | `tokenizer_config.json` field `tokenizer_class` | Stage 2D receipt, "Tokenizer identity" row: `GemmaTokenizer` | Directly pinned by Stage 2D narrative evidence; the parsed dict's `tokenizer_class` value is the source for the producer's emission |
| `tokenizer.identity_fingerprint` | SHA-256 over the canonical re-serialization of the parsed `tokenizer_config.json` | Stage 2D raw-file SHA `a4260621db48fa22f2b09ce3ba5ad0ec0cc0e032aa702e3ab743a0bc9d6e1d06` pins the same source file; canonical re-serialization of that file's parsed dict is content-equivalent | Transitively pinned via the immutable Stage 2D artifact (same `tokenizer_config.json` file, byte-exact reproduction of the raw SHA) |
| Source file path itself (`/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit/tokenizer_config.json`) | Local filesystem | Stage 2D "Resolved artifact" row pinned the parent directory; the artifact is the immutable boundary (no `snapshots/` or `refs/` subdirectory); every other raw-file SHA in Stage 2D reproduces byte-exact (see §Stage 2D Raw Evidence Reproduction) | Transitively pinned |

The fingerprint is **content-binding**, not file-binding. The producer
deliberately discards the source bytes and emits a content-equivalent
canonical fingerprint — this is endorsed by the Stage 2F contract
§ Safe/Bounded Representation: *"A template or tokenizer fingerprint
establishes identity without returning content."* Two distinct source
files with the same parsed dict would produce the same fingerprint; that
is the contract's intended semantic.

No producer material input is "not pinned". The implementation may
proceed.

## Stage 2D Raw Evidence Reproduction

Recomputed every raw-file SHA Stage 2D recorded, on the exact files at the
exact Stage 2D-pinned path, using the exact algorithm Stage 2D used
(SHA-256 over the raw file bytes).

```text
shasum -a 256 <file>
```

| File | Stage 2D receipt | Recomputed | Match |
| --- | --- | --- | --- |
| `config.json` | `fe091f98e6f7e5e80461bd8ec7ced6d87ac16987586239386ed44b82ecbc2b12` | `fe091f98e6f7e5e80461bd8ec7ced6d87ac16987586239386ed44b82ecbc2b12` | ✓ |
| `tokenizer_config.json` | `a4260621db48fa22f2b09ce3ba5ad0ec0cc0e032aa702e3ab743a0bc9d6e1d06` | `a4260621db48fa22f2b09ce3ba5ad0ec0cc0e032aa702e3ab743a0bc9d6e1d06` | ✓ |
| `generation_config.json` | `a8349d9bd64cc5841297fcb5002f0fdc4749c473c8f1b10ea337f9ce4ee7014e` | `a8349d9bd64cc5841297fcb5002f0fdc4749c473c8f1b10ea337f9ce4ee7014e` | ✓ |
| `chat_template.jinja` | `36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0` | `36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0` | ✓ |
| `model.safetensors.index.json` | `b87c93774de5d13ca9d0e21b045793e42e5df032fb5e7622212524f56f9695f2` | `b87c93774de5d13ca9d0e21b045793e42e5df032fb5e7622212524f56f9695f2` | ✓ |

All five reproduce exactly. No current file has drifted from Stage 2D
evidence. The local artifact is byte-identical to the one Stage 2D
qualified.

## Artifact / Revision Binding

The Stage 2D receipt states: *"the flattened local directory exposed no HF
revision/snapshot commit."* The artifact directory
`/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`
contains no `snapshots/` or `refs/` subdirectory; it is a flat directory
of files. The directory name is the only identifier; there is no HF
revision pointer or content-addressed snapshot hash to bind to.

The artifact boundary used by this proof is therefore:

- The directory is the immutable artifact boundary, by Stage 2D evidence
  (Stage 2D recorded the exact directory path and pinned five files
  inside it via SHA-256; the present task re-pinned all five files
  byte-exactly).
- No mutable alias or path is treated as immutable identity: the path is
  used **only** as a way to locate the files that Stage 2D explicitly
  pinned by content hash. If any file's content hash ever diverges from
  Stage 2D, this binding breaks and the canonical fingerprint is no
  longer trustworthy.

The binding is therefore a **content-bound transitive pinning**, not a
path-bound assertion.

## Canonical Tokenizer Identity Object

The producer's canonical object is the parsed `tokenizer_config.json` dict
itself — re-serialized deterministically. The exact parsed dict, sorted
by key, with compact separators and `ensure_ascii=False`, equals (one
line, 2 021 UTF-8 bytes):

```text
{"audio_token":"<|audio|>","backend":"tokenizers","boa_token":"<|audio|>","boi_token":"<|image|>","bos_token":"<bos>","eoa_token":"<audio|>","eoc_token":"<channel|>","eoi_token":"<image|>","eos_token":"<end_of_turn>","image_token":"<|image|>","processor_class":"Gemma4Processor","special_tokens":...}
```

(The full one-line form is 2 021 bytes; the producer's algorithm emits it
on a single line with no insignificant whitespace. The exact byte
sequence is verified below by independent reproduction.)

**Canonicalization rules applied:** sorted keys, compact `separators=(",", ":")`,
`ensure_ascii=False`, UTF-8 encoding.

**Canonicalization rules NOT applied (deliberately narrower than the
global profile):** NFC key/value normalization, keyset completeness check,
placeholder rejection. The producer does not apply these at the
sub-fingerprint layer; they are applied by the global
`whooshd.qualification-attestation.canonical-json.v1` canonicalizer when
the complete attestation is built. This narrower structure is the
producer's documented behavior in
`whooshd/qualification_attestation.py` lines 367–370.

## Exact Canonical Serialization

The full canonical object is a JSON object containing the Stage 2D
artifact's `tokenizer_config.json` content, sorted by key, with no
significant whitespace. Byte length: **2 021** UTF-8 bytes.

The canonical form is **not** included verbatim in this proof because (a)
the contents are user-visible textual content, and (b) the fingerprint
itself is the evidence-bound identity — not the literal bytes. The
fingerprint is reproducible from the bound source file by applying the
exact algorithm, as verified in §Independent Reproduction below.

## Fingerprint Algorithm

```
sha256(
  utf-8_encode(
    json.dumps(
      json.loads(read_text(tokenizer_config_path, encoding="utf-8")),
      ensure_ascii=False,
      sort_keys=True,
      separators=(",", ":"),
    )
  )
)
```

Serialised fingerprint form: `sha256:<64 lowercase hex characters>`.

## Expected `tokenizer.identity_fingerprint`

```text
sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264
```

## Independent Reproduction

Two independent paths were executed against the exact Stage 2D artifact
path. Both produced the same fingerprint byte-for-byte.

### A. Producer-side (calling the exact producer seam)

```text
$ ./venv311/bin/python
>>> from whooshd.qualification_attestation import collect_mlx_vlm_target_material
>>> m = collect_mlx_vlm_target_material(
...     invocation_model_id="gemma-4-12b-it-qat-4bit",
...     resolved_model_id="<stage2d artifact path>",
...     model_source="<stage2d artifact path>",
...     serving_runtime={"package": "mlx-vlm", "version": "0.6.2"},
...     structured_decoder={"package": "llguidance", "version": "1.7.6"},
...     structured_transport={"mode": "strict_json_schema",
...                           "protocol_version": "model-turn.strict-json-schema.v1"},
... )
>>> m["tokenizer"]
{'implementation': 'GemmaTokenizer',
 'identity_fingerprint': 'sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264'}
```

### B. Independent stdlib reconstruction (no producer import)

```text
$ ./venv/bin/python
>>> import json, hashlib
>>> from pathlib import Path
>>> p = Path("<stage2d artifact path>/tokenizer_config.json")
>>> parsed = json.loads(p.read_text(encoding="utf-8"))
>>> canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
>>> digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
>>> f"sha256:{digest}"
'sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264'
```

A second independent path (a hand-rolled JSON serializer that walks
`sorted(obj.items())` rather than using `json.dumps(sort_keys=True)`) was
also run and produced the same canonical bytes (2 021 bytes) and the
same fingerprint. All three paths agree.

**Both fingerprints match byte-for-byte:** no hash-of-hash shortcut was
used; the algorithm is the literal producer algorithm documented above.

## Result

- **Stage 2D raw-file SHAs reproduce byte-exactly** for all five files
  Stage 2D pinned.
- **The producer's tokenizer-identity algorithm** for the Stage 2D
  target is precisely characterized: parsed dict → canonical
  re-serialization (sorted keys, compact separators, `ensure_ascii=False`,
  UTF-8) → SHA-256 → `sha256:<hex>`.
- **The expected `tokenizer.identity_fingerprint`** for the Stage 2D
  qualified target is
  `sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264`.
- **Two independent reproductions match byte-for-byte** (producer-side
  via `collect_mlx_vlm_target_material`; independent stdlib via a
  hand-rolled canonical serializer).
- **No hash-of-hash shortcut** was used. The Stage 2D raw SHA is
  evidence binding the source file; the canonical fingerprint is
  computed by the producer's literal algorithm over that file.
- **No model generation, requalification, or A/B/C/D probe ran.** Only
  the read-only producer seam and the read-only filesystem were
  touched.
- **No Whoosh'd / model / tokenizer / config / dependency files changed.**
  Verified by `git status` of `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd`:
  only the pre-existing untracked `.venv311/` is present.
- **The original Stage 2D proof was not modified.** Verified by
  `git diff -- <stage 2D proof path>`.

## Qualification Scope

This supplemental proof does **not** broaden the Stage 2D qualification.
It only makes the tokenizer-identity dimension of the **already-qualified
target** machine-readable under the later Stage 2F contract.

- No other Gemma model is qualified.
- No other quantization is qualified.
- No other tokenizer artifact is qualified.
- No other template is qualified.
- No other MLX-VLM version is qualified.
- No other runtime adapter is qualified.
- Whoosh'd generally is not qualified.

## What This Proves

- The exact value the Stage 2F.1a producer would emit for
  `tokenizer.identity_fingerprint` against the exact Stage 2D
  qualified artifact, given the documented producer algorithm.
- The byte-exact reproducibility of that value from the Stage 2D-bound
  source file.
- That the source file itself has not drifted from Stage 2D evidence
  (raw SHA-256 reproduction, all five files).
- That the binding between Stage 2D and Stage 2F.1b is content-equivalent
  for this dimension, not file-equivalent — which is the contract's
  intended semantics.

## What This Does Not Prove

- Any other model's tokenizer identity.
- That the `tokenizer.identity_fingerprint` is part of a complete
  machine-readable qualification record for the Stage 2D target. Other
  required material fields are populated by Stage 2D evidence but the
  Stage 2F.1b Codexify comparator is not built here.
- That the live Whoosh'd service is currently serving the Stage 2D
  target. The live service was serving stub-model during Stage 2F.1a
  proof capture; whether it is currently serving the Stage 2D target is
  out of scope here and will be a Stage 2F.1b or later concern.
- Any qualification of tool behavior. No model generation occurred.

## Stage 2F.1b Handoff

With this supplemental proof, Stage 2F.1b has the missing
`tokenizer.identity_fingerprint` value:

```text
sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264
```

The resumed Stage 2F.1b task must read **both**:

1. `docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md`
2. `docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-tokenizer-identity-reconciliation-proof.md` (this document)

and may then construct the complete machine-readable qualification record
and continue with the Codexify attestation comparator.

The Stage 2F.1b stop condition on `tokenizer.identity_fingerprint` is now
resolved.

## Validation

The following documentation checks were run after this proof was written:

- `python3 scripts/validate_docs.py` — passed.
- `make docs PYTHON=python3` — passed.
- `git diff --check` — passed.
- `test -f docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-tokenizer-identity-reconciliation-proof.md` — true.

No automated runtime tests apply to this evidence-reconciliation proof.

## Repository State

Codexify:

```text
branch: codex/correct-whooshd-model-identity
HEAD:   36e32d090c4da1567f8a55369279145348c5d4a1 (digest-amendment)
Stage 2D ancestor (f20858a7b): present
Stage 2F ancestor (36332b5e): present
digest-amendment ancestor (36e32d090): HEAD
```

Whoosh'd:

```text
branch: codex/cwc-007-control-error-contract
HEAD:   d08e3261d8ed2217b9c258bb783138fc6a06df9f (Stage 2F.1a producer)
working-tree changes: none (only pre-existing untracked .venv311/)
producer ancestor: present
```

## Commit

This supplemental proof is committed on top of the digest-amendment
Codexify HEAD as a docs-only amendment. No runtime code, no test, no
configuration, and no Whoosh'd file was modified.

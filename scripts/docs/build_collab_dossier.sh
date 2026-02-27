#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/docs/build_collab_dossier.sh [--profile <name>] [--out-root <path>] [--date YYYY-MM-DD] [--no-archive] [--dry-run]

Options:
  --profile <name>     Dossier profile name (default: technical-teaser)
  --out-root <path>    Output root directory (default: artifacts/dossiers)
  --date <YYYY-MM-DD>  Date stamp for output naming (default: current date)
  --no-archive         Skip .tar.gz archive creation
  --dry-run            Resolve inputs/outputs and print plan without writing
  -h, --help           Show this help message
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROFILE="technical-teaser"
OUT_ROOT="artifacts/dossiers"
DATE_STAMP="$(date +%Y-%m-%d)"
MAKE_ARCHIVE=1
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || { echo "error: --profile requires a value" >&2; exit 1; }
      PROFILE="$2"
      shift 2
      ;;
    --out-root)
      [[ $# -ge 2 ]] || { echo "error: --out-root requires a value" >&2; exit 1; }
      OUT_ROOT="$2"
      shift 2
      ;;
    --date)
      [[ $# -ge 2 ]] || { echo "error: --date requires a value" >&2; exit 1; }
      DATE_STAMP="$2"
      shift 2
      ;;
    --no-archive)
      MAKE_ARCHIVE=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

INCLUDE_FILE="${REPO_ROOT}/scripts/docs/dossier_profiles/${PROFILE}.include"
EXCLUDE_FILE="${REPO_ROOT}/scripts/docs/dossier_profiles/${PROFILE}.exclude"

[[ -f "${INCLUDE_FILE}" ]] || { echo "error: include profile not found: ${INCLUDE_FILE}" >&2; exit 1; }
[[ -f "${EXCLUDE_FILE}" ]] || { echo "error: exclude profile not found: ${EXCLUDE_FILE}" >&2; exit 1; }

if [[ ! "${DATE_STAMP}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "error: --date must be in YYYY-MM-DD format" >&2
  exit 1
fi

if [[ "${OUT_ROOT}" = /* ]]; then
  OUT_ROOT_ABS="${OUT_ROOT}"
else
  OUT_ROOT_ABS="${REPO_ROOT}/${OUT_ROOT}"
fi

read_profile_lines() {
  local file="$1"
  local line
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "${line}" ]] && continue
    [[ "${line}" == \#* ]] && continue
    printf '%s\n' "${line}"
  done < "${file}"
}

INCLUDE_PATHS=()
while IFS= read -r line; do
  INCLUDE_PATHS+=("${line}")
done < <(read_profile_lines "${INCLUDE_FILE}")

EXCLUDE_PATTERNS=()
while IFS= read -r line; do
  EXCLUDE_PATTERNS+=("${line}")
done < <(read_profile_lines "${EXCLUDE_FILE}")

[[ ${#INCLUDE_PATHS[@]} -gt 0 ]] || { echo "error: include profile is empty" >&2; exit 1; }

matches_denylist() {
  local rel="$1"
  local pattern
  for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    [[ "${rel}" == ${pattern} ]] && return 0
  done
  return 1
}

for rel in "${INCLUDE_PATHS[@]}"; do
  src="${REPO_ROOT}/${rel}"
  [[ -f "${src}" ]] || { echo "error: included file is missing: ${rel}" >&2; exit 1; }
  if matches_denylist "${rel}"; then
    echo "error: include path matches denylist rule: ${rel}" >&2
    exit 1
  fi
done

BASE_NAME="codexify-${PROFILE}-${DATE_STAMP}"
OUTPUT_DIR="${OUT_ROOT_ABS}/${BASE_NAME}"
if [[ -e "${OUTPUT_DIR}" ]]; then
  OUTPUT_DIR="${OUT_ROOT_ABS}/${BASE_NAME}-$(date +%H%M%S)"
fi

ARCHIVE_PATH="${OUTPUT_DIR}.tar.gz"
if [[ ${MAKE_ARCHIVE} -eq 0 ]]; then
  ARCHIVE_PATH=""
fi

printf 'profile=%s\n' "${PROFILE}"
printf 'repo_root=%s\n' "${REPO_ROOT}"
printf 'out_root=%s\n' "${OUT_ROOT_ABS}"
printf 'output_dir=%s\n' "${OUTPUT_DIR}"
if [[ ${MAKE_ARCHIVE} -eq 1 ]]; then
  printf 'archive_path=%s\n' "${ARCHIVE_PATH}"
else
  printf 'archive_path=<disabled>\n'
fi
printf 'include_count=%s\n' "${#INCLUDE_PATHS[@]}"
printf 'exclude_count=%s\n' "${#EXCLUDE_PATTERNS[@]}"
printf '\nResolved include files:\n'
printf '  - %s\n' "${INCLUDE_PATHS[@]}"

if [[ ${DRY_RUN} -eq 1 ]]; then
  echo
  echo "dry-run: no files were written."
  exit 0
fi

mkdir -p "${OUTPUT_DIR}/manifest"

for rel in "${INCLUDE_PATHS[@]}"; do
  src="${REPO_ROOT}/${rel}"
  dst="${OUTPUT_DIR}/${rel}"
  mkdir -p "$(dirname "${dst}")"
  cp "${src}" "${dst}"
done

{
  printf '# Included source files copied into this dossier\n'
  printf '%s\n' "${INCLUDE_PATHS[@]}"
} > "${OUTPUT_DIR}/manifest/include-resolved.txt"

{
  printf '# Denylist rules used for this dossier build\n'
  printf '%s\n' "${EXCLUDE_PATTERNS[@]}"
} > "${OUTPUT_DIR}/manifest/exclude-rules.txt"

cat > "${OUTPUT_DIR}/DOSSIER_README.md" <<'EOF'
# Codexify Collaborator Dossier (Technical Teaser)

This dossier is a curated, non-destructive copy of selected project documentation for external collaborator interest.

## Suggested Reading Order

1. `README.md`
2. `docs/help/CODEXIFY_HELP_AND_FAQ.md`
3. `docs/architecture/README.md`
4. `docs/architecture/system-overview.md`
5. `docs/architecture/flows.md`
6. `docs/architecture/modules-and-ownership.md`
7. `docs/architecture/data-and-storage.md`
8. `docs/architecture/config-and-ops.md`
9. `docs/architecture/roadmap-signals.md`
10. `docs/architecture/tech-debt-and-risks.md`
11. `docs/Plugins/plugin-sdk.md`
12. `docs/Plugins/plugin_development.md`

## Notes

- This bundle is intentionally scoped to technical onboarding and architecture signal.
- Internal prompt libraries, task/campaign exhaust, and sensitive operational playbooks are excluded by profile denylist.
- Source files are copied as-is from the repository and are not rewritten.
EOF

cat > "${OUTPUT_DIR}/DOSSIER_SCOPE.md" <<EOF
# Dossier Scope

Profile: \`${PROFILE}\`

## Intent

Share a high-signal technical teaser of Codexify architecture and current operational behavior without exposing private prompt internals or exhaustive internal campaign/task records.

## Inclusion Strategy

- Include curated top-level docs plus architecture, setup, plugin, and selected ops/security boundary docs.
- Preserve source documents unchanged.

## Exclusion Strategy

- Exclude prompt internals, task/campaign trails, internal infra notes, full Codexify legacy docs subtree, and sensitive incident response playbooks.
- Denylist rules are recorded in \`manifest/exclude-rules.txt\`.
EOF

sha256_one() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file}" | awk '{print $1}'
  else
    shasum -a 256 "${file}" | awk '{print $1}'
  fi
}

: > "${OUTPUT_DIR}/manifest/SHA256SUMS.txt"
for rel in "${INCLUDE_PATHS[@]}"; do
  digest="$(sha256_one "${OUTPUT_DIR}/${rel}")"
  printf '%s  %s\n' "${digest}" "${rel}" >> "${OUTPUT_DIR}/manifest/SHA256SUMS.txt"
done

checksum_lines="$(wc -l < "${OUTPUT_DIR}/manifest/SHA256SUMS.txt" | tr -d ' ')"
if [[ "${checksum_lines}" -ne "${#INCLUDE_PATHS[@]}" ]]; then
  echo "error: checksum count mismatch (${checksum_lines} vs ${#INCLUDE_PATHS[@]})" >&2
  exit 1
fi

while IFS= read -r rel || [[ -n "${rel}" ]]; do
  [[ "${rel}" =~ ^#.*$ ]] && continue
  [[ -z "${rel}" ]] && continue
  if ! grep -Fq "  ${rel}" "${OUTPUT_DIR}/manifest/SHA256SUMS.txt"; then
    echo "error: missing checksum entry for ${rel}" >&2
    exit 1
  fi
done < "${OUTPUT_DIR}/manifest/include-resolved.txt"

while IFS= read -r rel || [[ -n "${rel}" ]]; do
  [[ "${rel}" =~ ^#.*$ ]] && continue
  [[ -z "${rel}" ]] && continue
  if matches_denylist "${rel}"; then
    echo "error: denylist violation in output: ${rel}" >&2
    exit 1
  fi
done < "${OUTPUT_DIR}/manifest/include-resolved.txt"

while IFS= read -r rel || [[ -n "${rel}" ]]; do
  [[ -z "${rel}" ]] && continue
  if matches_denylist "${rel}"; then
    echo "error: denylist violation found in output tree: ${rel}" >&2
    exit 1
  fi
done < <(cd "${OUTPUT_DIR}" && find . -type f | sed 's|^\./||')

METADATA_JSON="${OUTPUT_DIR}/manifest/METADATA.json"
GIT_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")"
GENERATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ARCHIVE_VALUE="null"
if [[ ${MAKE_ARCHIVE} -eq 1 ]]; then
  ARCHIVE_VALUE="\"${ARCHIVE_PATH}\""
fi

cat > "${METADATA_JSON}" <<EOF
{
  "profile": "${PROFILE}",
  "generated_at_utc": "${GENERATED_AT}",
  "date_stamp": "${DATE_STAMP}",
  "repo_root": "${REPO_ROOT}",
  "git_commit": "${GIT_COMMIT}",
  "output_dir": "${OUTPUT_DIR}",
  "archive_path": ${ARCHIVE_VALUE},
  "file_count": ${#INCLUDE_PATHS[@]}
}
EOF

if [[ ${MAKE_ARCHIVE} -eq 1 ]]; then
  mkdir -p "${OUT_ROOT_ABS}"
  tar -czf "${ARCHIVE_PATH}" -C "${OUT_ROOT_ABS}" "$(basename "${OUTPUT_DIR}")"
  tar -tzf "${ARCHIVE_PATH}" >/dev/null
fi

echo
echo "Dossier build complete."
echo "Folder:  ${OUTPUT_DIR}"
if [[ ${MAKE_ARCHIVE} -eq 1 ]]; then
  echo "Archive: ${ARCHIVE_PATH}"
else
  echo "Archive: <disabled>"
fi

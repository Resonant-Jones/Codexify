#!/usr/bin/env bash
set -u

print() {
  printf '%s\n' "$*"
}

printerr() {
  printf '%s\n' "$*" >&2
}

detect_frontend_root() {
  local dir="$1"

  if [ -d "$dir/frontend/src" ]; then
    print "frontend"
    return 0
  fi

  if [ -d "$dir/ui/src" ]; then
    print "ui"
    return 0
  fi

  if [ -d "$dir/web/src" ]; then
    print "web"
    return 0
  fi

  if [ -d "$dir/app/src" ]; then
    print "app"
    return 0
  fi

  local path
  local parent
  for path in "$dir"/*/src; do
    [ -d "$path" ] || continue
    parent="${path%/src}"
    if [ -f "$parent/package.json" ]; then
      print "${parent#"$dir"/}"
      return 0
    fi
  done

  return 1
}

is_repo_root() {
  local dir="$1"

  if [ ! -f "$dir/README.md" ]; then
    return 1
  fi

  if ! grep -q "Codexify" "$dir/README.md" 2>/dev/null; then
    return 1
  fi

  if [ ! -f "$dir/docker-compose.yml" ] && [ ! -f "$dir/compose.yml" ]; then
    return 1
  fi

  if [ ! -d "$dir/backend" ] && [ ! -d "$dir/guardian" ]; then
    return 1
  fi

  if ! detect_frontend_root "$dir" >/dev/null 2>&1; then
    return 1
  fi

  return 0
}

current_dir="$(pwd)"

if is_repo_root "$current_dir"; then
  frontend_root="$(detect_frontend_root "$current_dir")"

  print "Codexify repo root detected: $current_dir"
  print "Frontend root: ${frontend_root}/"
  print ""
  print "rg commands to locate utils.js:306 source:"
  print "  rg --fixed-strings \"[guardian] failed to load threads\" \"$frontend_root\""
  print "  rg --fixed-strings \"[documents] failed to load backend documents\" \"$frontend_root\""
  print "  rg --fixed-strings \"[codex] failed to load entries\" \"$frontend_root\""
  print "  rg \"Object\\.keys\\(\" \"$frontend_root\""
  print ""
  print "DevTools reminder: Sources -> Cmd+P -> utils.js -> line 306 (sourcemapped origin)."
  exit 0
fi

printerr "error: not in Codexify repo root."
printerr "current directory: $current_dir"
printerr ""
printerr "Likely repo locations (checked in order):"

suggested_dir=""
for candidate in "$HOME/Codexify" "$HOME/code/Codexify" "$HOME/Projects/Codexify"; do
  printerr "  $candidate"
  if [ -z "$suggested_dir" ] && is_repo_root "$candidate"; then
    suggested_dir="$candidate"
  fi
done

printerr ""
if [ -n "$suggested_dir" ]; then
  printerr "Likely repo directory: $suggested_dir"
  printerr "Try:"
  printerr "  cd \"$suggested_dir\""
  printerr "  bash scripts/dev/doctor.sh"
else
  printerr "No likely repo directory found."
  printerr "If your repo lives elsewhere, cd into it and re-run:"
  printerr "  bash scripts/dev/doctor.sh"
fi

exit 2

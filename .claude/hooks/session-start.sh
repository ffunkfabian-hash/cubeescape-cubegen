#!/bin/bash
# SessionStart hook for Claude Code cloud sessions (claude.ai/code) - does nothing on a local machine.
# Installs what the Python suite needs to run without skips: ImageMagick (6 on Ubuntu; cubegen handles it) and
# Blender 5.2 LTS as a Python module from PyPI (download.blender.org is blocked) behind a `blender` command.
# Idempotent: a resumed or cached container only re-checks. AGENTS.md › Abschluss in zwei Stufen.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

BPY_VERSION=5.2.2                     # Blender 5.2 LTS, as on the user's Mac; needs exactly Python 3.13
BPY_DIR=/opt/bpy-$BPY_VERSION
HOOKS=$(cd "$(dirname "$0")" && pwd)
ENV_FILE=${CLAUDE_ENV_FILE:-/dev/null}
log() { echo "[session-start] $*" >&2; }

apt_install() {  # packages whose dpkg status is missing
  local missing=()
  for p in "$@"; do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || missing+=("$p")
  done
  [ ${#missing[@]} -eq 0 ] && return 0
  log "apt: ${missing[*]}"
  apt-get update -qq </dev/null >&2 || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold "${missing[@]}" </dev/null >&2 \
    || log "apt-get meldet einen Fehler - fehlende Pakete stehen unten in der Übersicht"
}

# ImageMagick for textures, icons and contact sheets; the libraries Blender needs headless (EGL via Mesa)
apt_install imagemagick libegl1 libegl-mesa0 libgl1 libgl1-mesa-dri libxrender1 libxxf86vm1 libxfixes3 libxi6 \
  libxkbcommon0 libsm6

blender_note="Blender: fehlt (bpy $BPY_VERSION nicht installierbar) - Blender-Tests werden übersprungen"
if [ ! -x "$BPY_DIR/bin/blender" ]; then
  log "bpy $BPY_VERSION -> $BPY_DIR"
  if python3 -m venv "$BPY_DIR" >&2 && "$BPY_DIR/bin/pip" install -q "bpy==$BPY_VERSION" >&2; then
    { echo "#!$BPY_DIR/bin/python"; tail -n +2 "$HOOKS/blender_cli.py"; } > "$BPY_DIR/bin/blender"
    chmod +x "$BPY_DIR/bin/blender"
  else
    rm -rf "$BPY_DIR"
  fi
fi
if [ -x "$BPY_DIR/bin/blender" ]; then
  # only the blender command on PATH - the venv's python stays out of the way
  mkdir -p /opt/cloud-bin && ln -sf "$BPY_DIR/bin/blender" /opt/cloud-bin/blender
  echo "export PATH=\"/opt/cloud-bin:\$PATH\"" >> "$ENV_FILE"
  echo "export CUBEGEN_BLENDER=\"$BPY_DIR/bin/blender\"" >> "$ENV_FILE"
  blender_note="Blender: $("$BPY_DIR/bin/blender" --version 2>/dev/null | head -1) als \`blender\` (headless, CPU)"
fi

im=$(convert -version 2>/dev/null | head -1 | sed 's/^Version: //; s/ https.*//')
cat <<EOF
Cloud-Sitzung vorbereitet (.claude/hooks/session-start.sh):
- ImageMagick: ${im:-fehlt} (Version 6: \`convert\`/\`montage\`/\`compare\`, kein \`magick\`)
- $blender_note
- Tests: \`python3 tools/run_tests.py --tier quick\` (schnell), \`--tier full\` mit Blender; Unity-Check, Blender-Plugin und
  die macOS-App fehlen hier - Abschluss Stufe 1 (AGENTS.md › Abschluss in zwei Stufen).
EOF

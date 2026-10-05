#!/usr/bin/env bash
# Download / update cubegen (CLI + Blender add-on) for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior/HEAD/tools/install.sh | bash
#   ... | bash -s -- ~/Projekte/cubegen         (eigener Zielordner)
#   bash install.sh [ORDNER] [--dir ORDNER] [--branch BRANCH] [--no-link]
#
# Target folder: the given one; without one the current folder if it is empty (or already holds cubegen),
# else ~/cubegen. A folder that already holds other files gets a "cubegen" subfolder. Adds a `cubegen`
# command to ~/.local/bin, builds the Blender add-on (<folder>/dist/cubegen_blender_addon.zip) and checks
# Blender + ImageMagick. Run it again to update.
set -euo pipefail

REPO="ffunkfabian-hash/lowpoly_cubeescape_model_generatior"
URL="https://github.com/$REPO.git"
DIR="${CUBEGEN_DIR:-}"
BRANCH=""
LINK=1

usage() {
  echo "usage: install.sh [ORDNER] [--dir ORDNER] [--branch BRANCH] [--no-link]"
  echo "  ORDNER / --dir   Zielordner (Standard: der aktuelle Ordner, wenn er leer ist, sonst ~/cubegen)"
  echo "  --branch BRANCH  Branch statt dem Standard-Branch"
  echo "  --no-link        keinen 'cubegen'-Befehl in ~/.local/bin anlegen"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="${2:?--dir braucht einen Ordner}"; shift 2 ;;
    --dir=*) DIR="${1#--dir=}"; shift ;;
    --branch) BRANCH="${2:?--branch braucht einen Namen}"; shift 2 ;;
    --no-link) LINK=0; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unbekannte Option: $1" >&2; usage >&2; exit 2 ;;
    *) DIR="$1"; shift ;;
  esac
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m!   %s\033[0m\n' "$*"; }
die() { printf '\033[31mFehler: %s\033[0m\n' "$*" >&2; exit 1; }

# a folder is "free" when it does not exist or only holds Finder / Explorer leftovers
is_free() {
  [ -d "$1" ] || return 0
  local f
  for f in "$1"/* "$1"/.[!.]* "$1"/..?*; do
    [ -e "$f" ] || continue
    case "${f##*/}" in .DS_Store|.localized|Thumbs.db|desktop.ini) ;; *) return 1 ;; esac
  done
  return 0
}
is_cubegen() { [ -f "$1/cubegen/cli.py" ] && [ -f "$1/tools/build_addon.py" ]; }

# --- Python ---------------------------------------------------------------------------------------
PYTHON="$(command -v python3 || true)"
[ -n "$PYTHON" ] || die "python3 nicht gefunden. Installieren: https://www.python.org/downloads/ (macOS: brew install python)"
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
  || die "cubegen braucht Python >= 3.9, gefunden: $("$PYTHON" -V 2>&1)"

# --- target folder --------------------------------------------------------------------------------
case "$DIR" in "~") DIR="$HOME" ;; "~/"*) DIR="$HOME/${DIR#\~/}" ;; esac  # a quoted ~ is not expanded
if [ -z "$DIR" ]; then
  here="$(pwd)"  # an empty folder or an existing install: use the folder the script runs in
  if [ "$here" != "$HOME" ] && { is_free "$here" || is_cubegen "$here"; }; then DIR="$here"; else DIR="$HOME/cubegen"; fi
fi
if [ -d "$DIR" ] && ! is_cubegen "$DIR" && ! is_free "$DIR"; then
  DIR="$DIR/cubegen"  # never mix the project with other files
  if [ -d "$DIR" ] && ! is_cubegen "$DIR" && ! is_free "$DIR"; then
    die "$DIR enthält schon andere Dateien - bitte einen leeren Ordner angeben"
  fi
fi
mkdir -p "$DIR"
DIR="$(cd "$DIR" && pwd)"
say "Zielordner: $DIR"

# --- download or update ---------------------------------------------------------------------------
if command -v git >/dev/null 2>&1 && [ -z "${CUBEGEN_NO_GIT:-}" ] && { [ -d "$DIR/.git" ] || ! is_cubegen "$DIR"; }; then
  if [ ! -d "$DIR/.git" ]; then  # init + fetch instead of clone: works with a .DS_Store in the folder
    say "Lade cubegen herunter"
    git -C "$DIR" init --quiet
    git -C "$DIR" remote add origin "$URL"
    printf '.DS_Store\nThumbs.db\ndesktop.ini\n' >> "$DIR/.git/info/exclude"
  else
    say "Aktualisiere cubegen"
  fi
  B="$BRANCH"
  if [ -z "$B" ]; then
    B="$(git -C "$DIR" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
    if [ -z "$B" ] || ! git -C "$DIR" rev-parse --quiet --verify HEAD >/dev/null; then  # fresh: remote default
      B="$(git ls-remote --symref "$URL" HEAD | sed -n 's|^ref: refs/heads/\(.*\)[[:space:]]HEAD$|\1|p')"
    fi
  fi
  [ -n "$B" ] || die "konnte den Branch nicht ermitteln (Netzwerk?)"
  git -C "$DIR" fetch --quiet origin "+refs/heads/$B:refs/remotes/origin/$B" || die "Branch '$B' nicht gefunden"
  if [ "$(git -C "$DIR" symbolic-ref --quiet --short HEAD 2>/dev/null || true)" = "$B" ] \
     && git -C "$DIR" rev-parse --quiet --verify HEAD >/dev/null; then
    git -C "$DIR" merge --quiet --ff-only "origin/$B" \
      || die "lokale Änderungen in $DIR verhindern das Update (git status zeigt sie)"
  else
    git -C "$DIR" checkout --quiet -B "$B" "origin/$B" \
      || die "Dateien in $DIR stehen dem Download im Weg - bitte einen leeren Ordner angeben"
  fi
else  # no git (or an earlier archive install): download the archive and copy it over
  say "Lade cubegen herunter (Archiv, ohne git)"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  ref="${BRANCH:+refs/heads/$BRANCH}"
  curl -fsSL "https://github.com/$REPO/archive/${ref:-HEAD}.tar.gz" | tar -xz -C "$tmp"
  cp -R "$tmp"/*/. "$DIR"/
fi

# --- `cubegen` command ----------------------------------------------------------------------------
if [ "$LINK" = 1 ]; then
  BIN="$HOME/.local/bin"
  mkdir -p "$BIN"
  cat > "$BIN/cubegen" <<EOF
#!/bin/sh
# cubegen launcher (from install.sh) - runs the copy in $DIR
PYTHONPATH="$DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec "$PYTHON" -m cubegen "\$@"
EOF
  chmod +x "$BIN/cubegen"
  say "Befehl angelegt: $BIN/cubegen"
  case ":$PATH:" in
    *":$BIN:"*) ;;
    *) warn "$BIN ist nicht im PATH. Einmal ausführen (bzw. in ~/.zshrc / ~/.bashrc eintragen):"
       echo "    export PATH=\"$BIN:\$PATH\"" ;;
  esac
fi

# --- Blender add-on -------------------------------------------------------------------------------
say "Baue das Blender-Add-on"
ADDON="$("$PYTHON" "$DIR/tools/build_addon.py")"
echo "    $ADDON"

# --- check Blender + ImageMagick ------------------------------------------------------------------
say "Prüfe Blender und ImageMagick"
if ! (cd "$DIR" && "$PYTHON" -m cubegen doctor); then
  warn "Es fehlt noch etwas (siehe oben):"
  if [ "$(uname)" = "Darwin" ]; then
    echo "    ImageMagick: brew install imagemagick      Blender: https://www.blender.org/download/"
  else
    echo "    ImageMagick: sudo apt install imagemagick  Blender: https://www.blender.org/download/"
  fi
  echo "    Blender an einem anderen Ort: export BLENDER=/pfad/zu/blender"
fi

VERSION="$(cd "$DIR" && "$PYTHON" -m cubegen --version)"
cat <<EOF

Fertig: $VERSION in $DIR

  cubegen list                                     alle Modelltypen
  cubegen generate --seed 42 --types crate,drone --count 3
  cubegen generate --recipe $DIR/recipes/puzzle_room.json

Anleitung:      $DIR/docs/CLI.md
Blender-Add-on: $ADDON
                (Blender: Edit > Preferences > Add-ons > Install from Disk..., Zip nicht entpacken)
Aktualisieren:  dieses Script erneut ausführen$([ "$DIR" = "$HOME/cubegen" ] || printf ' (mit dem Ordner: bash -s -- %q)' "$DIR")
EOF

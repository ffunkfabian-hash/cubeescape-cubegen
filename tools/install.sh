#!/usr/bin/env bash
# Download / update cubegen (CLI + Blender add-on) for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior/HEAD/tools/install.sh | bash
#   bash install.sh [--dir DIR] [--branch BRANCH] [--no-link]
#
# Puts the project into ~/cubegen (or DIR), a `cubegen` command into ~/.local/bin, builds the Blender add-on
# (DIR/dist/cubegen_blender_addon.zip) and checks Blender + ImageMagick. Run it again to update.
set -euo pipefail

REPO="ffunkfabian-hash/lowpoly_cubeescape_model_generatior"
DIR="${CUBEGEN_DIR:-$HOME/cubegen}"
BRANCH=""
LINK=1

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --no-link) LINK=0; shift ;;
    -h|--help)
      echo "usage: install.sh [--dir DIR] [--branch BRANCH] [--no-link]"
      echo "  --dir DIR        Zielordner (Standard ~/cubegen)"
      echo "  --branch BRANCH  Branch statt dem Standard-Branch"
      echo "  --no-link        keinen 'cubegen'-Befehl in ~/.local/bin anlegen"
      exit 0 ;;
    *) echo "unbekannte Option: $1 (siehe --help)" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m!   %s\033[0m\n' "$*"; }

# --- Python ---------------------------------------------------------------------------------------
PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "python3 nicht gefunden. Installieren: https://www.python.org/downloads/ (macOS: brew install python)" >&2
  exit 1
fi
if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  echo "cubegen braucht Python >= 3.9, gefunden: $("$PYTHON" -V 2>&1)" >&2
  exit 1
fi

# --- download or update ---------------------------------------------------------------------------
if [ -d "$DIR/.git" ] && command -v git >/dev/null 2>&1 && [ -z "${CUBEGEN_NO_GIT:-}" ]; then
  say "Aktualisiere $DIR"
  if [ -n "$BRANCH" ]; then
    git -C "$DIR" fetch --quiet origin "$BRANCH"
    git -C "$DIR" checkout --quiet -B "$BRANCH" FETCH_HEAD
  else
    git -C "$DIR" pull --quiet --ff-only
  fi
elif command -v git >/dev/null 2>&1 && [ -z "${CUBEGEN_NO_GIT:-}" ]; then
  if [ -e "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    echo "$DIR existiert und ist kein cubegen-Klon - anderen Ordner mit --dir wählen" >&2
    exit 1
  fi
  say "Lade cubegen nach $DIR"
  git clone --quiet ${BRANCH:+--branch "$BRANCH"} "https://github.com/$REPO.git" "$DIR"
else  # no git: download the archive
  if [ -e "$DIR" ] && [ ! -f "$DIR/cubegen/cli.py" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    echo "$DIR existiert und ist kein cubegen-Ordner - anderen Ordner mit --dir wählen" >&2
    exit 1
  fi
  ref="${BRANCH:+refs/heads/$BRANCH}"
  say "Lade cubegen (Archiv, ohne git) nach $DIR"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "https://github.com/$REPO/archive/${ref:-HEAD}.tar.gz" | tar -xz -C "$tmp"
  rm -rf "$DIR"
  mkdir -p "$(dirname "$DIR")"
  mv "$tmp"/*/ "$DIR"
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
Aktualisieren:  dieses Script erneut ausführen
EOF

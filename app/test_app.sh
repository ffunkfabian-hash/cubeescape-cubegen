#!/bin/bash
# Headless tests of Cubegen.app (like the robot generator's viewer/test_viewer.sh): version, catalog through the bundled
# package, the command line the app builds (fixtures in app/tests, texture part checked against cubegen.gui),
# a 3D snapshot of a generated OBJ, the offscreen window and the ImageMagick icons of every catalog category.
#   app/test_app.sh [output dir]      default: ../output/app (builds the app when it is missing)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${1:-$ROOT/output/app}"
APP="$OUT/Cubegen.app"
[ -x "$APP/Contents/MacOS/Cubegen" ] || "$HERE/build.sh" "$OUT"
BIN="$APP/Contents/MacOS/Cubegen"
RES="$APP/Contents/Resources"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1"; fail=1; }

version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/cubegen/__init__.py")"
[ "$("$BIN" --version)" = "Cubegen.app $version, cubegen $version" ] && ok "version $version (app and bundled package)" \
  || bad "version"

catalog="$("$BIN" --catalog)" && [[ "$catalog" =~ ([0-9]+)\ types ]] && [ "${BASH_REMATCH[1]}" -gt 100 ] \
  && ok "catalog through the bundled package: $catalog" || bad "catalog ($catalog)"

for name in types family paint; do
  "$BIN" --print-args "$HERE/tests/settings_$name.json" > "$TMP/$name.json" &&
    python3 -c "import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); assert a==b, (a, b)" \
      "$TMP/$name.json" "$HERE/tests/settings_$name.expected.json" && ok "command line: $name" || bad "command line: $name"
done
if "$BIN" --print-args "$HERE/tests/settings_empty.json" > /dev/null 2>&1; then bad "no type, family or recipe rejected"
else ok "no type, family or recipe rejected"; fi

# the texture arguments are the desktop window's (cubegen.gui.texture_args)
cases=("none 512 ''" "tiled 1024 ''" "baked 256 ''" "palette 512 rust" "palette '' ''")
for c in "${cases[@]}"; do
  eval "set -- $c"
  printf '{"types":["crate"],"output":"/tmp/x","textures":"%s","textureSize":"%s","palette":"%s"}' "$1" "$2" "$3" \
    > "$TMP/tex.json"
  "$BIN" --print-args "$TMP/tex.json" > "$TMP/tex_args.json"
  PYTHONPATH="$ROOT" python3 - "$TMP/tex_args.json" "$1" "$2" "$3" <<'PY' && ok "textures $1/$2/$3 like the desktop window" \
    || bad "textures $1/$2/$3 like the desktop window"
import json, sys
from cubegen.gui import texture_args
args = json.load(open(sys.argv[1]))
want = texture_args(sys.argv[2], sys.argv[3], sys.argv[4])
got = []
for flag in ("--textures", "--texture-size", "--palette"):
    if flag in args:
        got += [flag, args[args.index(flag) + 1]]
assert got == want, (got, want)
PY
done

PYTHONPATH="$RES/python" python3 -m cubegen generate --seed 7 --pick machine:0,crate:0 --no-blender --out "$TMP/gen" \
  > /dev/null
"$BIN" --snapshot "$TMP/snap.png" --model "$TMP/gen/models/Machine_000.obj" --size 400x300 > /dev/null 2>&1 &&
  [ "$(magick identify -format '%wx%h' "$TMP/snap.png")" = "400x300" ] &&
  python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) > 0.05 else 1)" \
    "$(magick "$TMP/snap.png" \( +clone -fill "$(magick "$TMP/snap.png" -format '%[pixel:p{2,2}]' info:)" -colorize 100 \) \
       -compose difference -composite -colorspace gray -threshold 8% -format '%[fx:mean]' info:)" &&
  ok "3D snapshot of a generated OBJ (model covers > 5 % of the image)" || bad "3D snapshot of a generated OBJ"

"$BIN" --ui-snapshot "$TMP/ui.png" --results "$TMP/gen" > /dev/null 2>&1 && [ -s "$TMP/ui.png" ] \
  && ok "window drawn offscreen with catalog and results" || bad "window drawn offscreen"

PYTHONPATH="$RES/python" python3 - "$RES" <<'PY' && ok "ImageMagick icon for every catalog category" \
  || bad "ImageMagick icon for every catalog category"
import os, sys
from cubegen.cli import catalog_data
res = sys.argv[1]
categories = {t["category"] for t in catalog_data()["types"].values()}
names = [f"category_{c}" for c in categories] + ["view_iso", "view_front", "view_side", "view_top", "action_generate",
                                                 "action_validate", "action_stop", "action_folder", "cube"]
missing = [n for n in names if not os.path.isfile(os.path.join(res, n + ".png"))]
assert not missing, missing
PY

# a whole run through the app's process runner: with Blender (FBX + OBJ, preview, icon) when it is installed
printf '{"types":["crate","door"],"seed":"5","count":1,"output":"%s","unique":false}' "$TMP/run" > "$TMP/run.json"
if [ -x /Applications/Blender.app/Contents/MacOS/Blender ] || command -v blender >/dev/null; then
  "$BIN" --run "$TMP/run.json" > "$TMP/run.log" 2>&1 && grep -q "^models: 2, shown: Crate_000" "$TMP/run.log" &&
    grep -q "^progress: 2/2" "$TMP/run.log" && [ -f "$TMP/run/models/Crate_000.obj" ] && [ -f "$TMP/run/models/Crate_000.fbx" ] &&
    [ -f "$TMP/run/icons/Icon_Crate_000.png" ] && ok "run through the app (Blender: FBX, OBJ, preview, icon, progress)" ||
    { bad "run through the app"; tail -20 "$TMP/run.log"; }
  # Blender's MTL has a white ambient and linear colours: the 3D view must still show the materials' colours
  # (0.16.0: it was white/grey). The door has red and cyan status lights and coloured frame materials.
  "$BIN" --snapshot "$TMP/door.png" --model "$TMP/run/models/Door_000.obj" --no-floor --size 300x300 > /dev/null 2>&1 &&
    python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) > 0.35 else 1)" \
      "$(magick "$TMP/door.png" -colorspace HSL -channel G -separate +channel -format '%[fx:maxima]' info:)" &&
    ok "3D view shows material colours of a Blender OBJ" || bad "3D view shows material colours of a Blender OBJ"
else
  echo "SKIP run through the app with Blender (not installed)"
fi
printf '{"types":["crate"],"seed":"5","count":2,"output":"%s","noBlender":true}' "$TMP/run2" > "$TMP/run2.json"
"$BIN" --run "$TMP/run2.json" > "$TMP/run2.log" 2>&1 && grep -q "^models: 2" "$TMP/run2.log" \
  && ok "run through the app without Blender (OBJ)" || { bad "run through the app without Blender"; tail -20 "$TMP/run2.log"; }
"$BIN" --run "$TMP/run2.json" --validate > "$TMP/val.log" 2>&1 && grep -q "Qualitätsranking" "$TMP/val.log" \
  && ok "validation through the app (ranking)" || { bad "validation through the app"; tail -20 "$TMP/val.log"; }

exit $fail

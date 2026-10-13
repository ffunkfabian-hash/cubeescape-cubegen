#!/bin/bash
# The app's UI icons, drawn with ImageMagick (like the robot generator plans its UI icons): white line art on
# transparent (SwiftUI tints them as template images), drawn at 512 px and scaled to 64 / 128 px (@2x).
#   app/make_icons.sh <output dir>
# Reproducible: no time stamps in the PNGs. Names: view_*, action_*, category_* (the catalog's categories), cube.
set -euo pipefail
OUT="${1:?output dir}"
mkdir -p "$OUT"
W="#ffffff"
S=34   # stroke width at 512 px
M=(magick -define png:exclude-chunks=date,time)

icon() {  # name, draw arguments... (512 x 512 canvas, white strokes, no fill, round line ends)
  local name=$1; shift
  local args=()
  while [ $# -gt 0 ]; do
    if [ "$1" = "-draw" ]; then args+=(-draw "stroke-linecap round stroke-linejoin round $2"); shift 2
    else args+=("$1"); shift; fi
  done
  "${M[@]}" -size 512x512 xc:none -fill none -stroke "$W" -strokewidth $S "${args[@]}" "$OUT/.$name.png"
  "${M[@]}" "$OUT/.$name.png" -resize 64x64 "$OUT/$name.png"
  "${M[@]}" "$OUT/.$name.png" -resize 128x128 "$OUT/$name@2x.png"
  rm "$OUT/.$name.png"
}

# views
icon view_iso -draw "polygon 256,72 432,174 256,276 80,174" -draw "polyline 80,174 80,350 256,452 432,350 432,174" \
  -draw "line 256,276 256,452"
icon view_front -draw "rectangle 112,112 400,400" -draw "line 112,300 400,300"
icon view_side -draw "rectangle 176,112 336,400" -draw "polyline 336,112 400,160 400,448 336,400" \
  -draw "polyline 176,400 240,448 400,448"
icon view_top -draw "rectangle 112,112 400,400" -draw "rectangle 196,196 316,316"
# actions
icon action_turntable -draw "ellipse 256,300 180,80 0,360" -draw "line 256,300 256,96" \
  -fill "$W" -draw "polygon 436,300 396,250 476,250"
icon action_floor -draw "polyline 64,400 448,400" -draw "polyline 112,300 400,300" -draw "polyline 160,210 352,210" \
  -draw "line 160,210 64,400" -draw "line 352,210 448,400" -draw "line 256,210 256,400"
icon action_log -draw "line 96,144 416,144" -draw "line 96,256 416,256" -draw "line 96,368 320,368"
icon action_screenshot -draw "roundrectangle 64,160 448,416 40,40" -draw "circle 256,288 256,212" \
  -draw "polyline 176,160 208,104 304,104 336,160"
icon action_folder -draw "polyline 64,128 208,128 248,176 448,176 448,400 64,400 64,128"
icon action_generate -fill "$W" -draw "polygon 168,104 416,256 168,408"
icon action_validate -draw "polyline 96,272 208,384 416,136"
icon action_stop -fill "$W" -draw "roundrectangle 136,136 376,376 24,24"
# own paint scheme: a brush with a drop of paint
icon action_paint -draw "line 392,96 232,256" -draw "polygon 232,256 280,304 200,400 136,400 136,336" \
  -fill "$W" -draw "circle 376,392 376,352"
icon action_random -draw "roundrectangle 96,96 416,416 56,56" -fill "$W" -draw "circle 184,184 184,160" \
  -draw "circle 256,256 256,232" -draw "circle 328,328 328,304"
# model categories of the catalog
icon category_environment -draw "rectangle 64,96 448,416" -draw "line 64,202 448,202" -draw "line 64,310 448,310" \
  -draw "line 256,96 256,202" -draw "line 160,202 160,310" -draw "line 352,202 352,310" -draw "line 256,310 256,416"
icon category_industrial -draw "circle 256,256 256,168" -draw "circle 256,256 256,224" \
  -draw "line 256,64 256,120" -draw "line 256,392 256,448" -draw "line 64,256 120,256" -draw "line 392,256 448,256" \
  -draw "line 120,120 160,160" -draw "line 352,352 392,392" -draw "line 120,392 160,352" -draw "line 352,160 392,120"
icon category_nature -draw "bezier 256,440 120,300 160,120 256,72" -draw "bezier 256,72 352,120 392,300 256,440" \
  -draw "line 256,440 256,160"
icon category_props -draw "rectangle 96,128 416,416" -draw "line 96,128 416,416" -draw "line 416,128 96,416" \
  -draw "line 96,224 416,224"
icon category_puzzle -draw "polyline 96,176 200,176 200,96 312,96 312,176 416,176 416,416 96,416 96,176" \
  -draw "circle 256,300 256,252"
icon category_robots -draw "roundrectangle 112,168 400,416 40,40" -draw "line 256,168 256,96" \
  -draw "circle 256,84 256,64" -fill "$W" -draw "circle 192,280 192,252" -draw "circle 320,280 320,252"
icon category_ruins -draw "polyline 144,448 144,176 200,120 240,200 300,96 368,176 368,448" \
  -draw "line 96,448 416,448"
icon category_tech -draw "rectangle 152,152 360,360" -draw "rectangle 216,216 296,296" \
  -draw "line 200,152 200,80" -draw "line 312,152 312,80" -draw "line 200,360 200,432" -draw "line 312,360 312,432" \
  -draw "line 152,200 80,200" -draw "line 152,312 80,312" -draw "line 360,200 432,200" -draw "line 360,312 432,312"

# placeholder for a model without preview: the app icon's cube in colour (not a template)
"${M[@]}" -size 512x512 xc:none \
  -fill "#f2a64a" -draw "polygon 256,72 432,174 256,276 80,174" \
  -fill "#d0782a" -draw "polygon 80,174 256,276 256,452 80,350" \
  -fill "#9c5418" -draw "polygon 432,174 256,276 256,452 432,350" "$OUT/.cube.png"
"${M[@]}" "$OUT/.cube.png" -resize 128x128 "$OUT/cube.png"
rm "$OUT/.cube.png"
echo "> icons: $(ls "$OUT" | wc -l | tr -d ' ') files in $OUT"

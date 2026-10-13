# Cubegen 0.19.1 – Kaleidoscope

Korrektur vom 13. Oktober 2026, Release-Zweig `release/0.19.1`; vorherige Version [0.19.0](VERSION_0.19.0.md).

## Fund

Der neue GitHub-Job `blender` (0.19.0) lief durch – Blender 4.5 installiert, 104 Testmodule-Tests –, war aber rot,
ebenso die Gruppe `rest` in allen drei Python-Versionen. Ein Blick in die Historie: GitHub Actions ist **seit 0.17.0
rot** (lokal war alles grün, weil hier ImageMagick 7 läuft).

## Ursache

Der Ubuntu-Runner hat **ImageMagick 6**:

1. Es schreibt Zeitstempel in die PNGs (`tIME`, Text `date:create`/`date:modify`), obwohl Cubegen
   `-define png:exclude-chunks=date,time` setzt – zwei Läufe ergaben andere Bytes (4 Tests: Texturen, gebackener
   Atlas, Cache, parallele Kacheln).
2. Es gibt kein Programm `magick`; ein Test rief `magick compare` direkt auf.

## Korrektur

- `imagemagick.strip_png_dates`: nach jedem Schreiben (`ImageMagick.run` und der Back-Pfad `bake._magick`) entfernt
  ein kleiner Filter die Zeitstempel-Chunks aus der Ausgabe-PNG (auch mit Präfix `PNG8:`/`PNG24:`/`PNG32:`). Unter
  ImageMagick 7 ist er wirkungslos: eine PNG ohne Define plus Filter ist bytegleich mit einer PNG mit Define (Test).
  Die Ausgabe auf diesem Mac bleibt also bytegleich; Unity importiert nichts neu.
- Der Test vergleicht Bilder mit dem gefundenen ImageMagick (`magick compare` bzw. `compare`).

## Prüfung

- `tests/test_release_0191.py` (3 Tests): Filter (nur Zeit- und Datums-Chunks, sonst unverändert, Nicht-PNG),
  Ausgabe-Argumente mit Präfix, IM7 mit und ohne Define + Filter bytegleich.
- `tools/run_tests.py` (volle Stufe, mit Blender und ImageMagick 7): **322 Tests grün** (190 s); GitHub Actions nach dem Push geprüft.

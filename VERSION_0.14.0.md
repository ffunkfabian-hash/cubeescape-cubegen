# Cubegen 0.14.0 – Werkstattbuch

Release vom 12. Oktober 2026 (reiner Doku-Stand, Ausgabe unverändert). Release-Zweig `release/0.14.0`; vorherige
Version [0.13.0](VERSION_0.13.0.md).

## Inhalt

- **AGENTS.md › „Blender-Batch schnell halten“:** Erfahrungen aus dem Roboter-Generator (Repo
  `ffunkfabian-hash/cubeescape-robogen`, 1.8 „Turbo“ und 1.9 „Afterburner“), jeweils mit Messwert und der Stelle, an
  der sie Cubegen betreffen.
- **docs/ROADMAP.md:** offener Punkt „Schnellere Blender-Läufe“ – Backen über eine zusammengefügte Kopie
  (`cubegen/bake.py`), `--jobs` mit Thread-Grenze (`cubegen/pipeline.py`, `cubegen/blender.py`), ImageMagick mit
  `MAGICK_THREAD_LIMIT=1` (`cubegen/imagemagick.py`, `bake.py`).

Generator, Geometrie, Kollision, Materialien, Sidecar und Add-on-Logik sind unverändert; Golden-Daten unverändert.

## Prüfung

- `python3 -m unittest discover -s tests`: **262 Tests grün**, keiner übersprungen (Blender 5.2.2 und ImageMagick 7
  vorhanden), 263 s, am 12. Oktober 2026. Keine Exporte nötig, weil sich die Ausgabe nicht ändert.
- Links und Verweise auf Dateien und Funktionen (`bake.py`, `pipeline.py`, `blender.py`, `imagemagick.py`) von Hand geprüft.

## Grenzen

- Die Erfahrungen sind im Roboter-Generator gemessen, nicht in Cubegen. Vor einer Umsetzung in Cubegen messen
  (`cProfile`, `sample`), Ausgaben gegen die Golden-Daten vergleichen.

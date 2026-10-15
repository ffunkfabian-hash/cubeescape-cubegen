# Cubegen 0.30.0 – Lattice

*ungeprüft: Blender-/Unity-Abnahme offen* – Python-Suite und echte Blender-Läufe der Änderungen liefen lokal; der
Unity-Import (`tools/unity_check.py --require`) und der Import von Voxelmodellen in der Cube-Escape-Testkopie stehen aus.

Unveröffentlicht; Arbeitszweig `claude/practical-gould-a305b7` (Release-Zweig `release/0.30.0` erst beim Release);
vorherige Version [0.29.0](VERSION_0.29.0.md).

## Anlass

`docs/TECHNIK.md` (0.29.0) listete offene Techniken aus dem Roboter-Generator. Diese Version setzt um, was ohne
Vertragsänderung und ohne Cube Escape geht, misst den Rest und schreibt das Ergebnis in die Tabelle.

## Änderungen

- **Atlas (TECHNIK 6):** `bake.occupancy` misst die Belegung, `_atlas_uvs` packt nach Smart UV Project konkav nach
  (Rand 0,008). Belegung an 6 Typen 0,50–0,72 → 0,67–0,79. Manifest: `models[].atlas_occupancy`. Texturen gebackener
  Läufe ändern sich (neue Atlas-Anordnung); Geometrie, Sidecars, IDs nicht.
- **QA-Cache (TECHNIK 8a):** `quality.check_cached` (Schlüssel: `Asset.digest` + Hash der Prüfmodule). Von
  `quality.report` und `cubegen check`/`validate_batch` genutzt. 187 Typen × 10 Varianten: 7,1 s kalt, 4,6 s warm.
- **Lackzonen (TECHNIK 3):** `cubegen/zones.py`, Manifest `models[].zones`. Keine Zonenkarte (braucht Vertragsversion 4
  und Cube Escape). Messung: 135 von 154 Objektnamen sind `Body`; 78 von 187 Typen hätten zwei oder mehr bemalbare Zonen.
- **Teilgraphen im Material (TECHNIK 4):** gemessen – 2–6 Knoten je Material, 0,012 ms je Knoten: kein Gewinn, nicht umgesetzt.
- **Effektmaterialien als Daten (TECHNIK 7):** `cubegen/effects.py`, Manifest `models[].effects` (Art, Verwendung, Werte
  aus `materials.MATERIALS`); reine Beschreibung, das Spiel liest sie noch nicht.
- **Formvarianten (TECHNIK 4/15/17):** `--shape smooth|voxel` (Style `shape`, `cubegen/shapes.py`): feste, konvexe,
  dekorative Teile werden als verschmolzene Würfel neu gebaut; gleiche Teile, Collider, Behaviours, Sidecar. Facette
  (= `--detail low`) und Loch nicht umgesetzt. `catalog`/App zeigen die Option („Form“).
- **Viewer (TECHNIK 8):** geprüft, nicht betroffen (lädt nur Albedo ohne Alpha, keine Shader); Regel in DEVELOPER 6.
- **Gestrichen:** `app/notarize.sh` und alle Hinweise auf Developer ID/Notarisierung.

## Prüfung

- `python3 -m unittest tests.test_release_0300` (neu, 11 Tests): QA-Cache-Treffer = Rechnung, Zonen, Effektdaten,
  Voxelform über alle 187 Typen (Bounding-Box innen, gleiche Collider/Behaviours/Objekte, nicht mehr ungedeckte Teile,
  kein neues Z-Fighting), Verschmelzen, CLI-Katalog.
- Echte Läufe: `--textures baked` mit und ohne `--shape voxel` (5 Typen, Seed 7), Vorschau gesichtet; `app/test_app.sh` grün.
- `python3 tools/run_tests.py --tier full` (mit Blender und ImageMagick, unter der gemeinsamen Sperre): 455 Tests, alle
  Gruppen OK, 1 übersprungen (echter Unity-Lauf, `CUBEGEN_UNITY_CHECK`). Ein Codex-Gegenlauf kam nicht zustande.

## Offen

- Stufe 2: `unity_check.py --require`, Unity-Import und Physik von `--shape voxel`-Modellen; Sichtprüfung des neuen Atlas
  im Blender-Plugin; eigener Prüfsatz für `--shape voxel`.
- Zonenkarte und Effektblock im Sidecar (Vertrag, Cube Escape); Facette/Loch; Golden-Gruppe für die Voxelform.
- `--shape` fehlt im Blender-Add-on und in `cubegen/gui.py` (nur CLI, Rezepte, App über den Katalog).

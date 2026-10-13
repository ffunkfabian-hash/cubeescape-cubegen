# Cubegen 0.21.0 – Monolith

Release vom 13. Oktober 2026, Release-Zweig `release/0.21.0`; vorherige Version [0.20.0](VERSION_0.20.0.md).
Die Erkenntnisse aus Cube Escape 0.49 „Megastructure“, die die dortige Sitzung an Cubegen weitergegeben hat, sind
umgesetzt. Ohne die neue Option ist die Ausgabe der Modelle unverändert (Golden-Daten).

## 1 · Ein Renderer, wo es geht

Cube Escape baut in großen Leveln Modelle mit höchstens einem MeshRenderer und Kollision auf dem Modell als flache
Kopien (`FlatModels`); mehrteilige Cubegen-Modelle fielen heraus. Gemessen (Seed 1): 63 statische Typen exportieren
mehr als ein Mesh-Objekt, meist „Body + Glow“.

- `--single-renderer` (CLI, Rezeptfeld `single_renderer`, App, Desktop-Fenster): `Asset.merge_static` fügt die
  Mesh-Objekte eines statischen Modells zu einem zusammen; die Materialien bleiben Untermeshes (gleiche Optik, gleiche
  Draw Calls), Kollision und Kinder zeigen auf das bleibende Objekt. Nur wenn alle Teile reine Optik tragen
  (`asset.DECORATIVE_PARTS`: Body, Glow, Lights, Glass, Screen, Wall, Rock …) – Teile mit Bedeutung für
  Authoring-Profile oder Gameplay (Panel, Tile_<n>, Fluid, Basin, Rotor, Cover, Content, Occupant, Planet,
  StatusLight) lassen das Modell unverändert: Schleuse, Bruchplattform, Becken, Bodengitter, Turbine, Kryokapsel,
  Notfallkasten, Diagnosebuchse, Planetenfenster, Geometrietest.
- Geprüft: 105 Varianten zusammengefasst – Hülle, Dreiecke, Materialien gleich, Vertrag gültig, keine
  Qualitätsfehler; echtes FBX mit einem Mesh-Objekt (plus leere Anker); Unity-Check-Prüfsatz `single` (8 Typen, mit
  LODs) ohne Fehler. Manifest: `renderers` je Modell. Mit `--lods` sind es zwei Renderer.
- Option, nicht Standard: bestehende Exporte behalten ihre Hierarchie. Unity-ToDo 32: Standardsets mit der Option neu
  exportieren; danach kann sie Standard werden (ROADMAP).

## 2 · Grenzen in Bytes und Zeichen

- Cubegen misst die Sidecar-Grenze (4 MB) an der Datei, also in Bytes – richtig. Der Abgleich fand die Verwechslung
  in Cube Escape: `CubegenContract.cs` und `CubegenJson.cs` vergleichen die Zeichenzahl eines Strings mit der
  Byte-Grenze (Unity-ToDo 33).
- Neu: das Budget der Werkbank (`contract.RUNTIME_BUDGET`, aus Cube Escapes `CubegenImportBudget` und
  `CubegenGlb.Limits`): 32 MB je GLB, 60 000 Dreiecke, 512 Teile, 32 Materialien, 16 Texturen bis 2048 px, 64 MB
  Texturspeicher (RGBA32 mit Mips, wie Cube Escape zählt). `check_runtime_budget` liest das GLB selbst (Bytes,
  Knoten, Materialien, Dreiecke, eingebettete Bildgrößen aus dem PNG-Kopf); Warnung beim Erzeugen, `runtime_budget`
  im Manifest, Ausgabe in `cubegen check --export`.
- **Fund:** `--textures tiled --texture-size 2048` sprengt den Texturspeicher schon bei einer Kiste (128 MB), eine
  Konsole 192 MB, eine Werkbank 256 MB. Ursache in Cube Escape: geteilte Kacheltexturen zählen je Modell voll und
  unkomprimiert (Unity-ToDo 34). Für die Werkbank genügen 512–1024 px.

## 3 · Index statt jede Datei lesen

Ein Lauf aus dem Cache las jede Vorschau (für den Icon-Schlüssel) und jede bisher geschriebene Datei (zur Bestätigung)
vollständig. Jetzt merkt sich der Cache Größe und Änderungszeit je Datei (`stats` je Eintrag, `index` für gelesene
Eingaben) und hasht nur, wenn sie sich geändert haben. Ältere Cache-Dateien werden weiter gelesen (dann wird einmal
gehasht).

## 4 · Erst Schritte benennen, dann optimieren

- `timings.steps` im Manifest: `plan_models`, `build` (Python-Bauten), `contract` (ohne die Bauten, die er auslöst) –
  neben den Stufen und den Blender-Zeiten.
- `tools/perf_band.py`: feste Arbeitslasten (`catalog` ohne Blender, `cached` mit Blender aus dem Cache, `kit`)
  mehrfach, jeder Lauf nach Last je Kern eingestuft (ruhig ≤ 0,5, leicht ≤ 1,0 → Toleranz ×2, stark → Laufzeit nicht
  gewertet), Bänder (min/Median/max), Vergleich mit gespeichertem Band (15 %, mindestens 0,3 s). Dazu die CPU-Zeit
  des Befehls samt Blender-Prozessen – sie hängt kaum von fremder Last ab und zählt immer.
- Anlass: Während dieser Arbeit lag die Last bei 15–22 auf 10 Kernen (andere Sitzungen); derselbe Lauf dauerte 5 bis
  14 s. Das Pausen-Werkzeug aus der Regel „Ganze Leistung des Geräts“ liegt im Cube-Escape-Haupt-Checkout noch nicht
  vor – gemessen wurde deshalb mit Bändern und CPU-Zeit.

## 5 · Verzeichnisse statt Suchen

Profil (Katalog, 561 Modelle, ohne Blender): `build_spec` lief 1 683-mal – jedes Modell wurde für Vertrag, Export und
Manifest dreimal gebaut.

- Die Pipeline nutzt das vorhandene Verzeichnis gebauter Modelle (`asset_of`, neu `lod_of`) auch für Vertrag, OBJ-Export
  und Manifest: jedes Modell einmal je Lauf (Test).
- Set-Mitglieder in einem Durchgang gruppiert statt einer Suche je Set; `validate_contract` mit Namensverzeichnis statt
  `asset.get` je Verweis; die Flackerprüfung ohne `j in members` (Listensuche je Flächenpaar).
- Ergebnis (CPU-Zeit, je drei Läufe, Last „stark“): Katalog ohne Blender **4,65 → 2,57 s**, Katalog aus dem Cache
  **5,91 → 5,02 s**. Was bleibt: Ein Lauf aus dem Cache baut alle Modelle noch einmal (2,2 s) und schreibt das Manifest
  neu (2,8 s) – ROADMAP „Unveränderte Modelle nicht neu bauen“.

## Prüfung

- `tests/test_release_0210.py` (8 Tests): zusammengefasste Modelle (Optik, Vertrag), Teile mit Bedeutung bleiben,
  Option bis ins Manifest und Standard unverändert, GLB-Budget an einem erzeugten GLB, Index ohne erneutes Lesen und
  Erkennen geänderter Dateien, ein Bau je Modell und benannte Schritte, Lastklassen/Bänder/Urteile, Unity-Prüfsatz.
- `tools/run_tests.py` (volle Stufe): **337 Tests grün** (407 s unter Last); Golden-Daten unverändert.
- `app/test_app.sh`: **27 von 27**.
- `tools/unity_check.py --require`: **9 Prüfsätze, 262 Modelle, 0 Fehler** (Cube Escape `919ff679`).

## Grenzen

- `--single-renderer` ist eine Option; flache Kopien entstehen erst, wenn Cube Escape mit ihr neu exportiert.
- Die Unity-Seite der Funde (Byte-Grenze im Leser, ehrliches Texturbudget) ist Cube-Escape-Arbeit (ToDo 33, 34).

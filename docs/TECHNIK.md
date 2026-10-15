# Techniken aus dem Roboter-Generator – Übertrag auf Cubegen

Stand: Roboter-Generator 1.20.6, Cubegen 0.29.0 „Crossflow“. Quelle ist `docs/TECHNIK.md` im Repo
`cubeescape-robogen` (Abschnittsnummern „RG §n“ unten beziehen sich darauf). Diese Datei sagt, welche dieser Techniken
Cubegen schon hat, welche nur teilweise und welche fehlen, und wie man sie für Cubegen umsetzt. Sie wiederholt die
Robogen-Abschnitte nicht; Hintergründe und Messwerte stehen dort. Zahlen in dieser Datei sind Messwerte des
Roboter-Generators (Apple M5, Blender 5.2), keine von Cubegen, außer ausdrücklich so genannt.

Der Roboter-Generator baut genau eine Figur mit Rig und Clips, Cubegen viele statische und bewegliche Modelle.
Nicht übertragbar sind darum die Techniken rund um Skelett, Clips und Federknochen (RG §10 Federknochen, §11 Servo,
§15 Proportionen, §18) – siehe „Nicht übertragbar“ am Ende.

**Pflege:** Jede Cubegen-Version, die eine Technik umsetzt oder ändert, passt Tabelle und Checkliste im selben Zuge an
(Spalte „Stand“ mit Fundstelle im Code). Eine neue Robogen-Technik kommt als neue Tabellenzeile samt Abschnitt hinzu.
„Schon da“ heißt: mit Datei belegt und von einem Test oder Lauf abgedeckt; ist nur ein Teil belegt, steht „teilweise“
mit dem, was fehlt. Entwicklerhintergrund zu den vorhandenen Teilen: [`DEVELOPER.md`](DEVELOPER.md), offene Wünsche:
[`ROADMAP.md`](ROADMAP.md).

## Auf einen Blick

| Technik | Robogen | Stand in Cubegen | Nutzen |
|---|---|---|---|
| Looks als versionierte Daten | §1 | teilweise: `paint.PAINTS` (Python), `--paint-file` mit `paint.load_scheme`/`check_scheme`, Vertrag versioniert (`cubegen/contract.json`, `contract_for`); kein Look-Format mit Migration und Fixture | Themen ohne Code, sichere Formatänderungen |
| Einmal backen, linear zusammensetzen | §2 | schon da: `stylebake.py` (`bake_masks`, `compose_paint`), `paint.compose`, Gewichtskarten (DEVELOPER 2); Gegenprobe gegen direktes Backen: `tools/paint_reference.py` | jede Farbgebung in Sekundenbruchteilen |
| Maskenkanäle statt Textursatz je Variante | §3 | teilweise: gepackte neutrale Karten `MTN_` (`cubegen/neutral.py`), Shader in Cube Escape rechnet nach (ROADMAP ToDo 27); keine Zonen-/Abzeichen-/Leuchtlinien-Kanäle | Varianten zur Laufzeit statt Dateien |
| Lackzonen aus Teilnamen | §3 | offen: Teile sind benannt (`asset.py`), aber ohne Flächenattribut/Zonenkarte | Zweitfarbe exakt an Teilgrenzen |
| Decal-Anker je Modellfamilie | §3 | teilweise: Anker für Klang und Effekte (`cubegen/models/anchors.py`); keine Decals | Abzeichen/Kennungen auf jedem Typ |
| Normierte Verwitterungsfelder | §3 | teilweise: `wear`, `grime`, `dust`, `moss` als Regler je Thema (`paint.SCHEME_KEYS`); keine Rangfolge-Normierung | gleich empfindliche Regler |
| Gemeinsame Teilgraphen im Material | §4 | offen (nicht gemessen) | schnellerer Materialaufbau |
| Präsentationskarten | §5 | teilweise: Kontaktbögen und Set-Reihen (`pipeline.py` `SHEET_ROWS`, `imagemagick.py`), Konzeptvergleich `tools/style_test.py --concept`; keine Dreiviertel-/Bloom-Karte | Kataloge im Stil der Konzepte |
| Konzeptbögen auslesen | §6 | schon da: `tools/style_test.py --concept` | Paletten aus Referenzbildern |
| Icons mit Lesbarkeitsprüfung | §7 | teilweise: Icons je Modell (`imagemagick.make_icon`); Prüfung nur als Hinweis über Apple Vision (`tools/vision_report.py`) | Werkbank-Palette ohne Fehlgriffe |
| Viewer: Daten-Texturen roh, Uniform-Grenzen | §8 | offen (nicht geprüft): `app/Sources`, `ModelScene` liest MTL selbst | keine stillen Vorschaufehler |
| Atlas nachpacken, Belegung messen | §16 | offen: nur Smart UV Project (`cubegen/bake.py` `_atlas_uvs`) | kleinere Atlanten, schärfere Texel |
| Unity-Testprojekt, Prüfung in einem Start | §9, §11 | teilweise: `tools/unity_check.py` läuft in der Cube-Escape-Testkopie, Prüfsätze, eigene Prozessgruppe je Schritt; kein eigenes Testprojekt | Import, Kollision, Screenshots automatisch |
| Effektmaterialien als Daten | §11 | offen: Glas/Hologramm/Leuchten sind Materialnamen (`materials.py`), Effekt liegt in Cube Escape | gleiche Formeln in Vorschau und Spiel |
| LOD automatisch | §11 | teilweise: `--lods`, LOD1 als Neubau mit `style.detail = low` (`blender_worker.py` `build_asset`), geprüft je Stufe; kein Decimate, keine Dreiecksbudgets je Stufe | Detailstufen je Modell |
| Kollisionsformen aus Geometrie | §11 | teilweise: Rezepte und Prüfung (`collision.py`, `quality.uncovered_geometry`, `quality.needs_collider`); keine gemessenen Hüllen | passende Kollision (AGENTS.md) |
| QA-Ergebnis-Cache | §12 | offen: `quality.report` rechnet jedes Mal | Prüflauf in Sekunden |
| Prüfer parallel | §12 | schon da: `tools/run_tests.py` (Gruppen parallel), `ThreadPoolExecutor` in `pipeline.py`, `textures.py`, `imagemagick.py` | Wanduhrzeit = langsamster Prüfer |
| Render-Cache nach Szenen-Abdruck | §12 | teilweise: `modelcache.py` schlüsselt das ganze Worker-Paket samt Code, die Vorschau gehört zur Einheit; kein Abdruck der Szene | Treffer auch nach unwirksamen Codeänderungen |
| Ausgaben-Cache nach Inhalt | §17 | schon da: `cache.py` (`OutputCache`, `Store`), `modelcache.py`; Schlüssel mit `pipeline.image_code` | nichts schreiben, was gleich bleibt |
| Kanonische Reihenfolge | §12, §17 | teilweise: Schlüssel und FBX-Pfade kanonisch (`modelcache.py`, `fbxpath.py`, `asset.py` `digest`); keine reihenfolgeabhängige Operation wie Decimate | bitgleiche Ergebnisse je Prozess |
| Voxel-/Facetten-/Loch-Formvarianten | §15 | offen: Sets variieren das Innenleben (DEVELOPER 4), keine Formableitung mit gleichem Atlas | Stilvarianten ohne neue Texturen |
| Voxel-Flächen verschmelzen | §17 | offen (hängt an Voxel-Form) | weniger Dreiecke |
| Zeitband statt festes Budget | §17 | schon da: `tools/perf_band.py`, `STAGE_BUDGETS`, Lasterkennung (DEVELOPER 2) | keine Fehlalarme unter Last |
| Standard im Zielumfeld messen, alte Werte als neue ID | §19 | teilweise: Rückweg alter Namen (`materials.LEGACY_NAMES`, Vertragsversionen); keine Messung der Standardoberfläche in der dunklen Station | Standard sieht im Spiel richtig aus |
| Ein Cache für alle Checkouts | §20 | schon da: `~/Library/Caches/Cubegen/cache` (`cache.default_root`), atomar (`atomic_write`/`atomic_copy`), Aufräumen nach Größe (`Store.prune`), Übernahme (`migrate.py`); Dateikopie statt APFS-Klon | neuer Worktree startet warm |
| Prüfplan aus dem Diff | §20 | teilweise: Stufen `quick`/`standard`/`full` (`tools/run_tests.py`), Hook `golden-daten`; keine Zuordnung Datei → Prüfweg | nur nötige Prüfungen |
| Ruhige Maschine | §20 | teilweise: `pause_sessions.py` laut AGENTS.md, `perf_band.py` erkennt Last; kein `quiet.py` vor Volllauf | verlässliche Messwerte |
| Ein schwerer Lauf zur Zeit | §20 | teilweise: `HeavyLock` und `run_in_group` in `tools/unity_check.py`; `tools/run_tests.py --tier full` nimmt die Sperre nicht | keine Überlast bei parallelen Sitzungen |
| Release als ein Befehl | §21 | schon da: `tools/release.py` (Probelauf als Standard, `--apply`) | Release ohne Handarbeit |
| Bericht als Gate | §13 | teilweise: feste Golden-Daten statt Vorher-Nachher-Bericht – `tests/golden.json` (`Asset.digest` je Typ), `tests/quality_baseline.json`, `tests/test_golden.py`, `tests/test_quality.py` | Modelländerungen fallen sofort auf |
| Emitter als Daten | §10 | schon da: `Audio_*`/`FX_*`-Anker mit Sidecar (`models/anchors.py`) | Effekte ohne Partikel im Modell |
| Seed-Ströme getrennt | (RG §3 Abnutzung) | schon da: `seeds.derive_seed`, `a.sub("dressing")` – Zusatzteile ändern das Modell nicht | stabile Seeds |

## 1. Daten statt Code: Looks, Themen, Formate (RG §1)

**Was:** Ein Look ist ein Datensatz mit Palette, Oberfläche, Zonen und Metadaten, kein Python. Fehler nennen Datei und
Eintrag, IDs bleiben ewig, Listen wachsen nur am Ende, jedes Format hat Migration und Fixture.
**Cubegen heute:** Themen sind Daten (`paint.PAINTS`, `SCHEME_KEYS`) und kommen aus einer Datei (`--paint-file`,
`paint.load_scheme`, `check_scheme`); der Vertrag zu Cube Escape ist versioniert mit Rückweg (`contract_for`,
`--contract`). Die eingebauten Themen stehen aber im Quelltext, und `--paint-file` hat keine Formatversion.
**Umsetzung:** Die eingebauten Themen nach `cubegen/data/paints.json` auslagern, Format mit `format`/`version`,
Migration in `paint.py`, Fixture je Version in `tests/fixtures`. Das Golden-Digest bleibt gleich, solange nur der Ort
wechselt (Prüfstein: `tests/test_golden.py`). **Aufwand: M.**

## 2. Backen und Zusammensetzen (RG §2, §3, §4)

**Was:** Einmal mit schwarzer Palette backen (Konstante), je drei Palettenfarben ein Back (Gewichtskarten), jede
Variante per numpy. Masken statt Textursätze: Zonen, Abzeichen und Leuchtlinien als Kanäle, Zusammensetzen mit
Helligkeitsverhältnis, damit Schmutz und Kratzer bleiben. Messwerte: 62 Skins für den Preis von 6 Backs; Knotenzahl im
Material entscheidet den Aufbau (rund 1 ms je Knoten; gemeinsame Projektionen: 2,2 → 0,4 s).
**Cubegen heute:** Gewichtskarten und Zusammensetzen sind da (`stylebake.py`, `paint.compose`, `neutral.py`); die
gepackten neutralen Karten sind die Eingabe für den Shader in Cube Escape. Es gibt keine Zonen- und Decal-Kanäle.
**Umsetzung:** (a) Zonenkanal: beim Zusammenfügen ein Int-Attribut je Fläche aus dem Teilnamen (Name ohne `_L/_R`),
als Maske backen und in den Sidecar schreiben – neuer Kanal am Ende der Kartenliste, Vertragsversion +1 mit Rückweg.
(b) Decal-Anker je Modellfamilie neben den Klang-/Effektankern (`models/anchors.py`), Decal-Bibliothek per
ImageMagick. (c) Knotenzahl der Material-Bäume im Bericht messen, bevor optimiert wird. **Aufwand: L** (a, b), **S** (c).

## 3. Verwitterung als normierte Felder (RG §3 „Schichten und Werkstoffe“)

**Was:** Jede Schicht (Rost, Moos, Frost, Schmutz) ist ein gebackenes Skalarfeld; vor dem Gebrauch wird es durch seinen
Rang ersetzt (`equalise`), sodass Regler a genau den Anteil a bedeckt (Messwert dort: 49,9 % bei 0,5). Abnutzung kommt
vor Werkstoff und Schichten. Die Rangnormierung braucht ein Histogramm mit 65 536 Klassen statt voller Sortierung.
**Cubegen heute:** Regler je Thema (`wear`, `grime`, `rising_grime`, `dust`, `moss`, `paint.py`), Rauschflecken statt
flächiger Schichten (DEVELOPER 5). Ob die Regler gleich empfindlich sind, ist nicht gemessen.
**Umsetzung:** Nach dem Backen der Felder in `stylebake.py` die Rangnormierung anwenden und im Test die Abdeckung je
Reglerstufe prüfen (Erwartung: Stufe a ≈ Anteil a). Ändert die Karten, also Golden-Daten und `MTN_`-Bytes bewusst
aktualisieren (Hook `golden-daten`). **Aufwand: M.**

## 4. Formvarianten aus einem Modell (RG §15, §17)

**Was:** Facetten-, Voxel- und Lochform entstehen als Ableitung der Grundform mit gleichen Vertex-Gruppen, Materialien
und UVs, also mit gleichem Atlas und gleicher QA. Voxel nur, wenn der Zellmittelpunkt eine halbe Zelle tief im Teil
liegt (bei einem Viertel ragten Würfel bis 7 mm heraus); Gelenke und dünne Teile bleiben glatt; gleich aussehende
Nachbarflächen werden zu Rechtecken verschmolzen (17 136 → 11 348 Dreiecke).
**Cubegen heute:** Variantensets mit gleichem Umriss und anderem Innenleben (`--set`, DEVELOPER 4), Kristallschliff
(`crystal_cut`); keine Formableitung.
**Umsetzung:** Als eigene Stilachse `shape = smooth | voxel | facet` des Stils, abgeleitet nach dem Bau und vor dem
Atlas, Kollisionsrezept der Grundform übernehmen (innen rastern, Kleinteile glatt). Erst nach Atlas-Nachpacken (§6)
und mit eigener Golden-Gruppe. **Aufwand: L.**

## 5. Vorschau, Katalog, Icons (RG §5, §6, §7, §8)

**Was:** Karten in Dreiviertel-Ansicht mit Randlicht und Bloom (Schwelle über der normalen Beleuchtung, sonst strahlt
alles); Konzeptbögen mit festem, am Prüfbild vermessenem Raster auslesen (automatisches Suchen scheiterte); Icons mit
deterministischer Lesbarkeitsprüfung (Objekt füllt 30–96 % der längeren Seite und sitzt mittig, unter 1 s für 113
Icons). Viewer: Daten-Texturen roh laden (NSImage multipliziert RGB mit Alpha vor), SceneKit-Shader ab etwa 23
Argumenten stillschweigend pink – Uniforms packen.
**Cubegen heute:** Kontaktbögen und Set-Reihen, Konzeptvergleich im Stiltest, Icons je Modell. Die Lesbarkeit prüft nur
das Hinweiswerkzeug `tools/vision_report.py` (Neural Engine, je Gerät andere Werte, nie im normalen Lauf).
**Umsetzung:** (a) Die Icon-Prüfung als reine Bildmessung (Füllgrad, Mittelpunkt) in `imagemagick.py`/`pipeline.py`,
als Hinweis im Manifest – ersetzt das Neural-Engine-Werkzeug nicht, läuft aber immer. **Aufwand: S.**
(b) In `app/Sources` prüfen, ob Karten mit Alphakanal und viele Shader-Parameter betroffen sind (RG §8-Fallen);
`ModelScene` lädt heute über MTL, nicht über rohe Texturen. **Aufwand: S (Prüfung), M (falls Umbau).**
(c) Dreiviertel-Karte mit Randlicht für Set-/Katalogübersichten, Bloom nur auf Emission. **Aufwand: M.**

## 6. Atlas packen (RG §16)

**Was:** Belegung messen (Smart UV Project allein belegte 18 %), nach dem Abwickeln konkav nachpacken
(`pack_islands(shape_method="CONCAVE", rotate=True, …)`; bei Tausenden Inseln bestimmt der Inselabstand die Belegung:
0,003 → 0,002 ergab 41 → 51 %); Bake-Ränder höchstens den halben Inselabstand dilatieren, wenn mehrere Durchgänge in
einen Atlas schreiben.
**Cubegen heute:** `bake._atlas_uvs` ruft `smart_project(angle_limit=66°, island_margin=0.02)` auf, kein Nachpacken,
keine Belegungskennzahl. Die Atlas-UVs werden gecacht (`bake.read_uvs`/`apply_uvs`).
**Umsetzung:** Belegung (UV-Polygonfläche je Atlas) im Manifest als Kennzahl ausgeben; danach Nachpacken als Option
mit eigenem Cache-Schlüsselanteil (ändert Texturen und damit `modelcache.model_code`). Atlas-Größe nur ändern, wenn
das Texturbudget (`CubegenTextures`) es verlangt. **Aufwand: S (Kennzahl), M (Nachpacken).**

## 7. Effektmaterialien, LOD, Kollision (RG §11)

**Was:** Spezialmaterial als Laufzeit-Effekt über dem Skin, jede Formel in Vorschau und Spiel gleich, Beschreibung fürs
Zielmaterial als Daten (`urp`); LOD per Decimate „Collapse“ mit anschließendem „Smooth by Angle“ (6 000 / 2 500
Dreiecke); Treffer-Kapseln aus der Geometrie gemessen (93. Perzentil des Achsabstands, Enden 0,3 r innerhalb des 2./98.
Perzentils; 95–100 % Abdeckung).
**Cubegen heute:** LOD1 ist ein eigener Bau mit `detail = low` (sauberer als Collapse, weil Teile und Namen erhalten
bleiben), Kollision aus Rezepten mit Prüfung gegen die Geometrie (`collision.py`, `quality.py`; AGENTS.md verlangt den
Nachweis über den echten Unity-Import). Effektmaterialien sind Cube-Escape-Sache.
**Umsetzung:** (a) Dreiecksbudget je LOD-Stufe als Prüfung (`check_runtime_budget` erweitern). **Aufwand: S.**
(b) Für Typen ohne Rezept eine gemessene Kapsel/Box-Zerlegung als Vorschlag, nie als Ersatz des Rezepts; ein Erfolg
der Bounds-Prüfung ist kein Physiknachweis (AGENTS.md). **Aufwand: L.**
(c) Effekt-Beschreibung (`urp`-artig) im Sidecar nur zusammen mit Cube Escape (ROADMAP ToDo 28). **Aufwand: M.**

## 8. Prüfen und Cachen (RG §12, §13, §17, §20)

**Was:** QA-Ergebnisse nach Mesh, Rig und Prüfcode cachen (Prüfcode als Quelltext der QA-Funktionen im Schlüssel;
Standardlauf 121 → 51 s); Bilder nach dem Szenen-Abdruck statt nach dem Code (405 von 405 Vorschaubildern aus dem
Cache); Hashes über kanonische Daten; Ausgaben nach Inhalt; Cache außerhalb der Arbeitskopie, Einträge nach Inhalt,
atomar, nach Größe aufräumen (erster Volllauf im neuen Worktree 628 → 87 s).
**Fallen aus Robogen:** alle eingebetteten Materialbäume heißen gleich – nach Identität unterscheiden; veraltete
`matrix_world` bis `view_layer.update()`; Ausgabewerte verknüpfter Wertknoten gehören in den Abdruck (sonst blieb eine
geänderte Standardoberfläche unbemerkt); absolute Pfade im Schlüssel (nie ein Treffer im anderen Checkout).
**Cubegen heute:** der Cache-Teil ist weitgehend da (`cache.py`, `modelcache.py`, `migrate.py`, `pipeline.image_code`;
DEVELOPER 3). Offen: QA-Ergebnisse (`quality.report`, `uncovered_geometry` – teuer, rein aus Geometrie und Code
bestimmt), Bildabdruck der Szene, APFS-Klone (`atomic_copy` kopiert).
**Umsetzung:** (a) QA-Cache in `cache.Store`: Schlüssel = `Asset.digest` + Quelltext der Prüffunktionen
(`inspect.getsource`, wie `pipeline.image_code`) + Prüfparameter; Treffer liefert das Ergebnis-JSON.
Erwartung: spart den Großteil der Prüfzeit warmer Läufe; Messung nach Einführung mit `tools/perf_band.py`.
**Aufwand: M.** (b) APFS-Klon unter macOS im Kopierpfad (`cp -c` bzw. `clonefile`), Rückfall auf Kopieren. **Aufwand: S.**
(c) Szenen-Abdruck erst, wenn Vorschau-Fehltreffer nach unwirksamen Änderungen in `modelcache` messbar stören; die
Fallen oben vorher in einem Test festhalten. **Aufwand: L.**

## 9. Testablauf und Maschine (RG §9, §13, §20, §21)

**Was:** Prüfplan aus dem Diff (Zuordnung Datei → Bereich → Weg, `scripts/testplan.py`); Last prüfen, bevor gemessen
wird (`quiet.py`); eine rechnerweite Sperre für schwere Läufe mit Halterzeile (`heavy_lock.py`; Fallen: vererbter
Deskriptor → `O_CLOEXEC`, Prozessgruppe, Kinder mit `CE_HEAVY_HELD=1`, Regel: der Halter wartet nur, rechnet nie
selbst); Release als ein Befehl mit Probelauf; Unity-Tests in einem Start (Testbett 25–30 → 12 s); ein Unity-Testprojekt
je Generator, das auch Blickrichtung, Materialien und Screenshots prüft; Compiler-Fehler brechen im Batch-Modus nicht
ab – Log nach `error CS` durchsuchen.
**Cubegen heute:** `tools/release.py` (Probelauf), `HeavyLock`/`run_in_group` in `tools/unity_check.py`, Stufen und
parallele Gruppen in `tools/run_tests.py`, `tools/perf_band.py`. Nicht da: Zuordnung Datei → Prüfweg, Sperre für die
volle Suite, Suche nach `error CS`.
**Umsetzung:** (a) `run_tests.py --tier full` hält dieselbe Sperre wie `unity_check.py` (gleicher Vertrag, gleiche
Datei; Vertrag nur zusammen mit Cube Escape und dem Roboter-Generator ändern, DEVELOPER 7). **Aufwand: S.**
(b) `tools/testplan.py` mit Tabelle Pfad → Stufe/Zusatzprüfung (z. B. `cubegen/models/**` → `standard` + Golden,
`app/**` → `app/test_app.sh`, Doku → nichts); `--run` führt aus. **Aufwand: M.**
(c) In `unity_check.py` das Unity-Log nach `error CS` durchsuchen und den Lauf scheitern lassen, falls das nicht
schon die Cube-Escape-Seite tut (dort prüfen). **Aufwand: S.**

## 10. Standardwerte im Zielumfeld (RG §19)

**Was:** Die Vorschau leuchtet hell aus, die Station ist dunkel und matt (Metallic 0, Smoothness 0,4–0,5): Die
Standardoberfläche wurde dort gemessen und geändert, nicht die Masken; der alte Wert blieb als neue ID am Ende.
**Cubegen heute:** Rückweg alter IDs ist üblich (`materials.LEGACY_NAMES`, Vertragsversionen). Dass die Standardwerte
der Modelle in der Station gemessen werden, ist nicht belegt.
**Umsetzung:** Im Unity-Check (`unity_check.py`) einen Screenshot-Satz in der Station-Beleuchtung gegen Referenzwerte
vergleichen; Änderungen an Standardmaterialien nur als neue ID. **Aufwand: M.**

## 11. Reihenfolge und Determinismus (RG §12, §17)

**Was:** Blender legt Ecken, Flächen und Insel-Packen je Prozess unterschiedlich ab; Hashes und reihenfolgeabhängige
Operationen (Decimate) brauchen eine kanonische Kopie; neue BMesh-Elemente haben keinen gültigen `index` (nach dem Bau
`index_update()`); Innen-Tests mit drei leicht schrägen Strahlen und Mehrheitsentscheid; „gleich“ heißt bytegleich
(ImageMagick-Zeitstempel, Cycles-Abweichungen).
**Cubegen heute:** kanonische Schlüssel (`modelcache.py`, `fbxpath.py`), `imagemagick.REPRODUCIBLE`,
`cache.png_content_hash`, getrennte Seed-Ströme (`seeds.py`); Innen-Test in `quality._inside_solid` mit `ray_faces`.
Der Innen-Test nutzt **einen** achsparallelen Strahl nach +x mit Paritätsregel – genau die Lücke, die RG §17 bei
rasterförmig gebauten Teilen beschreibt (Strahl streift Kanten und Ecken).
**Umsetzung:** `_inside_solid` auf Mehrheit aus drei leicht schrägen Strahlen umstellen; Ergebnis über die Golden- und
Qualitätsbasis (`tests/quality_baseline.json`) belegen. **Aufwand: S.**

## Nicht übertragbar

Federknochen, gebackene Nachschwingung, Servo-Ereignisse, Requisiten per Matrix-Kette, Proportionen per Knochen-Matrix,
gesetzte Kontakte und Rollen über die Hülle (RG §10, §11, §15, §18) setzen Rig und Clips voraus; Cubegen liefert
statische Modelle und bewegliche Teile als benannte Unterteile, deren Bewegung Cube Escape macht (`Rotator`,
`Machine`). Kommt in Cubegen ein Rig dazu, die Abschnitte wieder aufnehmen. Der Schrift-Hinweis (RG §6, Hiragino)
gilt für Cubegen sinngemäß: Schriften mitliefern oder Zeichen als Pfade zeichnen, wo es plattformunabhängig bleiben soll
(`models/lettering.py`).

## Checkliste (RG §14)

Abgehakt nur, was Cubegen nachweislich ganz hat; bei „teilweise“ steht, was fehlt.

- [ ] Looks/Paletten als versionierte Datendatei mit Loader-Prüfung und Migration – teilweise: `--paint-file` mit
      `check_scheme`, aber eingebaute Themen im Quelltext (`paint.py`), keine Formatversion/Migration
- [x] Farbvarianten aus einmal gebackenen Gewichtskarten zusammensetzen – `cubegen/stylebake.py`, `paint.compose`;
      die Referenzformel prüft `tools/paint_reference.py` (eine Gegenprobe im Volllauf ist nicht belegt)
- [ ] Maskenkanäle (Zonen, Abzeichen, Leuchtlinien) statt Textursatz je Variante – teilweise: `MTN_`-Karten (`neutral.py`)
- [ ] Formvarianten (facettiert, Voxel, Lochung) als Ableitung mit gleichem Atlas und gleicher QA – offen
- [ ] Lackzonen über benannte Teile → Flächenattribut → Attribute-Node – offen
- [ ] Decal-Anker je Modellfamilie, Decal-Bibliothek per ImageMagick – teilweise: nur Klang-/Effektanker
- [ ] Gemeinsame Teilgraphen in Materialien (Knotenzahl messen) – offen
- [ ] Präsentationskarten mit Dreiviertel-Kamera, Randlicht, Bloom nur auf Emission – teilweise: Kontaktbögen
- [ ] Icons je Modell/Variante mit Lesbarkeitsprüfung – teilweise: Icons da, Prüfung nur als Hinweis (`vision_report.py`)
- [ ] Vorschau-App: Daten-Texturen roh laden, Uniforms packen, A/B-Vergleich, GIF/MP4-Export – offen (nicht geprüft)
- [ ] Bericht-Gate: Kennzahlen vor und nach jeder Änderung vergleichen – teilweise: feste Golden-Daten (`tests/golden.json`),
      `tests/quality_baseline.json`, `tests/test_golden.py`, `tests/test_quality.py`
- [ ] Unity-Testprojekt je Generator – teilweise: `tools/unity_check.py` in der Cube-Escape-Testkopie, kein eigenes Projekt
- [ ] Verwitterung als normierte Felder mit Regler, Werkstoff-Muster – teilweise: Regler je Thema, ohne Normierung
- [ ] Anbauteile: jede Variante in einer geprüften Kombination, Anschmiegen per Strahl, Emitter als Daten – teilweise:
      Emitter als Daten (`models/anchors.py`), Anbauten (`models/dressing.py`); kein Anschmiegen per Strahl
- [ ] Nachschwingen gebacken, Requisiten per Matrix-Kette – nicht übertragbar (kein Rig)
- [ ] Effektmaterialien als Laufzeit-Effekt mit Zielbeschreibung; Masken für die Engine packen – teilweise: Masken
      gepackt (`neutral.py`), Effekte offen
- [ ] LOD-Stufen und Kollisionsformen automatisch erzeugen und in der Engine prüfen – teilweise: `--lods`, Rezepte und
      Unity-Check; keine Dreiecksbudgets je Stufe
- [ ] Prüfergebnisse cachen, Bilder nach Szenen-Abdruck, Prüfer parallel, Engine-Prüfung in einem Prozess – teilweise:
      parallel (`run_tests.py`) und Modell-Cache da; QA-Cache und Szenen-Abdruck offen

## Empfohlene Reihenfolge (Nutzen/Aufwand)

1. **Sperre für die volle Suite** (§9a, S): `run_tests.py --tier full` an die gemeinsame Sperre; verhindert Überlast
   bei parallelen Sitzungen, kein Einfluss auf die Ausgabe.
2. **QA-Cache** (§8a, M): größter Zeitgewinn warmer Läufe, keine Änderung der Modelle; Schlüssel mit Prüfcode.
3. **Atlas-Belegung messen, dann nachpacken** (§6, S/M): zuerst nur die Kennzahl, Nachpacken danach mit bewusst
   aktualisierten Texturen und Golden-Daten.
4. **Prüfplan aus dem Diff** (§9b, M): spart tägliche Prüfzeit und Fehlgriffe bei der Stufenwahl.
5. **Icon-Lesbarkeit als Bildmessung** (§5a, S): deterministisch, läuft in jedem Lauf, ersetzt das Rätselraten nach
   Sichtprüfung; danach Looks als versionierte Daten (§1, M) als Grundlage für Zonen und Decals (§2, L).

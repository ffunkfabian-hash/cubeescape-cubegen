# Cubegen – Entwicklerhintergrund

`AGENTS.md` hält die knappen Regeln; hier stehen die Begründungen, Messwerte und Einzelheiten dazu. Die Abschnitte
tragen dieselben Namen wie die Verweise in `AGENTS.md`. Die Bedienung der Kommandozeile steht in
[`CLI.md`](CLI.md). Techniken des Roboter-Generators, die Cubegen übernehmen kann (mit Stand und Aufwand):
[`TECHNIK.md`](TECHNIK.md).

## 1. Leistung und Grenzen (Erkenntnisse aus Cube Escape 0.49, seit 0.21.0)

- **Ein Renderer, wo es geht:** Cube Escape baut statische Modelle mit höchstens einem MeshRenderer und Kollision auf
  dem Modell in großen Leveln als flache Kopien; in Unity kostet jedes Teil pro Objekt, nicht pro Dreieck.
  `--single-renderer` (`Asset.merge_static`) fasst die Mesh-Objekte statischer Modelle zusammen, deren Teile nur Optik
  tragen (`asset.DECORATIVE_PARTS`); Teile mit Bedeutung (Panel, Tile_<n>, Fluid, Rotor …) lassen das Modell, wie es
  ist. Neue Typen: Schmuckteile mit Namen aus der Liste benennen, Teile mit Bedeutung nicht. `--lods` ergibt zwei
  Renderer (LOD0/LOD1).
- **Grenzen in Bytes, wo Dateien oder Speicher gemeint sind:** ein UTF-8-Zeichen hat bis zu drei Bytes – nie die
  Länge eines Strings mit einer Byte-Grenze vergleichen. Zeichen nur, wo Zeichen gemeint sind (Glyphen der
  Schrift, `check_text`). Budget der Werkbank: `contract.RUNTIME_BUDGET` (aus Cube Escape abgeschrieben, beim Ändern
  dort nachsehen); `check_runtime_budget` prüft jedes GLB beim Erzeugen und in `check --export`. Texturspeicher wie
  Cube Escape 0.51 (`CubegenTextures`): jede verschiedene (Rolle, Bildinhalt) einmal, BC3 mit 1 Byte je Pixel × 4/3,
  Metall/Rauheit einmal als Metall-/Glättekarte.
- **Index statt jede Datei lesen:** Größe und Änderungszeit entscheiden, ob eine Datei neu gelesen werden muss
  (`OutputCache` `stats`/`index`, `digest`); erst bei Abweichung wird gehasht.
- **Erst Schritte benennen, dann optimieren:** neue Arbeit bekommt einen Schritt in `timings.steps` (Manifest);
  Vergleiche als Band über mehrere Läufe mit Lasterkennung: `tools/perf_band.py --save <vorher>` / `--compare`
  (ruhig / leicht = Toleranz ×2 / stark = Laufzeit nicht gewertet, CPU-Zeit zählt immer). Einzelläufe auf einem
  belebten Rechner sind keine Messung (0.21.0: 5–14 s für denselben Lauf).
- **Verzeichnisse statt Suchen:** in Schleifen nie linear suchen (`x in liste`, `next(o for o in … if o.name == …)`,
  `asset.get` je Element) – vorher ein Dictionary oder Set bauen. Gebaute Modelle eines Laufs liegen in
  `asset_of`/`lod_of`: jedes Modell wird je Lauf genau einmal gebaut (Test).

## 2. Blender-Batch schnell halten (Erfahrungen aus dem Roboter-Generator)

Gemessen im Roboter-Generator (Repo `ffunkfabian-hash/cubeescape-robogen`, Version 1.8 „Turbo“ und 1.9
„Afterburner“, Apple M5, Blender 5.2): ein Volllauf von 40 auf 3,5 Minuten, bei identischen QA-Ergebnissen.
Die Regeln gelten für jeden Blender-Batch-Lauf dieses Repos. Messen statt raten: `cProfile` per Wrapper-Skript um
`main()`, für Wartezeiten in C-Code macOS `sample <pid> 5` (zeigt, worauf der Hauptthread wartet), GPU-Auslastung ohne
sudo über `ioreg -r -c IOAccelerator` (`Device Utilization %`). Zeiten nur auf ruhiger Maschine vergleichen –
parallele Unity-/Blender-Läufe anderer Agenten verlangsamen um das Zwei- bis Fünffache; die Systemlast mitprotokollieren.

- **Cycles backt jedes ausgewählte Objekt in einer eigenen Sitzung.** Auf Metal kostet jede eine
  Geräte-Synchronisation (35 Teile: 9–20 s je Durchgang statt 0,2–1 s). Eine zusammengefügte Kopie aller Teile
  backen und die Bilder weiterverwenden – `cubegen/bake.py` macht das seit 0.15.0 (auch auf der CPU schneller:
  `sliding_puzzle` 3,7 → 1,1 s). Die GPU lohnt sich bei Cubegens kleinen Atlanten erst ab 1024 px
  (`--bake-device auto`). Cycles-Vorschauen (nur Rückfall ohne OpenGL) bleiben ungemessen auf der CPU.
- **Lineares nicht mehrfach backen.** Farben, die nur durch Mischen und Multiplizieren mit festen Faktoren
  entstehen, sind linear in der Palette: eine Konstante plus eine Gewichtskarte je Palettenfarbe backen, jede
  weitere Palette per numpy zusammensetzen (exakt; einmal direkt gegenbacken und vergleichen).
- **Blenders UV-Packen und Flächenreihenfolge sind nicht deterministisch.** Cache-Schlüssel über eine kanonische
  Ecken-Reihenfolge bilden; UVs cachen, sonst trifft kein Bake-Cache und Texturen wechseln von Lauf zu Lauf.
- **EEVEE: Ein einziges Material mit `surface_render_method = "BLENDED"` verdoppelt die Renderzeit.** Es erzwingt die
  Forward-Pipeline, und EEVEE wartet je Sample ein zweites Mal auf die Schatten-Aktualisierung
  (`ShadowModule::shadow_update_finished`, GPU-Rücklesen). Die Auflösung ist dagegen fast egal (150 px 0,34 s,
  600 px 0,44 s bei 24 Samples) – die Kosten hängen an den Samples. Für Vorschauen deckend oder `DITHERED` rendern,
  Samples senken, Raytracing aus; das exakte Bild nur für wenige Hauptansichten.
- **Mehrere Blender-Prozesse:** Startparameter `-t 1` (bzw. wenige Threads) für CPU-lastige Worker – ohne Grenze
  startet jeder Prozess einen Thread-Pool je Kern (gemessen: 734 statt 419 Prozess-Sekunden). Worker mit `nice`
  starten, wenn der Hauptprozess den kritischen Pfad hat. Arbeitspakete dynamisch verteilen (Anspruch per exklusiv
  angelegter Datei), größte zuerst; Ergebnisse in fester Reihenfolge zusammenführen. EEVEE: mehr als 3–4
  Render-Prozesse lohnen nicht, die GPU ist dann ausgelastet. `--jobs` (`cubegen/pipeline.py`) verteilt seit 0.15.0
  Arbeitspakete; `nice` entfällt, weil kein Prozess den kritischen Pfad hat. **`-t` nicht für Cycles-Backen:** Die
  Grenze gilt für Python-lastige Worker; Cubegens Worker backen echt parallel, mit `-t Kerne/Jobs` war das Station-Kit
  langsamer (50–54 s statt 47–49 s, `--jobs 3`, gemessen 0.15.0). Auch ohne Backen bringt `-t 1` nichts (186 Typen,
  Export und Vorschau, innerhalb der Streuung; 0.16.0).
- **`--jobs auto` (Standard seit 0.16.0, `pipeline.auto_jobs`):** bis Kerne − 1, je Prozess mindestens 2 s Arbeit
  (Start ≈ 0,6 s). CPU-Backen skaliert nicht (Cycles nutzt alle Kerne: 1–9 Prozesse 69–77 s) → höchstens 2;
  GPU-Arbeit höchstens 3. Neue Arbeit bekommt ihre Schätzung in `SECONDS_PER_MODEL` aus einer Messung.
- **ImageMagick parallel nur mit `MAGICK_THREAD_LIMIT=1`.** Die OpenMP-Threads paralleler Prozesse warten aktiv
  aufeinander (eine Montage aus 28 Kacheln: 1,6 s statt 3,8 s, parallel noch deutlich mehr). Die Ausgabe bleibt
  bitgleich. Cubegen setzt es für die Blender-Worker von `--jobs` (`bake._magick`) und für seine eigenen parallelen
  Aufrufe (`ImageMagick.single_threaded`: Texturen je Material, Icons je Modell, Kontaktbogen in Blöcken).
- **Beschriftungen in `montage` sind teuer** (≈ 70 ms je Label, 186 Modelle 15–20 s): große Kontaktbögen in Blöcken
  zu `SHEET_ROWS` Zeilen parallel montieren und mit `-append` stapeln – pixelgleich (Test), 2 statt 20 s.
- **Stufen überlappen:** Was Blender nicht sofort braucht, läuft daneben. Die Kacheltexturen entstehen, während die
  Blender-Prozesse starten (`textures.plan_texture_set` liefert Namen und Pfade vorab, eine Bereit-Datei gibt frei);
  `timings.overlap` nennt solche Stufen, ihre Zeiten sind dann nicht addierbar.
- **Bytegleiche Bilder sind die Voraussetzung für jeden Cache.** Jeder ImageMagick-Aufruf läuft mit
  `imagemagick.REPRODUCIBLE` (`-define png:exclude-chunks=date,time`); `cubegen/cache.py` übernimmt Texturen, Icons,
  Kontaktbogen, Set-Reihen und Material-Übersicht nur, wenn Eingabeschlüssel und Datei-Hashes stimmen – aus dem
  eigenen Ordner oder aus dem gemeinsamen Cache (Abschnitt 3). Neue Bildschritte nutzen denselben Cache; ein Test
  erzeugt zweimal und vergleicht die Bytes.
- **Zeiten messen statt schätzen:** Das Manifest trägt `timings` mit Budget je Stufe (`STAGE_BUDGETS`); eine neue
  Stufe bekommt ein Budget aus einer Messung. Nach Code-Änderungen `python3 tools/run_tests.py --tier quick`
  (rund 30 s), vor dem Release die volle Suite.
- **numpy-Kleinkram:** `foreach_get("co", …)` in ein `float32`-Array lesen (das native Format; `float64` erzwingt eine
  langsame Umwandlung, 3× langsamer), Hüllquader-Tests für alle Paare auf einmal statt einzeln je Paar.
- **Prüfung und Modellbau bleiben reines Python (0.16.0 entschieden):** `fix_z_fighting` bestimmt die Geometrie; eine
  andere Summationsreihenfolge (numpy) könnte Grenzfälle kippen und die Golden-Daten brechen, und die Flächengruppen
  sind zu klein, als dass Arrays sich lohnen. Robogens Idee gilt trotzdem: billiger Hüllquader-Test vor der teuren
  Prüfung – aber nur für Flächen, die überhaupt verglichen werden (alle vorab zu rechnen war langsamer), und teure
  Vorarbeit einmal je Teil statt je Probepunkt (`quality.ray_faces`). Ergebnis bytegleich prüfen (Prüf-JSON,
  erzeugte Dateien), CPU-Zeit vergleichen statt Wanduhr, wenn fremde Last läuft.
- **Gewichtskarten statt Backen je Farbgebung** (seit 0.17.0 im Stiltest `cubegen/paint.py`, `stylebake.py`): die
  Spielmaterialien als Gewichte (drei je RGB-Bild), Farbe = Summe aus Gewicht × Farbe – jede Farbgebung kostet
  Sekundenbruchteile statt eines Back-Laufs. Bisher nicht übertragbar war es nur, weil Cubegen keine Paletten backte
  (`palette.py` ist reines Python, `baked` backt eine Palette je Lauf). EEVEE-`BLENDED` – kein Cubegen-Material ist
  transparent. `foreach_get` als `float32` – Cubegen liest keine Meshes mit `foreach_get`. Kommen solche Fälle
  dazu (z. B. Texturvarianten je Palette, transparente Materialien), gelten die Regeln oben.
- **Die Neural Engine nutzt Blender nicht** (nur über Core ML erreichbar); Metal verteilt GPU-Arbeit selbst auf alle
  GPU-Kerne. Geprüft in 0.14.2: Vision-Merkmalsvergleiche taugen nicht als Prüfschranke (je Gerät andere Werte,
  trennen Fehler nicht besser als ein exakter Pixelvergleich); höchstens als Hinweiswerkzeug mit Zeitregel (ROADMAP).

## 3. Gemeinsamer Cache (seit 0.25.0, Erfahrungen aus dem Roboter-Generator 1.20)

Ein Cache je Ausgabeordner machte jeden neuen Worktree und Ordner kalt. Seit 0.25.0 liegt der inhaltsadressierte
Teil an **einer** Stelle für Haupt-Checkout, Worktrees, App und `unity_check.py`: `~/Library/Caches/Cubegen/cache`
(Linux `$XDG_CACHE_HOME/cubegen/cache`, sonst `~/.cache/…`), `CUBEGEN_CACHE=<Ordner>` verlegt ihn, `CUBEGEN_CACHE=0`
schaltet ihn ab. `python3 -m cubegen cache` zeigt Ort und Größe (`--prune`, `--migrate DIR`).

- **Was wohin:** `objects/<ab>/<sha256>` Dateiinhalte, `entries/<ab>/<Schlüssel>.json` Schlüssel → Rollen und Daten;
  im Ausgabeordner bleibt nur, was an den Ordner gebunden ist (`.cubegen_cache.json` Format 2: welche Dateien dort
  aktuell sind, Pfade relativ). `--force` verwendet nichts wieder, trägt aber ein (wie bisher).
- **Schlüssel nur aus Eingaben, nie aus Pfaden:** kein absoluter Pfad in Schlüssel oder Einträgen (0.24 hatte den
  Texturordner im Schlüssel). Der Code-Anteil ist der Hash des Bildcodes (`pipeline.image_code`: `imagemagick`,
  `textures` und was sie importieren – eine Änderung anderswo im Generator lässt den Cache warm); ImageMagick-
  Argumente, die in `pipeline.py` stehen, gehören selbst in den Schlüssel (`SET_ROW_*`). Vorschauen zählen mit ihrem
  Bildinhalt (`png_content_hash`): Blender stempelt Datum und Renderzeit hinein.
- **Atomar schreiben** (Temp-Datei im selben Ordner, dann umbenennen), Inhalte vor dem Eintrag; ein kaputter Inhalt
  erreicht nie einen Ausgabeordner (Hash beim Kopieren geprüft). Ein Fehler des Cache-Laufwerks bricht keinen Lauf ab.
- **Größe:** `CUBEGEN_CACHE_LIMIT_GB` (Standard 4); höchstens stündlich wird gekürzt, am längsten Unbenutztes zuerst,
  nichts aus den letzten zwei Stunden (ein Treffer frischt den Eintrag auf) – kein Schritt löscht, was ein anderer
  Checkout gerade braucht.
- **Übernahme alter Caches:** einmal je Cache (`migrated.json`) aus `output/` des Haupt-Checkouts und des eigenen –
  nur Einträge, deren alter Schlüssel sich aus dem Manifest exakt nachrechnen lässt und deren Generator denselben
  Bildcode hatte (`migrate.MIGRATABLE`, heute 0.24.0). Ändert sich der Bildcode, Eintrag dort und im Test entfernen.
- **Blender-Ergebnisse** (seit 0.26.0, `cubegen/modelcache.py`): ein Modell ist eine **Einheit** aus Export(en) mit
  Nebendateien (MTL, glTF-Puffer), Backen bzw. Anstrich-Karten (`MTA_`/`MTP_`/`MTN_`, `Neutral/`) und Vorschau – alles
  aus demselben Blender-Lauf, die Karten passen also immer zu den UVs des FBX. Der Schlüssel ist der ganze Auftrag
  des Workers samt Spec (Ordner als Rollen, der Texturordner relativ zum Modellordner, die Kacheltexturen über ihren
  `texture_key`), dazu `modelcache.model_code()` (das ganze Paket ohne die Versionszeile), Blender- und
  ImageMagick-Version und Plattform; bleibt ein absoluter Pfad übrig, wird das Modell nicht gecacht. **Nur das FBX ist
  ordnergebunden** (absolute Texturpfade in `Texture.FileName`, `Video.Filename`/`Path`): der Cache hält es kanonisch
  (`cubegen/fbxpath.py`, `<cubegen:textures>/…`), ein Treffer setzt den neuen Ordner ein – jedes andere Byte bleibt,
  wie Blender es schrieb (Zeitstempel und Objekt-IDs sind ohnehin je Export neu; Cube Escape liest die Texturen über
  den Sidecar, Unity-Check). Verfehlt die Einheit (andere Formate, Vorschau-Einstellungen, Anstrich mit gleichem
  Leuchtton), hilft der **Back-Cache** (`bake`): Karten des Backens samt **Atlas-UVs** (`bake.read_uvs`/`apply_uvs`,
  float32); der Worker setzt die UVs statt Smart UV Project und überspringt Cycles, Export, Anstrich und Vorschau laufen
  neu. Smart UV Project ist hier deterministisch (`test_release_0150`), der Cache verlässt sich nicht darauf. Nicht im
  Cache: die Übersichts-`.blend` (absolute Bildpfade) – ein voller Treffer startet Blender nur noch für sie
  (`--no-blend`: gar nicht). Neue Worker-Ausgaben gehören in die Einheit (`modelcache.result_files`), neue Eingaben in
  den Auftrag (dann automatisch im Schlüssel).
- **QA-Cache** (seit 0.30.0, `quality.check_cached`): Eintrag `qa` mit dem Ergebnis-JSON von `check` (keine Dateien).
  Schlüssel: `Asset.digest()` (Geometrie, Collider, Behaviours), Kategorie, Pivot, Budget-Faktor, Palette und der Hash
  der Prüfmodule samt Importen (`QA_MODULES`: quality, families, collision, palette; `pipeline.module_fingerprint`) –
  jede Änderung am Prüfcode macht alle Einträge ungültig, ohne Zutun. Ein Treffer ersetzt Z-Fighting-Test und
  Innenpunkt-Strahlen. Gemessen (golden_cases.quality, 187 Typen × 10 Varianten): kalt 7,1 s, warm 4,6 s – der Rest ist
  der Modellbau; der Cache lohnt sich für `cubegen check` und Gate-Läufe, nicht für einzelne Modelle. Das Ergebnis ist
  die JSON-Form (Tupel werden Listen).
- **Tests** laufen mit einem eigenen, frischen Cache je `run_tests.py`-Lauf (nie mit dem des Rechners).

## 4. Variantensets (Variation ohne Wiederholung)

Wunsch des Nutzers (0.17.0) für **alle** Modelle: Teile, die im Level nebeneinander stehen, dürfen nicht gleich
aussehen. Ein Set sind Varianten mit **gleichem Umriss** und **anderem Innenleben** (`--set`, Manifest `sets`).

- **Umriss nur über Parameter:** Alles, was den Anschluss bestimmt (Länge, Höhe, Breite, Tiefe, Radius), ist ein
  Parameter (`Param(size=True)` oder ein Name aus `OUTLINE_PARAMS`), nie ein im Builder gewürfelter Wert und keine
  Zufallsskalierung (`_mark` skaliert die übrigen Prototypen – Set-Teile nicht). Ein schon gewürfeltes Maß wird
  Parameter mit `p.value("name", <derselbe Wurf>)` – der Zufallsstrom bleibt, jede bestehende Variante auch.
  `--set` hält diese Parameter fest und prüft danach die Hüllquader-Seiten, an denen Nachbarn anschließen:
  `set_faces` am Typ (`@model(..., set_faces=...)`; Standard Wand: links/rechts, unten/oben, Rückseite – Boden: vier
  Seiten und unten, Details dürfen oben stehen; Decke: vier Seiten und oben; Ecke: rechts, hinten, unten, oben).
  Formwahlen, die ein anderes Teil ergeben (Art einer Ecke, Treppe oder Rampe, Geländer), hält `set_pins` fest.
  `outline_ok = false` heißt, der Typ ist (noch) nicht set-fähig. Set-fähig seit 0.19.0: das ganze Bau-Kit (Wand,
  Boden, Decke, Deckenplatte, Steg, Geländer, Säule, Kiste, Treppe, Plattform, Rampe, Wandabschluss, Ecke).
- **Anschlüsse durchlaufen lassen:** Sockel, Deckel und Kern an der vollen Länge; Muster mit einer Periode, die die
  Länge teilt (Warnstreifen 0,2 m bei 2 m), damit sie über den Stoß weiterlaufen.
- **Innen variieren** (`rng`, also reproduzierbar je Seed): Aufteilung (Spalten/Blöcke), Akzente, Lüftung, Anbauteile
  (Rohr, Kabel), Schilder mit wechselnder Kennung – und **starke Hingucker nur an manchen Teilen** (Kristalle
  `some`: etwa jedes zweite bis dritte). Vorbild: `test_wall_modules` (`cubegen/models/gameplay_tests.py`).
- **Einheitlicher Look bleibt Sache des Stils:** Leuchtfarbe, Material, Abnutzung über `--glow`, `--theme`,
  Anstriche – nicht über die Set-Variation.
- **Prüfen:** `--set --unique` (keine Doppelgänger), Reihenbild `set_<Typ>.png` ansehen; im Stiltest
  `tools/style_test.py --row <Typ>@…:5` (die Reihe gebacken und je Anstrich gerendert).
- **Unity:** Variantensets im Modell-Browser sind ToDo 25 der ROADMAP.

## 5. Anstriche (`--paint`)

- **Ein neutraler Back, Themen als Daten** (`cubegen/paint.py` `PAINTS`, Schlüssel `SCHEME_KEYS`): neue Themen sind
  neue Einträge, nie ein eigener Back-Pfad. `compose` ist die Referenzformel – auch für den späteren Unity-Shader
  (ROADMAP ToDo 27); Änderungen an der Formel dort mitdenken.
- **Unity-Vertrag:** Material heißt `MTA_<Modell>` (sonst lehnt der Import ab, belegt 0.17.0); erlaubte Karten in
  `textures.baked` stehen im Vertrag (`contract.json` › `baked_maps`, versioniert: `Emission` ab Version 2, nur bei
  Themen mit `edge_glow` > 0). Der Vertrag ändert sich nur mit neuer `version` und Rückweg (`contract_for`,
  `--contract`). Seit Version 3 (0.24.0) nennt der Sidecar die gepackten neutralen Karten (`MTN_`, `cubegen/neutral.py`)
  und das Thema (`paint`); die fertigen Karten entstehen aus genau diesen 8-Bit-Werten (ein Shader rechnet sie exakt
  nach, `tools/paint_reference.py`). Manifestfelder für Cube Escape
  (`format`, `sets`, `joins`, `dressings`) sind in `docs/UNITY_INTEGRATION.md` beschrieben – nur ergänzen, eine
  Bedeutung ändert sich nur mit neuem `format`.
- **Für alle Typen:** `M_Ground` ist je Thema ein neutraler Grundton (Böden!), Akzente der Modulwand nutzen
  `M_HazardOrange`; Staub, Moos, Schnee mit Rauschflecken, nie flächig. Ein Thema nie nur an Wänden abstimmen –
  Vergleich über mehrere Typen (`style_test.py --models floor_tile,platform,pillar,…`). Der Stiltest färbt
  Leuchtteile selbst um – Leuchtfarben deshalb immer auch in einem echten `--paint`-Lauf prüfen; Leuchtteile nie fest
  auf eine Farbe setzen, sondern `a.p.glow()`/`glow_or()` (folgt `--glow` und dem Thema).
- **Eigenes Thema** (`--paint-file`, `paint.load_scheme`): fehlende Werte kommen vom Grundthema, `check_scheme` prüft
  alles; der Name darf kein eingebautes Thema sein. Im Prozess per `register_scheme`, im Blender-Worker aus dem Auftrag
  (`job["paint_scheme"]`) – nie über eine globale Datei. `paint_names()` liefert nur die eingebauten.
- **Anbauten je Thema** (Parameter `dressing = none | ruin | organic`, `cubegen/models/dressing.py`; Modulwand,
  Boden, Säule, Steg): Geometrie, die ein Anstrich nicht liefern kann. Eigener Zufallsstrom (`a.sub("dressing")`),
  `quiet` (bei `none` nicht im Sidecar), nie gewürfelt, keine Kollision (klein, versperrt keinen Weg). Nichts darf
  unter den Boden reichen (`on_floor`), sonst verschiebt der Pivot das ganze Teil und der Set-Stoß bricht; Teile
  werden mit ihrer Reichweite eingegrenzt (`_inside`), nicht nur ihr Mittelpunkt.
- **`M_Crystal` nur für echten Kristall** (seit 0.24.0): Flüssigkeit, Hologramm/Energiefeld, Lampe, Blatt, leuchtende
  Organik, Sequenzfarbe, Leuchtakzent und Optik haben eigene Namen (`materials.CRYSTAL_SPLIT`, Test: nur
  `CRYSTAL_TYPES` nutzen `M_Crystal`). Ein neuer Typ wählt den passenden Namen; ein neues Material kommt ans Ende von
  `MATERIALS`, in den Vertrag (`materials`) und braucht einen Rückweg für ältere Vertragsversionen (`LEGACY_NAMES`).
- **Kristalle:** `crystal_color` je Thema (Manifest `paint`, Vorschau/Icon in der Farbe; Unity: ToDo 28);
  `crystal_cut = faceted` (Fels, Schwebeinsel, Hängekristalle, Modulwand) aus eigenem Zufallsstrom.
- **Prüfen:** `tools/style_test.py --paints all --concept <Konzeptbogen>` (Vergleich mit dem Konzept) und der echte
  Import in der Cube-Escape-Testkopie (`CubegenCliIntegrationTests` mit `CUBEGEN_TEST_EXPORTS`).

## 5a. Atlas, Zonen, Effektdaten (seit 0.30.0)

- **Atlas packen:** `bake._atlas_uvs` packt nach Smart UV Project mit `pack_islands(rotate, margin=0.008,
  shape_method=CONCAVE)` nach (0,008 ≈ die 4 px Bake-Rand bei 512 px; Smart UV Projects eigener Rand von 0,02 war
  breiter als nötig). Gemessen an 6 Typen (Blender 5.2.2, M-Klasse Mac): Belegung 0,50–0,72 → 0,67–0,79, bei einem
  Modell mit schon dichtem Atlas ±0 (0,720 → 0,717). `occupancy` = Summe der UV-Polygonflächen; im Manifest
  `models[].atlas_occupancy`, im Back-Cache neben den UVs gespeichert. Die Texturen gebackener Läufe ändern sich damit
  (Cache-Schlüssel enthält den Code, kalte Läufe einmalig); `CUBEGEN_ATLAS_PACK=off|convex|aabb` und
  `CUBEGEN_ATLAS_MARGIN` nur für Messungen (zusammen mit `CUBEGEN_CACHE=0`, der Schlüssel kennt sie nicht),
  `CUBEGEN_ATLAS_MEASURE=1` druckt vorher/nachher. Smart UV Project selbst schwankt zwischen Läufen (0,57 gegen 0,82
  bei gleichem Modell nach Seedwechsel), darum bleiben die UVs im Cache.
- **Lackzonen** (`zones.py`): Zone = Objektname ohne Ziffern- und Seiten-Endungen. Gemessen (Seed 42, 187 Typen): 108
  Typen haben nur eine bemalbare Zone (`Body`), 63 zwei, 12 drei, 3 mehr – eine Zweitfarbe an Teilgrenzen ist für 78
  Typen möglich, aber 135 von 154 Objektnamen sind `Body`; Teile innerhalb des Körpers sind nicht benannt (alle
  `part`). Eine Zonen-*Karte* braucht einen neuen Kanal im Vertrag (Version 4) und den Shader in Cube Escape – nicht
  Teil dieser Version.
- **Teilgraphen im Material:** gemessen und verworfen. `M_`-Materialien haben 2–5 Knoten, `MT_` 6; ein Knoten
  anlegen+entfernen kostet 0,012 ms, die Emissions-Ersatzgraphen des Backens (Kante) 0,2 ms je Material – ein Modell
  braucht dafür unter 10 ms gegen Sekunden Backzeit. Anders als im Roboter-Generator (große Material-Bäume) lohnt das
  Zusammenlegen nicht.
- **Effektmaterialien als Daten** (`effects.py`): Beschreibung je Material aus `KEEP_OWN` (Art, Verwendung, Werte aus
  `MATERIALS`), im Manifest je Modell; nichts erfunden, was das Spiel nicht hat (Fresnel, Alpha, Pulsieren leben in Cube
  Escape). Ein Test hält `KINDS`/`ROLES` und `KEEP_OWN` gleich.

## 5b. Formvarianten (`--shape voxel`, seit 0.30.0)

`shapes.voxelize` leitet nach dem Bau, vor der Z-Fighting-Korrektur, die Voxelform ab: geschlossene, konvexe Teile in
Objekten aus `DECORATIVE_PARTS` (kein ItemPickup), mindestens 3 Zellen dick; die Zelle ist die längste Seite / 24 (0,06
bis 0,2 m). Ein Würfel entsteht nur, wenn er ganz im Teil liegt (Zellmitte mindestens eine halbe Zelle innen, exakt für
konvexe Teile: Stützabstand des Würfels je Fläche) – nichts ragt heraus, die Collider der glatten Form bleiben gültig
(Test: Bounding-Box innen, gleiche Collider/Behaviours/Objektnamen, nicht mehr ungedeckte Teile, kein neues
Z-Fighting). Nur Flächen zur Luft bleiben, benachbarte Flächen einer Richtung/Schicht mit gleichem Material
werden zu Rechtecken verschmolzen (greedy); die Rolle je Richtung ist die der größten Originalfläche in dieser Richtung
(Oberseite behält ihre Rolle). Gemessen (187 Typen, Seed 42): 108 Teile in 66 Typen werden Voxel, Dreiecke gesamt 75 104 →
75 136 (Stufen kosten so viel wie Verschmelzen spart; ein Quader bleibt ein Quader). Die Atlas-UVs entstehen wie sonst
aus der Geometrie. Nicht umgesetzt: Facettenform (gibt es als `--detail low` und `crystal_cut`) und Lochform;
Voxel für gekrümmte, nicht konvexe oder dünne Teile bleibt glatt.

## 6. macOS-App (`app/`)

Gebaut wie der Robot Viewer des Roboter-Generators: SwiftUI + SceneKit, `swiftc` ohne Xcode-Projekt, universal,
ad-hoc signiert; Kommandozeilen-Modi statt UI-Automation für die Tests.

- **Eine Quelle:** Die App startet das mitgelieferte Paket (`python3 -m cubegen`) und liest Typen, Stiloptionen,
  Paletten und Familien aus `cubegen catalog` – keine eigenen Listen. Ihre Kommandozeile folgt `cubegen/gui.py`
  (`command`, `texture_args`); ändert sich dort etwas, ändert sich `GenerateSettings.arguments` mit, die Fixtures in
  `app/tests` und `app/test_app.sh` prüfen es.
- **Symbole per ImageMagick** (`app/make_icons.sh`), keine SF Symbols: weiße Linien auf Transparent als
  Vorlagenbilder, eins je Katalog-Kategorie (der Test verlangt das), `cube` als farbiger Platzhalter. Neue Kategorie
  oder Aktion → neues Symbol im selben Stil.
- **3D-Ansicht liest die MTL selbst** (`ModelScene.readMTL`): Blender schreibt `Ka 1 1 1`, ModelIO verändert die
  linearen Farben – beides ergab ein weißes Modell. Farben sind linear (wie Unity), die App rechnet nach sRGB um.
- **Gespeicherte Einstellungen** (`GenerateSettings`) lesen fehlende Schlüssel mit Standardwerten; Testmodi
  (`--run`, `--ui-snapshot`) lesen und schreiben sie nie.
- **Eigenes Thema mit Farbwählern** (`PaintEditor.swift`): Vorlagen und Schlüssel aus dem Katalog
  (`paint_schemes`, `paint_fields`), gespeichert als Datei für `--paint-file`; „Vorschau“ ist ein echter kleiner Lauf
  (vier Teile, 256 px). Testmodi `--paint-roundtrip`, `--paint-preview`, `--ui-snapshot --paint-editor`.
- **Prüfen:** `app/build.sh` und `app/test_app.sh` nach jeder Änderung an `app/` oder an CLI-Optionen, die die App
  anbietet; seit 0.30.0 geprüft (TECHNIK 5b): der Viewer liest nur `map_Kd` (Albedo, PNG24 ohne Alpha) per `NSImage`
  und hat keine Shader – Daten-Texturen (Normal, `MetallicSmoothness` mit Alpha als Datenkanal, `MTN_`) und
  Uniform-Grenzen treffen ihn nicht; kommt ein Shader oder eine Daten-Textur dazu: roh laden, Uniforms packen.
  Sichtprüfung über `--ui-snapshot` (Fenster offscreen; die SceneKit-Fläche bleibt dort leer) und
  `--snapshot` (3D-Ansicht).

## 7. Neural Engine und Unity-Check: ein schwerer Lauf zur Zeit

- **Neural Engine (nur macOS):** `tools/vision_report.py <Ausgabeordner>` – Apple Vision (`tools/vision_check.swift`,
  einmal kompiliert nach `output/tools`) meldet fast gleiche Varianten (Feature Prints) und Icons, die angeschnitten
  (Pixel am Rand), klein oder außermittig (Saliency) sind. Nur Hinweis: die Werte sind je Gerät verschieden und
  entscheiden nie über ausgegebene Varianten; nie im normalen Lauf.

- **Ein schwerer Lauf zur Zeit** (seit 0.25.0, Vertrag mit Cube Escape 0.59 „Turnstile“, `Tools/heavy_lock.py` dort):
  vor dem ersten Unity-Start wartet der Check auf die Sperre des ganzen Rechners – exklusives `flock` auf
  `~/Library/Caches/CubeEscape/heavy-run.lock` (fehlt die Datei, legt er sie an; nie löschen) – und hält sie bis zum
  letzten Prüfsatz (`HeavyLock` in `tools/unity_check.py`). Ein Wartender druckt den Halter (JSON-Zeile `{"pid",
  "what", "checkout", "since"}`, schreibt der Halter hinein) und meldet sich alle fünf Minuten. Der Deskriptor wird
  nie vererbt (`O_CLOEXEC`), Kinder bekommen `CE_HEAVY_HELD=1` (Cube Escapes Schritte darunter warten nicht auf
  ihren Elternprozess); `CE_HEAVY_LOCK=0` überspringt die Schlange. Jeder Unity-Schritt läuft seit 0.27.0 in einer
  eigenen Prozessgruppe (`run_in_group`): TERM/HUP/INT für den Check gehen an die ganze Gruppe, danach endet der Check
  (Exit 128 + Signal), und der Schritt ist erst vorbei, wenn die Gruppe leer ist – stirbt `verify.sh` vor Unity, bleibt
  die Sperre trotzdem bis zum Ende von Unity. Der Vertrag ändert sich nur gemeinsam mit Cube Escape, dem
  Roboter-Generator und Toolgen.

## 8. GitHub Actions in diesem Repo (seit 0.26.0)

Umsetzung in `.github/workflows/tests.yml`, **ein Job je Lauf**: ein Push auf `main` startet nur `quick` (Stufe
`quick`, Python 3.11, etwa 2 min – ein Release kommt erst nach der vollen lokalen Suite mit Blender und Unity auf
`main`), ein PR den Job `full` (ganze Suite mit Blender, `tools/run_tests.py --tier full`, Python 3.11, etwa 7 min);
„Run workflow“ wählt `quick`, `standard` (wie ein PR) oder `full` (dazu 3.9 und 3.13 mit Stufe `standard`, für
`test_golden`). Vorher (0.21.3 bis 0.25.0) kostete ein Push auf `main` vier Jobs, gemessen 17–19 abgerechnete Minuten.
`app/**` löst keinen Lauf aus (die App wird lokal geprüft). Job `quick` oder `full` nutzt die neueste Blender-LTS der
Reihe `BLENDER_SERIES` aus dem Actions-Cache, alle Gruppen laufen darin parallel. Hook `actions-sparsam` (Plugin `ce-shared`) warnt beim Bearbeiten eines Workflows.

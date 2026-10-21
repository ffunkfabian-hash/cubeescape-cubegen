# Cubegen – Entwicklerhintergrund

`AGENTS.md` hält die knappen Regeln; hier stehen die Begründungen, Messwerte und Einzelheiten dazu. Die Abschnitte
tragen dieselben Namen wie die Verweise in `AGENTS.md`. Die Bedienung der Kommandozeile steht in
[`CLI.md`](CLI.md). Techniken des Roboter-Generators, die Cubegen übernehmen kann (mit Stand und Aufwand):
[`TECHNIK.md`](TECHNIK.md). Teil 9 enthält den vollen früheren Wortlaut der `AGENTS.md`;
Entscheidungen des Nutzers: [`ENTSCHEIDUNGEN.md`](ENTSCHEIDUNGEN.md).

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
  `part`). Die Zonen-*Karte* (Vertrag Version 4): `stylebake.write_zone_map` rastert die Atlas-UVs der bemalten Objekte
  (`zones.zone_map`, numpy, hart 0/255, 4 px Rand), kein Cycles-Durchgang – exakt an den Zonengrenzen (ein gebackener
  Zonenkanal würde dort mischen) und bytegleich je UV-Satz; bis zu drei Slots (alphabetisch, `Body` ohne Slot), nur bei
  mindestens zwei Zonen. Der Shader mit der Zweitfarbe ist Cube Escapes.
- **Teilgraphen im Material:** gemessen und verworfen. `M_`-Materialien haben 2–5 Knoten, `MT_` 6; ein Knoten
  anlegen+entfernen kostet 0,012 ms, die Emissions-Ersatzgraphen des Backens (Kante) 0,2 ms je Material – ein Modell
  braucht dafür unter 10 ms gegen Sekunden Backzeit. Anders als im Roboter-Generator (große Material-Bäume) lohnt das
  Zusammenlegen nicht.
- **Effektmaterialien als Daten** (`effects.py`): Beschreibung je Material aus `KEEP_OWN` (Art, Verwendung, Werte aus
  `MATERIALS`), im Manifest je Modell; Basiswerte aus `MATERIALS`, `params` sind *vorgeschlagene* Laufzeit-Parameter
  je Art (`KIND_PARAMS`, `KIND_DEFAULTS`: Zahlen, Flags, 2-Vektoren – von Cubegen gewählt, Cube Escape setzt den Effekt um und
  darf sie ändern). Seit Vertrag 4 auch der Wurzelschlüssel `effects` im Sidecar. Ein Test hält `KINDS`/`ROLES`/`KIND_PARAMS`,
  den Abschnitt `effects` der Vertragsdatei und `KEEP_OWN` gleich.

## 5b. Formvarianten (`--shape voxel|facet|holes`, seit 0.30.0)

`shapes.voxelize` leitet nach dem Bau, vor der Z-Fighting-Korrektur, die Voxelform ab: geschlossene, konvexe Teile in
Objekten aus `DECORATIVE_PARTS` (kein ItemPickup), mindestens 3 Zellen dick; die Zelle ist die längste Seite / 24 (0,06
bis 0,2 m). Ein Würfel entsteht nur, wenn er ganz im Teil liegt (Zellmitte mindestens eine halbe Zelle innen, exakt für
konvexe Teile: Stützabstand des Würfels je Fläche) – nichts ragt heraus, die Collider der glatten Form bleiben gültig
(Test: Bounding-Box innen, gleiche Collider/Behaviours/Objektnamen, nicht mehr ungedeckte Teile, kein neues
Z-Fighting). Nur Flächen zur Luft bleiben, benachbarte Flächen einer Richtung/Schicht mit gleichem Material
werden zu Rechtecken verschmolzen (greedy); die Rolle je Richtung ist die der größten Originalfläche in dieser Richtung
(Oberseite behält ihre Rolle). Gemessen (187 Typen, Seed 42): 108 Teile in 66 Typen werden Voxel, Dreiecke gesamt 75 104 →
75 136 (Stufen kosten so viel wie Verschmelzen spart; ein Quader bleibt ein Quader). Die Atlas-UVs entstehen wie sonst
aus der Geometrie. **Facette** (`shapes.facet_part`): geschlossene konvexe Teile mit ≥ 12 Ecken, nicht flach (dünnste Seite ≥ 0,35 × mittlere:
Scheiben und Platten werden mit wenigen Ecken zu Splittern und bleiben): die konvexe Hülle (`_hull`, inkrementell) von jedem dritten
Eckpunkt (Farthest-Point-Auswahl, mindestens 8) – liegt wegen der Konvexität im Original; Rolle je Hüllfläche = die des
Originals mit der ähnlichsten Normale. Seed 42: 514 Teile in 114 Typen, 75 104 → 64 472 Dreiecke. **Löcher**
(`shapes.holes_part`): Platten (≤ 0,12 m dick, die anderen Seiten ≥ 4 × Dicke und ≥ 8 Löcher breit, beide Großflächen entlang
der Dickenachse) bekommen ein Gitter quadratischer Löcher (Zelle 0,06–0,15 m, Rand und jedes zweite Feld voll, eine Zellschicht
von 0,8 × Dicke, damit Fasen draußen bleiben); Löcher kosten Dreiecke (Seed 42: +45 %), deshalb nur solange das
Dreiecksbudget der Kategorie reicht, und nie bei Pivot `top` (Lauf-Flächen). Die Kollision bleibt die der glatten Form: ein
Collider-Quader über einer Platte füllt so kleine Löcher (nichts passt hindurch), das ist der einzige Unterschied zur Geometrie.
Meta-Schlüssel `derived_shape` (die Modelle nutzen `shape` selbst).
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

## 9. Regelwerk der AGENTS.md – Langfassung (ausgelagert in 0.30.1)

`AGENTS.md` hält seit 0.30.1 nur noch die Kurzfassung in der Standard-Gliederung (Projekt, Wahrheit und Aktualität, Befehle,
Regeln, Definition of Done). Der volle frühere Wortlaut jedes Abschnitts steht hier unverändert; bei Widerspruch gilt der
Code, dann dieser Text, dann die Kurzfassung wird angepasst.

### 9.1 Passende Kollision für jedes Modell


Jedes neue oder geänderte Modell braucht ein zur tatsächlichen Geometrie und Funktion
passendes Kollisionsrezept. Das gilt für Gameplay und statische Dekoration, intakte,
beschädigte und zerstörte Varianten, Parameterformen, LODs und bewegte Unterteile.
Ein erfolgreicher Export oder eine reine Prüfung der Bounds ist kein Physiknachweis.

- Feste Öffnungen und Zwischenräume bleiben frei. Eine Gesamtbox oder konvexe Hülle
  darf Käfige, Rohre, Tresore, Durchgänge oder Trümmerzwischenräume nicht auffüllen.
  Ein einfacher Box-/Hull-Collider ist nur für eine tatsächlich passende solide Form geeignet.
- Bewegte Teile und ihre Kinder tragen ihre Collider mit; Meshes unter bewegten
  Rigidbodies sind konvex. Feste komplexe Geometrie erhält genaue nichtkonvexe Meshes
  oder passend zerlegte einfache Shapes. Eine Schadenszone ersetzt keinen festen Collider.
- Rein visuelle Teile und Pickups werden ausdrücklich passend behandelt; Pickups
  behalten ihre Interaktionstrigger. Sichtbarkeit allein verlangt keine feste Kollision.
- Eigene vorhandene Shapes vor Änderungen prüfen. Generation 3 ergänzt fehlende
  Gameplay-/statische Shapes; ältere Generationen sind historische Ausgabe. Erhaltene
  alte Ausgabe niemals als korrigiert deklarieren. Alte fehlerhafte Exporte müssen
  mit dem aktuellen Rezept neu erzeugt und in Unity erneut geprüft werden.
- Dünne feste Teile (z. B. Stegstützen) zusätzlich durch tatsächliche Innenpunkte und
  exportierte Unity-Physik prüfen; Mindestvolumen-/Dickenfilter allein sind kein vollständiger Nachweis.
- Fehlende Kollisionsdeckung und blockierte Freiräume sind Fehler. Qualitätsprüfung
  muss den tatsächlichen Unity-Import abbilden, keine ersatzweise angenommene Hülle.
- Regressionen für Modelle, Seeds, Parameter und Zustände ergänzen. Bestehende Tests
  nicht löschen oder Importprüfungen lockern. Bei bewusster Änderung Golden-Daten
  gezielt aktualisieren und unveränderte Geometrie separat belegen.
- Python-Suite und echte FBX in der isolierten Cube-Escape-Testkopie prüfen:
  Geometrie-/Shape-Zuordnung, freie Öffnungen, bewegte Collider, Reimport und passende
  Laufzeit-/Physiktests. Kein Unity-Start auf einem Checkout.

Belegte Generatorfehler (Kollision, Geometrie, Export, Sidecar-/Metadaten) sofort beheben. Neue Befunde
gehören in den Versionsbericht der laufenden Arbeitsversion `docs/versions/<Hauptversion>.md` (siehe „Versionen,
Branches und Worktrees“): Fund, Ursache, Korrektur, geprüfte Varianten und verbleibende Grenzen. Veröffentlichte
Berichte bleiben historisch. Diese Regel gilt auch in allen späteren Integrationsphasen.

### 9.2 Ganze Leistung des Geräts (gemeinsame Regel mit Cube Escape und dem Roboter-Generator)


Braucht eine Sitzung den Rechner für sich (Messungen, Benchmarks, Zeitbudgets, Abnahmen), darf sie andere
Sitzungen pausieren. Werkzeug: `pause_sessions.py` aus Cube Escape
(`/Users/ffunk/Claude/Cube Escape/.agents/skills/ce-testing/scripts/pause_sessions.py run -- <Befehl>`): hält nur die
Befehle anderer Claude-/Codex-Sitzungen an (SIGSTOP), setzt sie danach immer fort (SIGCONT), lässt die Sitzungen selbst,
den Unity-Editor und Blender des Nutzers unberührt. Nur so lange wie nötig pausieren und es im Bericht nennen. Ein
pausierter Befehl kann in die Zeitgrenze seines Werkzeugs laufen – dann führt die andere Sitzung ihn erneut aus.

### 9.3 GitHub Actions sparsam (globale Regel)


Die Regel steht global im Repo `~/Claude/cubeescape-rules` (`~/.claude/CLAUDE.md` und `~/.codex/AGENTS.md` sind Links darauf) und gilt für alle Repos des Kontos:
2.000 min im Monat, Budget 0 $ – leer heißt, kein Workflow läuft mehr bis zum Monatsanfang. Kurz: `push` nur auf
`main`, sonst über den PR; `concurrency` mit `cancel-in-progress`; `paths-ignore` für Doku; wenige volle Jobs; große
Matrix nur auf Wunsch; `timeout-minutes`; lokal zuerst testen. Hier **ein Job je Lauf** (`.github/workflows/tests.yml`):
Push auf `main` = `quick`, PR = `full`, „Run workflow“ = `quick`/`standard`/`full`; `app/**` löst nichts aus (DEVELOPER.md 8).

### 9.4 Versionen, Branches und Worktrees


Jeder neue Branch, Worktree oder Arbeitsauftrag ist eine **neue Version**: Minor +1 (0.12.0 → 0.13.0 → 0.14.0 …)
mit einem eigenen, ausgedachten Namen – cool und auf Englisch (z. B. „Overdrive“, „Afterburner“), nie ein
beschreibender deutscher Begriff; gilt ab 0.16.0, ältere Namen bleiben. Setzt eine Sitzung dieselbe Arbeit in
einem Folge-Worktree fort, behält sie deren Version. Gleich zu Beginn, nicht erst beim Release:

- Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` (`bl_info`)
  gemeinsam anheben – `tests/test_versions.py` prüft die Gleichheit samt gebautem Add-on-ZIP.
- Branch `release/<Version>`, Bericht `docs/versions/<Haupt>.md` (`<Haupt>` = die ersten zwei Zahlen, 0.30.0 → `0.30`) mit
  Titel „# Cubegen <Haupt> – <Name>“ und Abschnitt „## Cubegen <Version> – <Name>“, Changelog-Eintrag
  „## <Version> „<Name>“ – unveröffentlicht“ (3–5 Zeilen und Link auf den Abschnitt).
- Release (nur auf Wunsch des Nutzers): Datum statt „unveröffentlicht“, Tests grün, dann `python3 tools/release.py`
  im Release-Worktree (Probelauf, ändert nichts; Prüfliste im Kopf der Datei); `--apply --trailer "Co-Authored-By: …"`
  merged im Haupt-Checkout (`git merge --no-ff`, „Cubegen <Version> – Release übernehmen“), taggt `v<Version>` und
  pusht `git push --atomic origin main release/<Version> v<Version>` – nie `--force`. `main` ist der Standard-Branch auf
  GitHub (ffunkfabian-hash/cubeescape-cubegen).

Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt nach derselben Regel.

### 9.5 Versionsberichte (Standard aller Projekte, seit 0.30)


Ein Bericht je **Hauptversion** (die ersten zwei Zahlen: 0.30) unter `docs/versions/<Haupt>.md`; ein Patch (0.30.1) **ergänzt**
den Bericht seiner Hauptversion als Abschnitt `## Cubegen 0.30.1 – <Name>`, nur eine neue Hauptversion legt eine Datei an.
Die letzten drei Hauptversionen liegen in `docs/versions/`, ältere in `docs/archive/versions/` (Agenten laden das Archiv
nicht von selbst, lesen es nur bei Bedarf). **Hauptordner schlank:** nur `README.md`, `AGENTS.md`, `CLAUDE.md`,
`CHANGELOG.md` und Konfiguration – keine `VERSION_*.md`, keine Notiz- oder Zwischenstandsdateien (Ideen: `docs/IDEEN.md`).
`CHANGELOG.md` hat je Version 3–5 Zeilen und einen Link auf den Abschnitt des Berichts. Beim Anlegen einer neuen Hauptversion
wandert der Bericht der viertletzten ins Archiv (`git mv`, Links in CHANGELOG/Docs mit anpassen); `tools/release.py`
prüft den Abschnitt der Version.

### 9.6 Abschluss in zwei Stufen


Sitzungen ohne Blender und Unity (z. B. in der Cloud, claude.ai/code) dürfen meist nur ihren eigenen Branch pushen –
keine Tags, kein `main`, keine Release-Branches – und können keinen Unity-Import prüfen. Cloud-Sitzungen richtet der
SessionStart-Hook `.claude/hooks/session-start.sh` ein (ImageMagick 6, Blender als `bpy`-Modul hinter dem Befehl
`blender`; damit laufen `--tier full` und echte Exporte auf der CPU). Kein Ersatz für Stufe 2: Blender-App mit GPU,
Blender-Plugin, `unity_check.py` und die macOS-App gibt es nur lokal.

- **Stufe 1 „ungeprüft“** (ohne Blender/Unity): `python3 -m unittest discover -s tests` (Blender-/ImageMagick-Tests
  werden ohne die Werkzeuge übersprungen – das im Bericht nennen), bei Bedarf `--no-blender`-Erzeugung; Branch pushen,
  PR mit Abschnitt „Vor dem Merge noch offen“; der Abschnitt der Version im Versionsbericht trägt oben
  *„ungeprüft: Blender-/Unity-Abnahme offen“*. Danach darf der Nutzer den PR auf GitHub mergen; kein Tag, kein Release.
- Stufe 1 reicht als Abschluss **nur für Doku oder Werkzeuge ohne Einfluss auf die Ausgabe**. Bei Generator-Code,
  Geometrie, Kollision, Materialien/Texturen, Sidecar/Vertrag oder Add-on ist sie ein Vorab-Stand: Der Bericht endet
  **immer** mit dem ausgefüllten Prompt für den lokalen Test (Vorlage unten) als kopierbarem Codeblock.
- **Stufe 2 „abgenommen“** (lokal): volle Python-Suite **mit** Blender und ImageMagick (keine übersprungenen Tests:
  `CUBEGEN_UNITY_CHECK=1 CUBEGEN_SLOW_TESTS=1 python3 tools/run_tests.py --tier full`; die numpy-Module laufen mit
  einem Python, das numpy hat – `run_tests.py` nimmt selbst Blenders Python und nennt die Interpreter),
  echte Exporte der geänderten Typen, Sichtprüfung (Kontaktbogen, Blender-Plugin), **`python3 tools/unity_check.py
  --require`** (feste Prüfsätze durch den echten Import von Cube Escape, Ergebniszeile in den Versionsbericht), bei
  neuen Typen oder Gameplay zusätzlich die geänderten Typen und die Physik in der Cube-Escape-Testkopie (Skill
  `ce-cubegen` dort), Vermerk „ungeprüft“ entfernen; danach Release wie oben.
  Bleibt etwas rot oder ist eine Richtungsfrage offen: anhalten und fragen, nicht releasen.

Vorlage – wörtlich übernehmen, `<…>` durch echte Werte ersetzen („Umfang: nur Abnahme“ für eine Prüfung ohne Release):

```text
Abnahme und Release nach Cubegen-AGENTS.md (Stufe 2):
Branch: <branch> · Version: <0.x.0 „Name“> · PR: <PR-Link>
Tag: <v0.x.0> · Release-Branch: <release/0.x.0> · Umfang: Abnahme und Release (oder: nur Abnahme)
Vor dem Merge noch offen:
- <offener Punkt aus dem PR, z. B. Exporte von …, Unity-Import in der Testkopie, Kontaktbogen ansehen>
Abnahme: eigener Worktree; volle Python-Suite mit Blender und ImageMagick ohne übersprungene Tests, echte Exporte der
geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Versionsbericht (`docs/versions/<Haupt>.md`) auf
Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```

### 9.7 Leistung und Grenzen (seit 0.21.0; Begründung DEVELOPER.md 1)


- **Ein Renderer, wo es geht:** `--single-renderer` fasst die Mesh-Objekte statischer Modelle zusammen, deren Teile nur
  Optik tragen (`asset.DECORATIVE_PARTS`). Neue Typen: Schmuckteile mit Namen aus der Liste benennen, Teile mit
  Bedeutung (Panel, Tile_<n>, Fluid, Rotor …) nicht.
- **Grenzen in Bytes, wo Dateien oder Speicher gemeint sind:** nie die Länge eines Strings mit einer Byte-Grenze
  vergleichen. Budget der Werkbank: `contract.RUNTIME_BUDGET` (aus Cube Escape abgeschrieben, beim Ändern dort
  nachsehen); `check_runtime_budget` prüft jedes GLB. Größe/Änderungszeit statt jede Datei lesen (`OutputCache`).
- **Erst Schritte benennen, dann optimieren:** neue Arbeit bekommt einen Schritt in `timings.steps` (Manifest);
  Vergleiche mit `tools/perf_band.py --save <vorher>` / `--compare` (Bänder mit Lasterkennung, CPU-Zeit zählt immer);
  Einzelläufe auf einem belebten Rechner sind keine Messung.
- **Verzeichnisse statt Suchen:** in Schleifen nie linear suchen (`x in liste`, `next(… if o.name == …)`, `asset.get`
  je Element) – vorher Dictionary oder Set bauen. Jedes Modell wird je Lauf genau einmal gebaut (`asset_of`/`lod_of`).

### 9.8 Abwechslung: Details aus eigenem Zufallsstrom


`cubegen check` zeigt je Typ, wie viele von 10 Varianten unterscheidbar sind (`variety.signature`: Objekte,
Materialien, Dreiecke, Hüllquader – Änderungen innen sieht es nicht). Zu wenig Abwechslung → kleine Details aus
`cubegen/models/details.py` (Schraubenkranz, Kennschild mit Code, Kabelkanal, Warnwinkel, Stromkasten, Käfig,
Kabeltrasse …), je Variante ein bis zwei aus `a.sub("variety")` – nie aus dem `rng` des Builders. Details bleiben
klein, statisch, weg von beweglichen Teilen und Spielpunkten (Strahlhöhe, Linse) und innerhalb von `set_faces`; ein
`Glow`-Teil behält ein Material. Die Signatur selbst nicht ändern: `--unique` würde andere Varianten wählen.

### 9.9 Werkzeuge: ImageMagick und Blender-Plugin


- **ImageMagick** (`magick`, Version 7; `python3 -m cubegen doctor` zeigt, ob es gefunden wird) erzeugt die Texturen
  (`--textures tiled|baked|palette`) und ist ausdrücklich auch zum **Gestalten** erwünscht: Symbole, Schilder,
  Leucht-Masken, Paletten, Kontaktbögen; zum Prüfen von Vorschauen zuschneiden, vergrößern, `montage`,
  `compare -metric AE`. Bilder reproduzierbar erzeugen (feste Seeds, `-define png:exclude-chunks=date,time`; alles
  über `ImageMagick.run`, das danach `strip_png_dates` anwendet – ImageMagick 6 ignoriert den Define). Linux/CI hat
  oft ImageMagick 6: kein `magick`, sondern `convert`/`compare`/`montage` – nie `magick` fest aufrufen.
- **Texturen sind erlaubt** (seit Cube Escape 0.35): Standard bleibt `none` (einfarbige `M_…`-Materialien); die Option
  gibt es in CLI, Blender-Add-on, Desktop-Fenster und in der Cube-Escape-Werkbank. Glow-/Status-, Glas- und
  Kristallmaterialien bleiben untexturiert (`docs/UNITY_INTEGRATION.md`).
- **Blender-Plugin** (MCP, `mcp__Blender__*`): steuert das **laufende** Blender des Nutzers (Port 9876). Ausdrücklich erwünscht
  (Nutzer, 19./20.10.2026; globale Regel `~/.claude/CLAUDE.md` › Blender-MCP): ohne Nachfrage nutzen, wenn Blender läuft – es ist der
  schnellste Weg zu belastbaren Befunden. Exporte laden und nachmessen (Maße, Pivot, Vorderseite, Teil-/Materialnamen, Öffnungen für die
  Kollision), UV und Material prüfen, Probe-Bakes, Texturen ansehen, Ansichten rendern. Immer in einer eigenen Szene, nie im geöffneten
  Nutzerprojekt; die Quelle bleibt der Generator (Befunde werden im Generator behoben). Eigene Szenen nur über `wm.save_as_mainfile`
  speichern (`bpy.data.libraries.write` mit neuer Szene ließ Blender 5.2.2 abstürzen); schwere Bakes über `heavy_lock`. Ohne laufendes
  Blender (Cloud, Batch) gilt nur der Batch-Export.
- **Neural Engine (nur macOS):** `tools/vision_report.py <Ausgabeordner>` ist nur ein Hinweis, entscheidet nie über
  ausgegebene Varianten und läuft nie im normalen Lauf (DEVELOPER.md 7).
- **Unity-Check** (`tools/unity_check.py`, nur lokal mit Cube Escape und Unity): feste Prüfsätze (Bau-Kit-Sets,
  Zusatzdetails, Gameplay, Anstrich mit Anbauten und Kristallen, eigenes Thema, Kacheln, Schäden, alle Typen als GLB)
  laufen über Cube Escapes `verify.sh` in der Testkopie, nie auf einem Checkout: Editor-Import
  (`CubegenCliIntegrationTests`) und Laufzeitpfad der Werkbank (`CubegenRealGenerationTests`). Etwa 3 min; `--quick`
  nur Bau-Kit und Anstrich. Prüfsätze nur bewusst ändern (Ergebnisse bleiben vergleichbar); ein neues Merkmal bekommt
  seinen Prüfsatz. Ohne Cube-Escape-Checkout „übersprungen“ (`--require`: Fehler). **Ein schwerer Lauf zur Zeit:** vor
  Unity wartet der Check auf `~/Library/Caches/CubeEscape/heavy-run.lock` (nie löschen; `CE_HEAVY_LOCK=0` überspringt;
  Vertrag nur gemeinsam mit Cube Escape ändern, DEVELOPER.md 7).

### 9.10 Plugins und Hooks (Claude Code)


`CLAUDE.md` importiert diese Datei. Nur Claude Code hat die Plugins; andere Agenten befolgen dieselben Regeln aus dem
Text. Gemeinsam mit Cube Escape und dem Roboter-Generator (dort je eine eigene Tabelle in `AGENTS.md`).

| Plugin | Einsatz in Cubegen |
|---|---|
| `quick-gate-python` | Ruff, Pyright, pytest als schnelle Prüfung; verbindlich bleibt `python3 -m unittest discover -s tests` |
| `code-review` | Slash-Befehl `code-review` vor jedem Release-Merge in `main` |
| `github` | Pull Requests, Issues, Release-Branches und Tags auf GitHub (oder `gh`); Release-Ablauf oben |
| `engineering` | `debug`, `testing-strategy`, `documentation` |
| `design` | `ux-copy`, `accessibility-review` für Desktop-Fenster und Blender-Add-on |
| `unity` | `physics-3d-collision` beim Prüfen der Kollision in der Cube-Escape-Testkopie (`ce-cubegen` dort) |
| `hookify` | Repo-eigene Regeln als `.claude/hookify.<name>.local.md` (eingecheckt mit `git add -f`, da `.claude/` lokal ausgeschlossen ist) |
| `ce-shared` | eigenes Plugin für Cube Escape, Cubegen und den Roboter-Generator (privates GitHub-Repo ffunkfabian-hash/ce-agent-tools, eingetragen in `.claude/settings.json`): gemeinsame Regeln und die Werkzeug-Profile der Subagents (`.claude/agent-guard.json`) |
| Blender-MCP | siehe „Werkzeuge: ImageMagick und Blender-Plugin“ |

**Hooks blockieren** (Plugin `ce-shared`) Unity und die Unity-CLI auf einem Cube-Escape-Checkout oder ohne
`--project-path`, nacktes `git stash` (geteilter Stash-Stapel), Force-Push und Teleportieren einer Cloud-Sitzung,
(hookify) Änderungen von Hand an `output/`; sie **halten das Sitzungsende an**, bis nach einer Python-Änderung die
Suite lief, und **warnen** bei Commit/Merge/Tag/Push (nur auf Wunsch), Golden-Daten, Versionsdateien und Workflows.
Ändert sich eine dieser Regeln, ändert sich ihre Hook-Datei mit (gemeinsame im Plugin-Repo, mit Tests).
**Subagents** (`.claude/agents/`): `cg-test-runner` (Tests nach Stufe, berichtet nur) und `cg-doc-keeper` (Doku auf
Endstand, nur Markdown) – Befehle und Schreibpfade begrenzt `.claude/agent-guard.json`.

### 9.11 Blender-Batch schnell halten (Regeln; Messungen und Begründung DEVELOPER.md 2)


Gilt für jeden Blender-Batch-Lauf dieses Repos. Messen statt raten (`cProfile` per Wrapper um `main()`, macOS
`sample <pid> 5`, GPU-Last über `ioreg -r -c IOAccelerator`), Zeiten nur auf ruhiger Maschine vergleichen und die
Systemlast mitprotokollieren.

- **Cycles:** eine zusammengefügte Kopie aller Teile backen (`cubegen/bake.py`), nicht jedes Objekt einzeln; GPU erst ab
  1024 px (`--bake-device auto`); Lineares nicht mehrfach backen (Gewichtskarten); `-t` nicht für Cycles-Backen.
- **Determinismus:** UV-Packen und Flächenreihenfolge sind nicht deterministisch – Cache-Schlüssel über eine kanonische
  Ecken-Reihenfolge, UVs cachen. Bytegleiche Bilder sind Voraussetzung für jeden Cache (`imagemagick.REPRODUCIBLE`);
  neue Bildschritte nutzen `cubegen/cache.py`, ein Test erzeugt zweimal und vergleicht die Bytes.
- **EEVEE:** nie ein Material mit `surface_render_method = "BLENDED"` in Vorschauen (verdoppelt die Renderzeit); deckend
  oder `DITHERED`, Samples senken, Raytracing aus.
- **Parallel:** `--jobs auto` (`pipeline.auto_jobs`); neue Arbeit bekommt ihre Schätzung in `SECONDS_PER_MODEL` aus einer
  Messung, eine neue Stufe ein Budget in `STAGE_BUDGETS`. ImageMagick parallel nur mit `MAGICK_THREAD_LIMIT=1`
  (`ImageMagick.single_threaded`); große Kontaktbögen in Blöcken zu `SHEET_ROWS` montieren.
- **Prüfung und Modellbau bleiben reines Python** (`fix_z_fighting`, `quality.ray_faces`; Ergebnis bytegleich prüfen);
  numpy-Kleinkram: `foreach_get("co", …)` in `float32`. Die Neural Engine nutzt Blender nicht.
- Nach Code-Änderungen `python3 tools/run_tests.py --tier quick` (rund 30 s), vor dem Release die volle Suite.

### 9.12 Gemeinsamer Cache (seit 0.25.0; Aufbau und Begründung DEVELOPER.md 3)


Ein inhaltsadressierter Cache für Haupt-Checkout, Worktrees, App und `unity_check.py`: `~/Library/Caches/Cubegen/cache`
(Linux `$XDG_CACHE_HOME/cubegen/cache`); `CUBEGEN_CACHE=<Ordner>` verlegt ihn, `CUBEGEN_CACHE=0` schaltet ihn ab,
`python3 -m cubegen cache` zeigt Ort und Größe (`--prune`, `--migrate DIR`).

- **Schlüssel nur aus Eingaben, nie aus Pfaden:** kein absoluter Pfad in Schlüssel oder Einträgen. Neue Bildschritte:
  ImageMagick-Argumente aus `pipeline.py` gehören in den Schlüssel; neue Worker-Ausgaben in `modelcache.result_files`,
  neue Worker-Eingaben in den Auftrag (dann automatisch im Schlüssel).
- **Atomar schreiben** (Temp-Datei, dann umbenennen), Inhalte vor dem Eintrag; ein Cache-Fehler bricht nie einen Lauf ab.
- Alte Caches nur über `migrate.MIGRATABLE` übernehmen; ändert sich der Bildcode, Eintrag dort und im Test entfernen.
- **Tests** laufen mit einem eigenen, frischen Cache je `run_tests.py`-Lauf (nie mit dem des Rechners).

### 9.13 Aufträge an andere Sitzungen


Ein Auftrag an eine andere Sitzung (Cube Escape, Roboter-Generator, eine zweite Cubegen-Sitzung) enthält nur die Aufgabe
und diese Punkte – kurz, als Liste:

```text
Art der Änderung: <Generator / Ausgabe / Werkzeug / Test / Doku> – was sich NICHT ändern darf
Prüfweg: <Tests (Stufe), echte Läufe, Unity-Check, Vergleich gegen Version X>
Erwartete Unterschiede: <keine (bytegleich) / welche Dateien, welche Felder>
Release: <ja: Version, Merge, Tag, Push / nein: nur Branch>
Bericht: Version/Name, Commits/Tag, Messwerte (vorher/nachher, Last), Testzahlen (übersprungen mit Grund), Offenes
```

### 9.14 Variantensets (Variation ohne Wiederholung; Einzelheiten DEVELOPER.md 4)


Teile, die im Level nebeneinander stehen, dürfen nicht gleich aussehen: ein Set sind Varianten mit **gleichem Umriss**
und **anderem Innenleben** (`--set`, Manifest `sets`).

- **Umriss nur über Parameter** (`Param(size=True)` oder ein Name aus `OUTLINE_PARAMS`), nie ein im Builder gewürfelter
  Wert, keine Zufallsskalierung; `set_faces` am Typ (`@model(..., set_faces=...)`), `set_pins` für Formwahlen,
  `outline_ok = false` = nicht set-fähig.
- **Anschlüsse durchlaufen lassen** (Sockel, Deckel, Kern an der vollen Länge; Muster mit einer Periode, die die Länge
  teilt). **Innen variieren** über `rng` (reproduzierbar je Seed); starke Hingucker nur an manchen Teilen. Der
  einheitliche Look bleibt Sache des Stils (`--glow`, `--theme`, Anstriche).
- **Prüfen:** `--set --unique`, Reihenbild `set_<Typ>.png`; Stiltest `tools/style_test.py --row <Typ>@…:5`.

### 9.15 Anstriche (`--paint`; Einzelheiten DEVELOPER.md 5)


- **Ein neutraler Back, Themen als Daten** (`cubegen/paint.py` `PAINTS`, `SCHEME_KEYS`): neue Themen sind neue Einträge,
  nie ein eigener Back-Pfad. `compose` ist die Referenzformel (auch für den späteren Unity-Shader, ROADMAP ToDo 27).
- **Unity-Vertrag:** Material heißt `MTA_<Modell>`; erlaubte Karten stehen im versionierten Vertrag
  (`contract.json` › `baked_maps`, Rückweg `contract_for`/`--contract`); der Vertrag ändert sich nur mit neuer `version`.
  Manifestfelder (`format`, `sets`, `joins`, `dressings`): `docs/UNITY_INTEGRATION.md` – nur ergänzen, eine Bedeutung
  ändert sich nur mit neuem `format`.
- **Für alle Typen prüfen**, ein Thema nie nur an Wänden abstimmen (`style_test.py --models …`); Leuchtteile nie fest auf
  eine Farbe, sondern `a.p.glow()`/`glow_or()`; Leuchtfarben auch in einem echten `--paint`-Lauf prüfen.
- **Eigenes Thema** (`--paint-file`, `paint.load_scheme`) nie über eine globale Datei; **Anbauten** (`dressing`, eigener
  Zufallsstrom, keine Kollision, nichts unter den Boden) und **`M_Crystal` nur für echten Kristall** (neues Material ans
  Ende von `MATERIALS`, in den Vertrag, Rückweg in `LEGACY_NAMES`): Einzelheiten DEVELOPER.md 5.
- **Prüfen:** `tools/style_test.py --paints all --concept <Konzeptbogen>` und der echte Import in der
  Cube-Escape-Testkopie (`CubegenCliIntegrationTests` mit `CUBEGEN_TEST_EXPORTS`).

### 9.16 macOS-App (`app/`; Einzelheiten DEVELOPER.md 6)


SwiftUI + SceneKit, `swiftc` ohne Xcode-Projekt. **Eine Quelle:** die App startet das mitgelieferte Paket und liest alles
aus `cubegen catalog`, keine eigenen Listen; ihre Kommandozeile folgt `cubegen/gui.py` (ändert sich dort etwas, ändert
sich `GenerateSettings.arguments` mit). Neue Kategorie oder Aktion → neues Symbol (`app/make_icons.sh`). Gespeicherte
Einstellungen lesen fehlende Schlüssel mit Standardwerten. **Prüfen:** `app/build.sh` und `app/test_app.sh` nach jeder Änderung an `app/` oder an
CLI-Optionen, die die App anbietet.

### 9.17 Ausrichtung gerichteter Modelle


Bei Kameras und anderen gerichteten Modellen die tatsächliche Funktionsfläche prüfen,
nicht nur die Objektrotation: Blender-/Unity-Achsen, Neigung und beide Schwenkvorzeichen
gegen die exportierte Geometrie testen. Ein Anker- oder Bounds-Test ersetzt keinen
Nachweis der Blickrichtung. Beabsichtigte Korrekturen gegenüber alten Generationen
ausdrücklich dokumentieren und historische Ausgaben getrennt prüfen.

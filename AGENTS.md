# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

## Passende Kollision für jedes Modell

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
gehören in den Versionsbericht der laufenden Arbeitsversion `VERSION_<Version>.md` (siehe „Versionen,
Branches und Worktrees“). 0.11.0 übernimmt das frühere 0.10.6-Vorhaben und besitzt den Bericht
`VERSION_0.11.0.md`. 0.12.0 (10. Oktober 2026) veröffentlicht die Arbeitsstände 0.11.1–0.11.4
(`VERSION_0.11.2.md` bis `VERSION_0.11.4.md`, Release-Bericht `VERSION_0.12.0.md`). 0.13.0 „Patina“ (10. Oktober 2026,
`VERSION_0.13.0.md`) ist veröffentlicht. 0.14.0 „Werkstattbuch“ (12. Oktober 2026, `VERSION_0.14.0.md`, Leistungserfahrungen
für Blender-Batch-Läufe) ist veröffentlicht, ebenso 0.14.1 (12. Oktober 2026, `VERSION_0.14.1.md`, Plugins und Hooks für
Claude Code). 0.14.2 (12. Oktober 2026, `VERSION_0.14.2.md`, Neural Engine geprüft) ist veröffentlicht. Laufende Arbeitsversion: 0.15.0 „Stoppuhr“ (`VERSION_0.15.0.md`).
Veröffentlichte Berichte bleiben historisch.
Fund, Ursache, Korrektur, geprüfte Varianten und verbleibende Grenzen festhalten.
Diese Regel gilt auch in allen späteren Integrationsphasen.

## Versionen, Branches und Worktrees

Jeder neue Branch, Worktree oder Arbeitsauftrag ist eine **neue Version**: Minor +1 (0.12.0 → 0.13.0 → 0.14.0 …)
mit einem eigenen, ausgedachten Namen (kurz, sprechend, z. B. „Eisenwald“). Setzt eine Sitzung dieselbe Arbeit in
einem Folge-Worktree fort, behält sie deren Version. Gleich zu Beginn, nicht erst beim Release:

- Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` (`bl_info`)
  gemeinsam anheben – `tests/test_versions.py` prüft die Gleichheit samt gebautem Add-on-ZIP.
- Branch `release/<Version>`, Bericht `VERSION_<Version>.md` mit Titel „Cubegen <Version> – <Name>“ und
  Changelog-Eintrag „## <Version> „<Name>“ – unveröffentlicht“.
- Release (nur auf Wunsch des Nutzers): Datum statt „unveröffentlicht“, Tests grün, `git merge --no-ff` in `main`
  („Cubegen <Version> – Release übernehmen“), Tag `v<Version>`, Push von `main`, `release/<Version>` und Tag.
  `main` ist der Standard-Branch auf GitHub (ffunkfabian-hash/lowpoly_cubeescape_model_generatior).

Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt nach derselben Regel.

## Abschluss in zwei Stufen

Sitzungen ohne Blender und Unity (z. B. in der Cloud, claude.ai/code) dürfen meist nur ihren eigenen Branch pushen –
keine Tags, kein `main`, keine Release-Branches – und können keine echten Exporte und keinen Unity-Import prüfen.

- **Stufe 1 „ungeprüft“** (ohne Blender/Unity): `python3 -m unittest discover -s tests` (Blender-/ImageMagick-Tests
  werden ohne die Werkzeuge übersprungen – das im Bericht nennen), bei Bedarf `--no-blender`-Erzeugung; Branch pushen,
  PR mit Abschnitt „Vor dem Merge noch offen“; der Versionsbericht `VERSION_<Version>.md` trägt oben
  *„ungeprüft: Blender-/Unity-Abnahme offen“*. Danach darf der Nutzer den PR auf GitHub mergen; kein Tag, kein Release.
- Stufe 1 reicht als Abschluss **nur für Doku oder Werkzeuge ohne Einfluss auf die Ausgabe**. Bei Generator-Code,
  Geometrie, Kollision, Materialien/Texturen, Sidecar/Vertrag oder Add-on ist sie ein Vorab-Stand: Der Bericht endet
  **immer** mit dem ausgefüllten Prompt für den lokalen Test (Vorlage unten) als kopierbarem Codeblock.
- **Stufe 2 „abgenommen“** (lokal): volle Python-Suite **mit** Blender und ImageMagick (keine übersprungenen Tests),
  echte Exporte der geänderten Typen, Sichtprüfung (Kontaktbogen, Blender-Plugin), Import und Physik in der
  Cube-Escape-Testkopie (Skill `ce-cubegen` dort), Vermerk „ungeprüft“ entfernen; danach Release wie oben.
  Bleibt etwas rot oder ist eine Richtungsfrage offen: anhalten und fragen, nicht releasen.

Vorlage – wörtlich übernehmen, `<…>` durch echte Werte ersetzen („Umfang: nur Abnahme“ für eine Prüfung ohne Release):

```text
Abnahme und Release nach Cubegen-AGENTS.md (Stufe 2):
Branch: <branch> · Version: <0.x.0 „Name“> · PR: <PR-Link>
Tag: <v0.x.0> · Release-Branch: <release/0.x.0> · Umfang: Abnahme und Release (oder: nur Abnahme)
Vor dem Merge noch offen:
- <offener Punkt aus dem PR, z. B. Exporte von …, Unity-Import in der Testkopie, Kontaktbogen ansehen>
Abnahme: eigener Worktree; volle Python-Suite mit Blender und ImageMagick ohne übersprungene Tests, echte Exporte der
geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Bericht VERSION_<Version>.md auf
Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```

## Werkzeuge: ImageMagick und Blender-Plugin

- **ImageMagick** (`magick`, Version 7; `python3 -m cubegen doctor` zeigt, ob es gefunden wird) erzeugt die Texturen
  (`--textures tiled|baked|palette`) und ist ausdrücklich auch zum **Gestalten** erwünscht: Symbole, Schilder,
  Leucht-Masken, Paletten, Kontaktbögen; zum Prüfen von Vorschauen zuschneiden, vergrößern, `montage`,
  `compare -metric AE`. Bilder reproduzierbar erzeugen (feste Seeds, `-define png:exclude-chunks=date,time`).
- **Texturen sind erlaubt** (seit Cube Escape 0.35): Standard bleibt `none` (einfarbige `M_…`-Materialien); die Option
  gibt es in CLI, Blender-Add-on, Desktop-Fenster und in der Cube-Escape-Werkbank. Glow-/Status-, Glas- und
  Kristallmaterialien bleiben untexturiert (`docs/UNITY_INTEGRATION.md`).
- **Blender-Plugin** (MCP, Werkzeuge `mcp__Blender__*`): steuert das **laufende** Blender des Nutzers (Add-on „MCP“
  aus dem Extensions-Repository von Blender Lab, Port 9876). Als Prüfstand nutzen: Exporte laden und nachmessen
  (Maße, Pivot, Vorderseite, Teil-/Materialnamen, Öffnungen für die Kollision), Texturen am Modell ansehen, Ansichten
  rendern. Immer in einer eigenen Szene, nichts speichern – die Quelle bleibt der Generator. Ohne laufendes Blender
  (Cloud, Batch) fehlt das Plugin; dann gilt nur der Batch-Export.

## Plugins und Hooks (Claude Code)

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
| `hookify` | Regeln als `.claude/hookify.<name>.local.md` (eingecheckt mit `git add -f`, da `.claude/` lokal ausgeschlossen ist) |
| Blender-MCP | siehe „Werkzeuge: ImageMagick und Blender-Plugin“ |

**Hooks** (hookify) **blockieren** Unity auf einem Checkout, nacktes `git stash` (geteilter Stash-Stapel), Force-Push
und Änderungen von Hand an `output/`; sie **halten das Sitzungsende an**, bis nach einer Python-Änderung die Suite lief,
und **warnen** bei Commit/Merge/Tag/Push (nur auf Wunsch), Golden-Daten und Versionsdateien. Ändert sich eine dieser
Regeln, ändert sich ihre Hook-Datei mit.

## Blender-Batch schnell halten (Erfahrungen aus dem Roboter-Generator)

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
  langsamer (50–54 s statt 47–49 s, `--jobs 3`, gemessen 0.15.0).
- **ImageMagick parallel nur mit `MAGICK_THREAD_LIMIT=1`.** Die OpenMP-Threads paralleler Prozesse warten aktiv
  aufeinander (eine Montage aus 28 Kacheln: 1,6 s statt 3,8 s, parallel noch deutlich mehr). Die Ausgabe bleibt
  bitgleich. Cubegen setzt es für die Blender-Worker von `--jobs` (`bake._magick`); Texturen, Icons und
  Kontaktbogen laufen nacheinander im Hauptprozess.
- **Bytegleiche Bilder sind die Voraussetzung für jeden Cache.** Jeder ImageMagick-Aufruf läuft mit
  `imagemagick.REPRODUCIBLE` (`-define png:exclude-chunks=date,time`); `cubegen/cache.py` übernimmt Texturen, Icons,
  Kontaktbogen und Material-Übersicht nur, wenn Eingabeschlüssel und Datei-Hashes stimmen. Neue Bildschritte nutzen
  denselben Cache; ein Test erzeugt zweimal und vergleicht die Bytes.
- **Zeiten messen statt schätzen:** Das Manifest trägt `timings` mit Budget je Stufe (`STAGE_BUDGETS`); eine neue
  Stufe bekommt ein Budget aus einer Messung. Nach Code-Änderungen `python3 tools/run_tests.py --tier quick`
  (rund 30 s), vor dem Release die volle Suite.
- **numpy-Kleinkram:** `foreach_get("co", …)` in ein `float32`-Array lesen (das native Format; `float64` erzwingt eine
  langsame Umwandlung, 3× langsamer), Hüllquader-Tests für alle Paare auf einmal statt einzeln je Paar.
- **Nicht übertragbar** (geprüft 0.15.0): Paletten aus Gewichtskarten zusammensetzen – Cubegen backt keine Paletten
  (`palette.py` ist reines Python, `baked` backt eine Palette je Lauf). EEVEE-`BLENDED` – kein Cubegen-Material ist
  transparent. `foreach_get` als `float32` – Cubegen liest keine Meshes mit `foreach_get`. Kommen solche Fälle
  dazu (z. B. Texturvarianten je Palette, transparente Materialien), gelten die Regeln oben.
- **Die Neural Engine nutzt Blender nicht** (nur über Core ML erreichbar); Metal verteilt GPU-Arbeit selbst auf alle
  GPU-Kerne. Geprüft in 0.14.2: Vision-Merkmalsvergleiche taugen nicht als Prüfschranke (je Gerät andere Werte,
  trennen Fehler nicht besser als ein exakter Pixelvergleich); höchstens als Hinweiswerkzeug mit Zeitregel (ROADMAP).

## Ausrichtung gerichteter Modelle

Bei Kameras und anderen gerichteten Modellen die tatsächliche Funktionsfläche prüfen,
nicht nur die Objektrotation: Blender-/Unity-Achsen, Neigung und beide Schwenkvorzeichen
gegen die exportierte Geometrie testen. Ein Anker- oder Bounds-Test ersetzt keinen
Nachweis der Blickrichtung. Beabsichtigte Korrekturen gegenüber alten Generationen
ausdrücklich dokumentieren und historische Ausgaben getrennt prüfen.

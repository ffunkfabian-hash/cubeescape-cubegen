# Changelog

Einzige Übersicht der Versionen: je Version 3–5 Zeilen und ein Link auf den Bericht (`docs/versions/` für die letzten drei
Hauptversionen, `docs/archive/versions/` für ältere). Ausführliche Texte vor 0.30 stehen in der Git-Historie dieser Datei.

## tools-0.16 „Tidemark“ – 2026-10-22

- Gemeinsame Werkzeuge über `ce_sync.py` aus Agent Tools 0.16 (ce-agent-tools#15): `./ce plugins check|fix` hält die Claude-Code-Installationen von ce-shared auf einer Version (je Worktree ein Eintrag, Update erreicht sie nicht sicher); der SessionStart-Hook des Plugins warnt bei älterem ce-shared.
- `"autoUpdate": true` am Marketplace in `.claude/settings.json`; Hinweis in `AGENTS.md` › Plugins und Hooks; fachliche Versionen und Ausgaben unverändert.

## tools-0.15.1 „Wakeline“ – 2026-10-22

- Gemeinsame Werkzeuge über `ce_sync.py` aus Agent Tools 0.15.1 (ce-agent-tools#13, #14): `./ce session mail` braucht keinen Namen mehr und teilt den Stand mit dem neuen Stop-Hook des Plugins, der den Postfach-Wächter für reservierte Sitzungen selbst startet (am Mac live geprüft); `say` nimmt den Absender aus der Reservierung des Worktrees.
- Hook-Beschreibung in `AGENTS.md` › Plugins und Hooks ergänzt; fachliche Versionen und Ausgaben unverändert.

## tools-0.14.0 „Crosstalk“ – 2026-10-22

- Gemeinsame Werkzeuge über `ce_sync.py` aus Agent Tools 0.14 synchronisiert: `--reserve`/`./ce session patch` melden die Sitzung im Postfach (cubeescape-nexogen#16) an, `./ce session say|who` schreiben Sitzungen einander bzw. listen die angemeldeten.
- Eigenständiger Werkzeugpaket-Stand; fachliche Versionen und Ausgaben unverändert.
- Abnahme über [Tools #12](https://github.com/ffunkfabian-hash/ce-agent-tools/pull/12) (401 Tests, Opus-Richter), `ce_sync --check` und Repo-Quick.

## tools-0.13.0 „Glasshouse“ – 2026-10-22

- Gemeinsame Werkzeuge über `ce_sync.py` aus dem geprüften Agent-Tools-Quellstand 0.13 synchronisiert: Dashboard, Belegvergleich, Vorprüfung, Durchlaufmessung und strengere Cloud-/Vertragsprüfungen.
- Eigenständiger Werkzeugpaket-Stand; fachliche Versionen und Ausgaben unverändert, bestehende Gatehouse-Hooks werden nicht neu installiert.
- Abnahme über [Tools #11](https://github.com/ffunkfabian-hash/ce-agent-tools/pull/11), Quellhash-Abgleich, Repo-Quick und Doku-Prüfung.

## tools-0.12.0 „Gatehouse“ – 2026-10-22

- Gemeinsame Werkzeuge über `ce_sync.py` aus der freigegebenen Quelle Agent Tools 0.12 synchronisiert, einschließlich der Korrektur für ältere Toolgen-Prüfschnittstellen aus 0.11.1.
- Hook-Beschreibung ergänzt: gemeinsame Client-Vorabprüfung und unabhängiges Git-Netz werden über Nexogen installiert; Einbau und Grenzen bleiben zentral dokumentiert.
- Eigenständiger Werkzeugpaket-Stand; Abnahme durch Quellfreigabe [Tools #10](https://github.com/ffunkfabian-hash/ce-agent-tools/pull/10), Hash-Abgleich, Repo-Quick und Doku-Prüfung.

## 0.32.0 „Relaywake“ – 2026-10-22

- Eingebettete gemeinsame Werkzeuge von der geprüften Quelle Agent Tools 0.11 „Wayfinder“ synchronisiert: FTS-Korrektur, öffentliche Such-Aliase, risikobasierter Richter und budgetierter API-Einstieg.
- Nur Werkzeug-Rollout auf Basis 0.31.0; fachliche Daten, Generator-Ausgabe und Verträge unverändert. Hash-Abgleich und repo-eigener Quick sind die Abnahme.
- [Versionsbericht](docs/versions/0.32.md).

## 0.31.0 „Crosscurrent“ – unveröffentlicht

- Gemeinsame Agentenwerkzeuge, `./ce`, Suchserver-Konfiguration und kurze Lehren angebunden.
- Nachtlauf verwendet die vorhandene volle Testsuite mit exklusiver Ressourcensperre.
- Generator, Modelle und Sidecar-Format unverändert; keine neuen Bild-Ausgaben erzeugt.
- [Versionsbericht](docs/versions/0.31.md).

## 0.30.2 „Lattice“ – unveröffentlicht

* Formen `--shape voxel|facet` behalten die begehbare Oberseite: Voxel setzen über der obersten Zelle Feinschichten (0,05 m) auf,
  Voxel bauen die oberste Platte exakt als Deckel, Facetten nehmen Eckpunkte hinzu, bis keiner mehr als 0,05 m über der Hülle liegt (Tank, Ventilator, Turbine sanken um bis zu 1,2 m).
* Glatte Modelle, Collider, Teile, IDs, Atlas und Dreiecksbudget unverändert; Golden-Werte nur `shape_voxel`/`shape_facet`.
* Neuer Test `tests/test_release_0302.py`, Unity-Sätze `shape_round`, `shape_round_voxel`.

Bericht: [Cubegen 0.30.2](docs/versions/0.30.md#cubegen-0302--lattice).

## 0.30.1 „Common Ground“ – unveröffentlicht

* Nur Werkzeuge und Doku; Generator, Geometrie, Materialien und Sidecars unverändert (bis auf die Versionsangabe).
* Gemeinsamer Standard: `.ce-repo.json`, eingebettete Werkzeuge `tools/ce_tools/`, Wrapper `./check` und `./release`.
* `AGENTS.md` auf 150 Zeilen in Standard-Gliederung (Langfassung: `docs/DEVELOPER.md` 9); neu `docs/ENTSCHEIDUNGEN.md`.

Bericht: [Cubegen 0.30.1](docs/versions/0.30.md#cubegen-0301--common-ground).

## 0.30.0 „Lattice“ – unveröffentlicht

* Atlas konkav nachgepackt, Belegung im Manifest (`atlas_occupancy`); QA-Cache (`quality.check_cached`).
* `--shape smooth|voxel|facet|holes`: abgeleitete Formen mit gleichen Teilen, Collidern und Atlas; Golden- und Unity-Prüfsätze.
* Vertrag Version 4 (rückwärtskompatibel, `--contract 3` wie bisher): Zonenkarte `textures.zones`, Effektblock `effects`.
* Versionsberichte neu geordnet: ein Bericht je Hauptversion, ältere im Archiv; `app/notarize.sh` entfernt.
* Neues Werkzeug `tools/atlas_check.py`: Belegung, Überlappung und Ränder der Atlas-UVs (Atlas ohne Befund).
Bericht: [Cubegen 0.30](docs/versions/0.30.md).

## 0.29.0 „Crossflow“ – 2026-10-15

* Nur Doku; Code, Geometrie, Materialien und Sidecars unverändert (bis auf die Versionsangabe).
* Neu: `docs/TECHNIK.md` mit den Techniken des Roboter-Generators (1.20.6) und ihrem Stand in Cubegen.
* Aufwand und empfohlene Reihenfolge je Technik; Modell-Editor-Checkliste abgehakt; Verweise aus `AGENTS.md`/`DEVELOPER.md`.

Bericht: [Hauptversion-Bericht](docs/versions/0.29.md#cubegen-0290--crossflow).

## 0.28.0 „Clean Slate“ – 2026-10-15

* Nur ein Test; Code, Geometrie, Materialien und Sidecars unverändert.
* `test_blender_starts_while_the_textures_are_built` schlug mit dem gemeinsamen Rechner-Cache fehl (seed 3 `crate,door`).
* Der Test bekommt jetzt einen eigenen, leeren `CUBEGEN_CACHE`-Ordner (wie `BakeTest` seit 0.26.0).

Bericht: [Hauptversion-Bericht](docs/versions/0.28.md#cubegen-0280--clean-slate).

## 0.27.0 „Fieldbook“ – 2026-10-15

* Doku und ein Werkzeug; Generierung, Geometrie, Materialien und Sidecars unverändert.
* `docs/DEVELOPER.md` neu: Abschnitte 1–8 (vorher CLI.md 16.1–16.8) wörtlich übernommen, Verweise angepasst.
* Unity-Check hält die Sperre für schwere Läufe bis zum letzten Enkelprozess (eigene Prozessgruppe, `run_in_group`).
* Neue Tests: `tests/test_release_0270.py`.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.27.md#cubegen-0270--fieldbook).

## 0.26.1 „Stockpile“ – 2026-10-15

* Nur Doku: `AGENTS.md` von 462 auf 281 Zeilen gekürzt; Code und Ausgabe unverändert.
* Messwerte, Begründungen und lange Beispiele wanderten nach `docs/CLI.md` › 16 „Entwicklerhintergrund“.
* In `AGENTS.md` bleiben die Regeln und je ein Verweis (16.x).

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.26.md#cubegen-0261--stockpile).

## 0.26.0 „Stockpile“ – 2026-10-15

* Blender-Ergebnisse (Export, Karten, Vorschau) im gemeinsamen Cache: Anstrich, sechs Modelle, 512 px: 13,4–15,1 s → 1,8–2,0 s.
* GitHub Actions: ein Job je Lauf (Push `main` = `quick`, PR = volle Suite, „Run workflow“ wählbar); `app/**` löst nichts aus.
* Neuer Release-Befehl `tools/release.py`: Probelauf mit allen Prüfungen, `--apply` merged, taggt und pusht atomar.
* Repo-Name `cubeescape-cubegen` in Doku und `tools/install.sh`; Geometrie und Sidecars unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.26.md#cubegen-0260--stockpile).

## 0.25.0 „Quartermaster“ – 2026-10-15

* Gemeinsamer inhaltsadressierter Cache `~/Library/Caches/Cubegen/cache` für Texturen, Icons, Kontaktbogen und Set-Reihen.
* `CUBEGEN_CACHE` verlegt (`0`: aus), `CUBEGEN_CACHE_LIMIT_GB` begrenzt (Standard 4); `python3 -m cubegen cache` mit `--prune`/`--migrate`.
* `tools/run_tests.py` mit numpy-Gruppe, Interpreter- und Skip-Ausgabe, frischem Cache je Lauf.
* `tools/unity_check.py` wartet auf die Sperre `heavy-run.lock` (Cube Escape 0.59); `CE_HEAVY_LOCK=0` überspringt.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.25.md#cubegen-0250--quartermaster).

## 0.24.0 „Primer“ – 2026-10-14

* `--paint` schreibt fünf neutrale Karten `MTN_<Modell>_…` (Gewichte, Rauschen, Detail, AO/Kante/oben/Höhe); `MTP_` entstehen daraus (max. 5/255 Abweichung).
* Vertrag Version 3 (`textures.neutral`, `weight_layout`, `paint`, `neutral_maps`, `materials`, `paint_scheme`); `--contract 2`/`1` wie bisher.
* Eigene Materialien `M_Liquid`, `M_Hologram`, `M_Lamp`, `M_Leaf`, `M_Biolume`, `M_Signal`, `M_Accent`, `M_Optic` in 20 Typen; `M_Crystal` nur noch echter Kristall.
* `tools/paint_reference.py` (Vergleichsbilder), `cubegen catalog --paints`, Unity-Check-Prüfsatz `neutral`.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.24.md#cubegen-0240--primer).

## 0.23.0 „Wingman“ – 2026-10-14

* Agenten-Werkzeuge: Subagents `cg-test-runner` und `cg-doc-keeper` in `.claude/agents/`, Werkzeuge je Agent in `.claude/agent-guard.json`.
* Gemeinsames Plugin `ce-shared` (privates Repo `ce-agent-tools`) liefert Force-Push-, Stash-, Unity- und Actions-Hooks.
* Generator und Ausgabe unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.23.md#cubegen-0230--wingman).

## 0.22.0 „Beacon“ – 2026-10-14

* Vertrag Version 2 mit `baked_maps` und Leuchtkarte (`textures.baked.Emission`); nur Themen mit `edge_glow` > 0 schreiben sie.
* Rückweg für den heutigen Import: `generate --contract 1`, `contract --version 1`, `check --export … --contract 1`.
* Manifestformat 2: `format`, `sets[].faces_unity`/`bounds`, `models[].set`, `joins`, `connectors[].moves`, `dressings`.
* Modelle im Modus `baked` ohne gebackenes Material bekommen keinen `textures`-Eintrag mehr.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.22.md#cubegen-0220--beacon).

## 0.21.3 „Monolith“ – 2026-10-14

* GitHub Actions sparsam: nach 14 Tagen waren 90 % der 2.000 Freiminuten weg (13 Jobs, rund 40 min je Lauf).
* Jetzt `push` nur auf `main`, Abbruch alter Läufe, Doku löst nichts aus, ein Job je Python-Version, `timeout-minutes`.
* Regel global und in `AGENTS.md`, Hook `actions-sparsam`; Ausgabe unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.21.md#cubegen-0213--monolith).

## 0.21.2 „Monolith“ – 2026-10-14

* Test der Kiste mit Kacheln: ImageMagick 6 schreibt zwei sonst gleiche Karten verschieden (9 statt 8 Texturen).
* 8 Texturen werden nur mit ImageMagick 7 verlangt, das Budget immer; Ausgabe unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.21.md#cubegen-0212--monolith).

## 0.21.1 „Monolith“ – 2026-10-14

* Texturbudget der Werkbank wie Cube Escape 0.51: jede (Rolle, Bildinhalt) einmal, 1 Byte je Pixel × 4/3.
* Kiste mit Kacheln in 2048 px (Seed 4242): 8 Texturen, 42,7 MB und im Budget; 0.21.0 rechnete 268 MB.
* Nur Texturen, die ein Material lädt, zählen.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.21.md#cubegen-0211--monolith).

## 0.21.0 „Monolith“ – 2026-10-13

* `--single-renderer`: statische Modelle mit reinen Schmuckteilen werden ein Mesh-Objekt (53 von 63 mehrteiligen Typen); Manifest `renderers`.
* `contract.check_runtime_budget` liest jedes GLB gegen das Budget von Cube Escape; `runtime_budget` im Manifest.
* `timings.steps` im Manifest, `tools/perf_band.py`; Modelle einmal je Lauf gebaut, Katalog ohne Blender CPU 4,65 → 2,57 s.
* Unity-Check-Prüfsatz `single`; Ausgabe ohne die Option unverändert (Golden-Daten).

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.21.md#cubegen-0210--monolith).

## 0.20.0 „Gatekeeper“ – 2026-10-13

* Neues `tools/unity_check.py`: acht feste Prüfsätze durch Cube Escapes echten Import (Editor und Werkbank-Laufzeit) via `verify.sh`.
* Bericht `output/unity_check/report.json`; erster Lauf: 254 Modelle, 0 Fehler, knapp 3 min.
* Fester Schritt jedes Releases; Ausgabe der Modelle unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.20.md#cubegen-0200--gatekeeper).

## 0.19.1 „Kaleidoscope“ – 2026-10-13

* CI wieder grün: ImageMagick 6 des Ubuntu-Runners schrieb Zeitstempel in PNGs (rot seit 0.17.0).
* Neu `imagemagick.strip_png_dates` nach jedem Schreiben; Bildvergleich im Test nutzt das gefundene ImageMagick.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.19.md#cubegen-0191--kaleidoscope).

## 0.19.0 „Kaleidoscope“ – 2026-10-13

* Bau-Kit set-fähig (`set_faces`, `set_pins`): alle 13 Typen halten im Set ihren Umriss (0.18: zehn nicht); Deckenmodul-Überstand behoben.
* Anbauten auf Boden, Säule, Steg (`dressing = ruin | organic`); Kristall-Schliff `crystal_cut = faceted` und `crystal_color` je Thema.
* Farbwähler in der App (`PaintEditor.swift`, 25 Prüfungen), `tools/vision_report.py`, GitHub-Job `blender`.
* Zusatzdetails für acht Typen: 6–7 → 9–10 von 10 unterscheidbar; Golden-Daten dieser Typen neu.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.19.md#cubegen-0190--kaleidoscope).

## 0.18.1 „Chameleon“ – 2026-10-13

* Fehler: Leuchtschlitz der Modulwand war fest `M_GlowOrange` und ignorierte das Thema (Orange statt Cyan bei `--paint organic`).
* Jetzt folgt er der Leuchtfarbe des Stils (`ParamReader.glow_or`), ohne Würfelwurf; ohne Vorgabe orange.
* Golden-Daten: nur Modulwand-Fälle mit Leuchtvorgabe.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.18.md#cubegen-0181--chameleon).

## 0.18.0 „Chameleon“ – 2026-10-13

* Anstriche auf allen Typen in elf Themen geprüft; `M_Ground` je Thema ein neutraler Grundton, Staub/Moos/Schnee fleckig.
* Eigenes Thema `--paint-file <Datei.json>` (CLI, Rezept, App, Fenster), im Manifest `config.paint_scheme`; Beispiel `paints/custom_example.json`.
* `test_wall_modules.dressing = none | ruin | organic`, Set-Umriss bleibt (45 Varianten geprüft).
* Unity-ToDos 28–30 in der ROADMAP; Golden-Daten: nur `test_wall_modules`.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.18.md#cubegen-0180--chameleon).

## 0.17.0 „Prism“ – 2026-10-13

* Stiltest Anstriche (`tools/style_test.py`): einmal neutral backen, Anstrich als Daten (`cubegen/paint.py`), 0,2–0,3 s je Zusammensetzung.
* `--set`: Varianten mit gleichem Umriss und anderem Innenleben, Manifest `sets`, Reihenbild `set_<Typ>.png`.
* `--paint` als Ausgabemodus mit elf Themen; Unity liest das Ergebnis wie `--textures baked`.
* Neuer Typ `test_wall_modules`; Golden-Daten nur dieser Typ neu, 186 unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.17.md#cubegen-0170--prism).

## 0.16.0 „Overdrive“ – 2026-10-12

* Neue macOS-App `app/` (`Cubegen.app`, SwiftUI + SceneKit) mit Katalog, Vorabprüfung, Galerie und 3D-Ansicht; `app/test_app.sh` 17 Prüfungen.
* `--jobs auto` ist Standard (bis Kerne − 1 Blender-Prozesse); ImageMagick parallel (186 Modelle Kontaktbogen 2 statt 20 s).
* Backen: Rauheit und Metall in einem Durchgang (4 statt 5), Karten bytegleich; Qualitätsprüfung 35 % weniger CPU.
* Versionsnamen ab jetzt cool und englisch.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.16.md#cubegen-0160--overdrive).

## 0.15.0 „Stoppuhr“ – 2026-10-12

* Behoben: ImageMagick schrieb Zeitstempel in PNGs; jetzt `-define png:exclude-chunks=date,time`, Ausgabe bytegleich.
* Bildcache (`.cubegen_cache.json`, `--force` baut neu): Station-Kit mit gebackenen Texturen 8,1 → 1,4 s.
* Backen: eine zusammengefügte Kopie je Asset, neu `--bake-device auto|cpu|gpu` (auto = GPU ab 1024 px).
* `--jobs` verteilt Modelle als Arbeitspakete; `manifest.json` › `timings`; `tools/run_tests.py --tier quick|standard|full`.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.15.md#cubegen-0150--stoppuhr).

## 0.14.2 „Werkstattbuch“ – 2026-10-12

* Neural-Engine-Prüfung (mit Roboter-Generator 1.9.2): schnell (3,8 ms je Bild), taugt aber nicht als Prüfschranke.
* Nebenbefund: `--unique` übersieht fast gleiche Varianten, da die Signatur exakt gleiche Dreieckszahlen verlangt.
* ROADMAP um drei offene Punkte ergänzt (tolerantere Signatur, Doubletten-Bericht, Icon-Lesbarkeit).
* Nur Doku; Generator, Ausgaben und Golden-Daten unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.14.md#cubegen-0142--werkstattbuch).

## 0.14.1 „Werkstattbuch“ – 2026-10-12

* `CLAUDE.md` importiert `AGENTS.md`; neuer Abschnitt „Plugins und Hooks (Claude Code)“.
* Acht hookify-Regeln in `.claude/`: blockieren Unity auf Checkout, nacktes `git stash`, Force-Push, Änderungen an `output/`.
* Weitere Regeln verlangen die Python-Suite vor Sitzungsende und warnen bei Git-Veröffentlichung und Golden-Daten.
* Nur Doku und Agenten-Werkzeuge; Ausgaben unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.14.md#cubegen-0141--werkstattbuch).

## 0.14.0 „Werkstattbuch“ – 2026-10-12

* AGENTS.md: Abschnitt „Blender-Batch schnell halten“ mit gemessenen Erfahrungen aus dem Roboter-Generator.
* Themen: Cycles-Backen je Objekt, UV-Packen, EEVEE bei `BLENDED`, Worker mit `-t 1`, ImageMagick-Threadgrenze.
* ROADMAP: offener Punkt „Schnellere Blender-Läufe“. Nur Doku; Ausgaben unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.14.md#cubegen-0140--werkstattbuch).

## 0.13.0 „Patina“ – 2026-10-10

* Desktop-GUI: Auswahl Texturen (keine / Kacheln / Kacheln + Gebrauchsspuren / Farbpalette), Größe und Palette wie `--textures`.
* Argumente aus `texture_args()` mit Tests (`tests/test_gui_textures.py`).
* AGENTS.md: Abschluss in zwei Stufen (ungeprüft / abgenommen) mit Vorlage für den lokalen Test; ImageMagick und Blender-MCP.
* Paket, CLI und Add-on auf 0.13.0.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.13.md#cubegen-0130--patina).

## 0.12.0 – 2026-10-10

* Release der Arbeitsstände 0.11.1–0.11.4: erste bis dritte Asset-/Stationswelle, sieben Modell-Kits, Kollisionskorrekturen Generation 3.
* Generationen 1/2 bleiben unverändert; Release-Zweig `release/0.12.0`.
* Prüfung: 258 Python-Tests grün (inkl. Blender-Smoke).

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.12.md#cubegen-0120--stationswellen-modell-kits-und-generation-3-korrekturen).

## 0.11.4 – veröffentlicht mit 0.12.0

* Generation 3: hohle Spindfächer, freier Leitereinstieg am Etagenbett, Wartungsdeckel, Geländerprofile für Stegkreuzungen.
* Offenes Waschbecken, Wasserbehälter an der Kaffeemaschine, feste Halterungen der Statuspfosten der Ausfahrbrücke.
* Dritte Stationswelle: zwölf Modelle (`recipes/station_wave3.json`) und sieben Kits mit je neun Modellen unter `recipes/kits`.
* Familienrezepte mit Namen einer eingebauten Familie laden deren Maßvertrag wieder; Unity: Portalflächen angepasst.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.11.md#cubegen-0114--modellprüfung-und-familien-kits).

## 0.11.3 – veröffentlicht mit 0.12.0

* Zweite Stationswelle: `recipes/station_wave2.json`, 28 zusätzliche Exportmodelle aus vorhandenen Typen.
* `collapsed_catwalk`: Generation 3 nutzt genaue feste Mesh-Collider statt Bodenbox; Geometrie und Generation 1/2 unverändert.
* Acht Golden-Digests gezielt auf den vollständigen Kollisionsvertrag aktualisiert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.11.md#cubegen-0113--zweite-stationswelle-und-vollständige-stegkollision).

## 0.11.2 – 2026-10-09

* Erste Asset-Welle: elf neue Typen (u. a. `airlock_chamber`, `pipe_rack`, `turbine`, `compressor`), nun 186 Typen.
* Gameplay-Skripte nur über Optionen (`turbine.machine`, `compressor.machine`, `warning_beacon.signal`).
* Varianten: `door.variant=iris`, `hatch.variant=maintenance`, `keypad.variant=access`; bestehende Seeds bitgleich.
* Korrektur: `test_*`-Prototypen mit genauen Mesh-Collidern statt Gesamtbox (Generation 3); 240 Tests grün.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.11.md#cubegen-0112--erste-asset-welle-aus-ideenmd-varianten-und-prototyp-kollision).

## 0.11.0 – 2026-10-08

* Fragmentkollision Generation 3: Compound-Parents mit getrennten Shard-Collidern, exakte Partitionen für Rohre, Profile, Drehkörper.
* Fehler behoben: `cocoon`/`stalagmite` Seed 1, `fallen_pillar` (Oberkante unter Grundfläche), Kryokapsel-Pivot.
* `steam_vent` erhält den fehlenden `FX_Steam`-Anker; Blender-Export aktualisiert den View-Layer vor der Collection-Auswahl.
* Unity-Übernahme per Fast-Forward, 891/891 Tests grün; 0.10.6 wurde in 0.11.0 übernommen.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.11.md#cubegen-0110--fragmentkollision-und-unity-integration).

## 0.10.5 – 2026-10-08

* Kollisionsprüfung nutzt den echten Unity-Vertrag; fehlende feste Kollision ist ein Fehler.
* Generation 3 ergänzt fehlende Collider je Teil (genaue feste Meshes); alte Exporte brauchen Reexport/Reimport.
* Dampfventile mit Body-/Wheel-Kollision; Kastenkameras schauen 15–30° nach unten.
* Zerstörte Exporte triangulieren zerbrochene Flächen explizit; Generationen 1/2 unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cubegen-0105--versions--und-prüfbericht).

## 0.10.4.1 – 2026-10-07

* Neuer Clutter-Pass: `--clutter clean|lived-in|chaotic` bzw. `style.clutter` platziert Werkzeug-, Ersatzteil- und Keycard-Meshes.
* Erste Flächen: intakte Tisch- und Labortische; Abstände werden geprüft, Fehlplätze als `clutter_pass.skipped` im Sidecar.
* Props als eigene `Clutter_*`-Objekte; Tisch-Kleinkram wird bei aktivem Pass ersetzt.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cubegen-01041--arbeits--und-prüfbericht).

## 0.10.4 – 2026-10-07

* Schwenk-Vorrotation folgt der Richtung bei Kamera und Geschütz; negative Speed-Parameter erlaubt.
* Explizites `speed: 0` bleibt stehen (Generation 2/3); Generation 1 unverändert.
* Druckplatten, Kameras und Geschütze der Generation 3 mit festen und bewegten Mesh-Collidern.
* Prüfung: 170/170 Python-Tests grün; Unity-Phase 3 mit 859 Tests grün.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cubegen-0104--releasebericht).

## 0.10.3 – 2026-10-07

* Paket, CLI und Blender-Add-on einheitlich 0.10.3 (Add-on meldete zuvor 0.10.2.4); Regression prüft auch den ZIP-Inhalt.
* Berichtstest prüft die aktuelle Paketversion statt einer festen Patchnummer.
* Cube-Escape-Phase 2 dokumentiert: 36 echte FBX ohne Importfehler; Geometrie und Gameplay-Vertrag unverändert.
* Prüfung: 166 Python-Tests grün.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cube-escape-generator--version-0103).

## 0.10.2.5 – 2026-10-07

* Neue Primitive: Hohlrohre, U-/L-/T-/I-Profile, Keile, Gitter, gerundete Boxen.
* `geometry_test` zeigt alle acht Formen als CLI-Demo.
* Zehn experimentelle Gameplay-Prototypen aus `IDEEN.md`; nicht Unity-geprüft, ohne Puzzle-Logik.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cube-escape-generator--version-01025).

## 0.10.2.4 – 2026-10-07

* Desktop-GUI zeigt nach dem Build gerenderte Vorschauen.
* Interaktive OBJ-Ansicht mit Drehen und Zoomen; Blender-Builds exportieren dafür zusätzlich OBJ.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cube-escape-generator--version-01024).

## 0.10.2.3 – 2026-10-07

* Vorab- und Qualitätsberichte mit Score, Rang, Metriken und Hinweisen auf ähnliche Varianten je Variante.
* Inkrementelle Builds erkennen unveränderte OBJ-Assets (`--force` baut neu).
* Neue Desktop-GUI (`cubegen gui` / `cubegen-gui`) mit Modellwahl, Rezepten, Vorabprüfung, Ähnlichkeitsfilter.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cube-escape-generator--version-01023).

## 0.10.2.2 – 2026-10-07

* Optionale Asset-Bereinigung entfernt nur unreferenzierte leere Meshes; Qualität `pass`/`warning`/`error`.
* `generate --strict` behandelt Warnungen als Fehler, `--relaxed` lässt sie zu; `--validate-only`, `--report FILE`.
* Manifeste: Connector-Kompatibilitätsmatrix, UTC-Zeit, Quellcodehash, SHA-256 je Asset.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md#cube-escape-generator--version-01022).

## 0.10.2 – 2026-10-07

* Palettenexport: Sidecars enthalten `textures.mode: palette` und relativen Pfad zum Palettenmanifest (Importer löst Maps nun auf).
* Rollenvertrag: `body`-Rollen von `Rotatable`, `SignalLight`, `SignalIndicator` sind Einzelteile.
* Enthält die Phase-0-Korrekturen aus 0.10.1; Tag `v0.10.2`.
* Prüfung: 148 Python-Tests, Unity-Adapter 842 Tests grün; alle 164 alten FBX bestehen ohne Ausnahmen.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md).

## 0.10.1 – historischer Arbeitsstand, 2026-10-07 (in 0.10.2 enthalten)

* `phase_platform`/`portal_frame`: `SignalLight.parts.glow` ist ein einzelner Teilname statt Liste.
* Eigene konvexe Mesh-Collider für Ventilräder (`water_level`) und das runde Luken-Verschlussrad (`hatch`).
* `sequence_panel`: Tastenanzeiger als `meta.deferred_behaviours` im Manifest erhalten, noch nicht spielbereit.
* Prüfung: 147 Python-Tests; 164 Typen: 82 Gameplay / 74 statisch / 8 offen / 0 Fehler; 135 Geometriefälle unverändert.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md).

## 0.10.0 – 2026-10-06

* Add-on „Einrasten“ (`cubegen/snapping.py`, Regeln `families.JOINS`); Paletten-Modus `--textures palette`
  (`MP_Palette`, ein Draw Call) mit acht Farbpaletten (`--palette`, `cubegen palettes`).
* Neu: `sweep` für `camera`/`turret`, Familien `medbay`, `derelict`, `greenhouse`, `reactor`, Zustand `fractured`,
  Blockschrift (`sign.text`, `door.label`), 35 neue Typen (jetzt 164).
* Generation 3 (Standard): Anker `Audio_*`/`FX_*`; `--generation 1|2` baut ältere Stände bitgleich nach.
* Prüfungen/Korrekturen: Collider-Abdeckung (`check`), Vertrag `contract.json`, 0 flackernde Flächen (2 mm Versatz),
  Fixes für `archway`, `solar_panel`, Luftschleuse (Blattreihenfolge), Add-on mit `foundry`/`lab`.
* Tests parallel in drei Gruppen: rund 2 statt 6½ Minuten.

Bericht: [Hauptversion-Bericht](docs/archive/versions/0.10.md).

## 0.9.0 – 2026-10-06

* Modellfamilien mit verbindlichen Maßen und Bau-Kits (`station`, `foundry`, `lab`), `--family`, `--match`,
  Passungsprüfung (0 von über 15 000 Fugen fehlerhaft).
* 8 neue Typen (jetzt 129); neue Varianten für `wall` (`opening`), `catwalk.shape`, `stairs.layout`; alte Seeds bitgleich.
* Unity-Vertrag: `contract.py` prüft Sidecars gegen FBX; `item_id` für `ItemPickup`; `--lods`-Sidecar korrigiert.

## 0.8.0 – 2026-10-06

* Behoben: falsche Pivots ab der dritten Ebene in der FBX (`balance_scale`, `robot_arm`, `turret`); FBX wird nach
  dem Export zurückgelesen und geprüft – diese Typen neu exportieren.
* Gleicher Seed = gleiches Modell: `tests/golden.json`, `StableRandom`, `a.sub("name")`; Python 3.9 bis 3.13 bitgleich.
* Neu: `--unique`, `--theme`, `--lods` (im Median 30 % weniger Dreiecke), inkrementelle Läufe, `--jobs`,
  `cubegen check` (Dreiecke, Draw Calls, Z-Fighting), Rezeptprüfung mit Tippfehler-Hinweisen.

## 0.7.0 – 2026-10-06

* Neu: `colliders` im Sidecar (Boxen oder konvexe Mesh-Collider) für begehbare und bewegte Typen (`stairs`,
  `catwalk`, `platform`, `lift`, `hatch` …); zerstörte Varianten ohne.
* 17 neue Typen (jetzt 121): Fallen, Rätsel, Bau-Kit-Teile, Items, Geräte; Rezept `recipes/traps_riddles.json`.
* Gleiche Seeds liefern dieselben Modelle wie 0.5.0.

## Frühere Versionen

Siehe Git-Historie (0.5.0: 104 Typen, Parameter & Stil, Texturen, Zerstörung, Blender-Add-on).

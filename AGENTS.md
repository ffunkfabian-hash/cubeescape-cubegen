# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

Langform, Begründungen und Messwerte zu den Abschnitten unten: `docs/DEVELOPER.md` (ein Abschnitt je
Verweis). Techniken des Roboter-Generators und ihr Stand in Cubegen: `docs/TECHNIK.md`. Versionsgeschichte: `CHANGELOG.md` und `VERSION_<Version>.md`.

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
Branches und Worktrees“): Fund, Ursache, Korrektur, geprüfte Varianten und verbleibende Grenzen. Veröffentlichte
Berichte bleiben historisch. Diese Regel gilt auch in allen späteren Integrationsphasen.

## Ganze Leistung des Geräts (gemeinsame Regel mit Cube Escape und dem Roboter-Generator)

Braucht eine Sitzung den Rechner für sich (Messungen, Benchmarks, Zeitbudgets, Abnahmen), darf sie andere
Sitzungen pausieren. Werkzeug: `pause_sessions.py` aus Cube Escape
(`/Users/ffunk/Claude/Cube Escape/.agents/skills/ce-testing/scripts/pause_sessions.py run -- <Befehl>`): hält nur die
Befehle anderer Claude-/Codex-Sitzungen an (SIGSTOP), setzt sie danach immer fort (SIGCONT), lässt die Sitzungen selbst,
den Unity-Editor und Blender des Nutzers unberührt. Nur so lange wie nötig pausieren und es im Bericht nennen. Ein
pausierter Befehl kann in die Zeitgrenze seines Werkzeugs laufen – dann führt die andere Sitzung ihn erneut aus.

## GitHub Actions sparsam (globale Regel)

Die Regel steht global in `~/.claude/CLAUDE.md` (Codex: `~/.codex/AGENTS.md`) und gilt für alle Repos des Kontos:
2.000 min im Monat, Budget 0 $ – leer heißt, kein Workflow läuft mehr bis zum Monatsanfang. Kurz: `push` nur auf
`main`, sonst über den PR; `concurrency` mit `cancel-in-progress`; `paths-ignore` für Doku; wenige volle Jobs; große
Matrix nur auf Wunsch; `timeout-minutes`; lokal zuerst testen. Hier **ein Job je Lauf** (`.github/workflows/tests.yml`):
Push auf `main` = `quick`, PR = `full`, „Run workflow“ = `quick`/`standard`/`full`; `app/**` löst nichts aus (DEVELOPER.md 8).

## Versionen, Branches und Worktrees

Jeder neue Branch, Worktree oder Arbeitsauftrag ist eine **neue Version**: Minor +1 (0.12.0 → 0.13.0 → 0.14.0 …)
mit einem eigenen, ausgedachten Namen – cool und auf Englisch (z. B. „Overdrive“, „Afterburner“), nie ein
beschreibender deutscher Begriff; gilt ab 0.16.0, ältere Namen bleiben. Setzt eine Sitzung dieselbe Arbeit in
einem Folge-Worktree fort, behält sie deren Version. Gleich zu Beginn, nicht erst beim Release:

- Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` (`bl_info`)
  gemeinsam anheben – `tests/test_versions.py` prüft die Gleichheit samt gebautem Add-on-ZIP.
- Branch `release/<Version>`, Bericht `VERSION_<Version>.md` mit Titel „Cubegen <Version> – <Name>“ und
  Changelog-Eintrag „## <Version> „<Name>“ – unveröffentlicht“.
- Release (nur auf Wunsch des Nutzers): Datum statt „unveröffentlicht“, Tests grün, dann `python3 tools/release.py`
  im Release-Worktree (Probelauf, ändert nichts; Prüfliste im Kopf der Datei); `--apply --trailer "Co-Authored-By: …"`
  merged im Haupt-Checkout (`git merge --no-ff`, „Cubegen <Version> – Release übernehmen“), taggt `v<Version>` und
  pusht `git push --atomic origin main release/<Version> v<Version>` – nie `--force`. `main` ist der Standard-Branch auf
  GitHub (ffunkfabian-hash/cubeescape-cubegen).

Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt nach derselben Regel.

## Abschluss in zwei Stufen

Sitzungen ohne Blender und Unity (z. B. in der Cloud, claude.ai/code) dürfen meist nur ihren eigenen Branch pushen –
keine Tags, kein `main`, keine Release-Branches – und können keinen Unity-Import prüfen. Cloud-Sitzungen richtet der
SessionStart-Hook `.claude/hooks/session-start.sh` ein (ImageMagick 6, Blender als `bpy`-Modul hinter dem Befehl
`blender`; damit laufen `--tier full` und echte Exporte auf der CPU). Kein Ersatz für Stufe 2: Blender-App mit GPU,
Blender-Plugin, `unity_check.py` und die macOS-App gibt es nur lokal.

- **Stufe 1 „ungeprüft“** (ohne Blender/Unity): `python3 -m unittest discover -s tests` (Blender-/ImageMagick-Tests
  werden ohne die Werkzeuge übersprungen – das im Bericht nennen), bei Bedarf `--no-blender`-Erzeugung; Branch pushen,
  PR mit Abschnitt „Vor dem Merge noch offen“; der Versionsbericht `VERSION_<Version>.md` trägt oben
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
geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Bericht VERSION_<Version>.md auf
Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```

## Leistung und Grenzen (seit 0.21.0; Begründung DEVELOPER.md 1)

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

## Abwechslung: Details aus eigenem Zufallsstrom

`cubegen check` zeigt je Typ, wie viele von 10 Varianten unterscheidbar sind (`variety.signature`: Objekte,
Materialien, Dreiecke, Hüllquader – Änderungen innen sieht es nicht). Zu wenig Abwechslung → kleine Details aus
`cubegen/models/details.py` (Schraubenkranz, Kennschild mit Code, Kabelkanal, Warnwinkel, Stromkasten, Käfig,
Kabeltrasse …), je Variante ein bis zwei aus `a.sub("variety")` – nie aus dem `rng` des Builders. Details bleiben
klein, statisch, weg von beweglichen Teilen und Spielpunkten (Strahlhöhe, Linse) und innerhalb von `set_faces`; ein
`Glow`-Teil behält ein Material. Die Signatur selbst nicht ändern: `--unique` würde andere Varianten wählen.

## Werkzeuge: ImageMagick und Blender-Plugin

- **ImageMagick** (`magick`, Version 7; `python3 -m cubegen doctor` zeigt, ob es gefunden wird) erzeugt die Texturen
  (`--textures tiled|baked|palette`) und ist ausdrücklich auch zum **Gestalten** erwünscht: Symbole, Schilder,
  Leucht-Masken, Paletten, Kontaktbögen; zum Prüfen von Vorschauen zuschneiden, vergrößern, `montage`,
  `compare -metric AE`. Bilder reproduzierbar erzeugen (feste Seeds, `-define png:exclude-chunks=date,time`; alles
  über `ImageMagick.run`, das danach `strip_png_dates` anwendet – ImageMagick 6 ignoriert den Define). Linux/CI hat
  oft ImageMagick 6: kein `magick`, sondern `convert`/`compare`/`montage` – nie `magick` fest aufrufen.
- **Texturen sind erlaubt** (seit Cube Escape 0.35): Standard bleibt `none` (einfarbige `M_…`-Materialien); die Option
  gibt es in CLI, Blender-Add-on, Desktop-Fenster und in der Cube-Escape-Werkbank. Glow-/Status-, Glas- und
  Kristallmaterialien bleiben untexturiert (`docs/UNITY_INTEGRATION.md`).
- **Blender-Plugin** (MCP, `mcp__Blender__*`): steuert das **laufende** Blender des Nutzers (Port 9876) als Prüfstand:
  Exporte laden und nachmessen (Maße, Pivot, Vorderseite, Teil-/Materialnamen, Öffnungen für die Kollision), Texturen
  ansehen, Ansichten rendern. Immer in einer eigenen Szene, nichts speichern – die Quelle bleibt der Generator. Ohne
  laufendes Blender (Cloud, Batch) gilt nur der Batch-Export.
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

## Blender-Batch schnell halten (Regeln; Messungen und Begründung DEVELOPER.md 2)

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

## Gemeinsamer Cache (seit 0.25.0; Aufbau und Begründung DEVELOPER.md 3)

Ein inhaltsadressierter Cache für Haupt-Checkout, Worktrees, App und `unity_check.py`: `~/Library/Caches/Cubegen/cache`
(Linux `$XDG_CACHE_HOME/cubegen/cache`); `CUBEGEN_CACHE=<Ordner>` verlegt ihn, `CUBEGEN_CACHE=0` schaltet ihn ab,
`python3 -m cubegen cache` zeigt Ort und Größe (`--prune`, `--migrate DIR`).

- **Schlüssel nur aus Eingaben, nie aus Pfaden:** kein absoluter Pfad in Schlüssel oder Einträgen. Neue Bildschritte:
  ImageMagick-Argumente aus `pipeline.py` gehören in den Schlüssel; neue Worker-Ausgaben in `modelcache.result_files`,
  neue Worker-Eingaben in den Auftrag (dann automatisch im Schlüssel).
- **Atomar schreiben** (Temp-Datei, dann umbenennen), Inhalte vor dem Eintrag; ein Cache-Fehler bricht nie einen Lauf ab.
- Alte Caches nur über `migrate.MIGRATABLE` übernehmen; ändert sich der Bildcode, Eintrag dort und im Test entfernen.
- **Tests** laufen mit einem eigenen, frischen Cache je `run_tests.py`-Lauf (nie mit dem des Rechners).

## Aufträge an andere Sitzungen

Ein Auftrag an eine andere Sitzung (Cube Escape, Roboter-Generator, eine zweite Cubegen-Sitzung) enthält nur die Aufgabe
und diese Punkte – kurz, als Liste:

```text
Art der Änderung: <Generator / Ausgabe / Werkzeug / Test / Doku> – was sich NICHT ändern darf
Prüfweg: <Tests (Stufe), echte Läufe, Unity-Check, Vergleich gegen Version X>
Erwartete Unterschiede: <keine (bytegleich) / welche Dateien, welche Felder>
Release: <ja: Version, Merge, Tag, Push / nein: nur Branch>
Bericht: Version/Name, Commits/Tag, Messwerte (vorher/nachher, Last), Testzahlen (übersprungen mit Grund), Offenes
```

## Variantensets (Variation ohne Wiederholung; Einzelheiten DEVELOPER.md 4)

Teile, die im Level nebeneinander stehen, dürfen nicht gleich aussehen: ein Set sind Varianten mit **gleichem Umriss**
und **anderem Innenleben** (`--set`, Manifest `sets`).

- **Umriss nur über Parameter** (`Param(size=True)` oder ein Name aus `OUTLINE_PARAMS`), nie ein im Builder gewürfelter
  Wert, keine Zufallsskalierung; `set_faces` am Typ (`@model(..., set_faces=...)`), `set_pins` für Formwahlen,
  `outline_ok = false` = nicht set-fähig.
- **Anschlüsse durchlaufen lassen** (Sockel, Deckel, Kern an der vollen Länge; Muster mit einer Periode, die die Länge
  teilt). **Innen variieren** über `rng` (reproduzierbar je Seed); starke Hingucker nur an manchen Teilen. Der
  einheitliche Look bleibt Sache des Stils (`--glow`, `--theme`, Anstriche).
- **Prüfen:** `--set --unique`, Reihenbild `set_<Typ>.png`; Stiltest `tools/style_test.py --row <Typ>@…:5`.

## Anstriche (`--paint`; Einzelheiten DEVELOPER.md 5)

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

## macOS-App (`app/`; Einzelheiten DEVELOPER.md 6)

SwiftUI + SceneKit, `swiftc` ohne Xcode-Projekt. **Eine Quelle:** die App startet das mitgelieferte Paket und liest alles
aus `cubegen catalog`, keine eigenen Listen; ihre Kommandozeile folgt `cubegen/gui.py` (ändert sich dort etwas, ändert
sich `GenerateSettings.arguments` mit). Neue Kategorie oder Aktion → neues Symbol (`app/make_icons.sh`). Gespeicherte
Einstellungen lesen fehlende Schlüssel mit Standardwerten. `app/notarize.sh` führt nur der Nutzer aus (nie
Zugangsdaten im Skript). **Prüfen:** `app/build.sh` und `app/test_app.sh` nach jeder Änderung an `app/` oder an
CLI-Optionen, die die App anbietet.

## Ausrichtung gerichteter Modelle

Bei Kameras und anderen gerichteten Modellen die tatsächliche Funktionsfläche prüfen,
nicht nur die Objektrotation: Blender-/Unity-Achsen, Neigung und beide Schwenkvorzeichen
gegen die exportierte Geometrie testen. Ein Anker- oder Bounds-Test ersetzt keinen
Nachweis der Blickrichtung. Beabsichtigte Korrekturen gegenüber alten Generationen
ausdrücklich dokumentieren und historische Ausgaben getrennt prüfen.

# Cubegen 0.25.0 – Quartermaster

Unveröffentlicht; Zweig `release/0.25.0`; vorherige Version [0.24.0](VERSION_0.24.0.md).
Test- und Cache-Werkzeuge (Python). Geometrie, Materialien, Texturen und Sidecars bleiben wie in 0.24.0 – nur die
Versionsangabe im Sidecar ändert sich (Nachweis unten). Lehren aus dem Roboter-Generator 1.20.2 (am selben Tag, selber
Rechner): ein Cache je Checkout macht jeden neuen Worktree kalt, absolute Pfade in Schlüsseln verhindern die
Wiederverwendung, Schreiben muss atomar sein, kein Schritt darf löschen, was andere Checkouts brauchen, alte Caches
einmal übernehmen.

## 1. Gemeinsamer Cache

**Fund.** `cubegen/cache.py` hielt `.cubegen_cache.json` je Ausgabeordner (Texturen, Icons, Kontaktbogen,
Material-Übersicht, Set-Reihen) mit absoluten Pfaden; jeder neue Ordner, jeder Worktree, jeder Unity-Check-Prüfsatz
(der seinen Ordner vorher löscht) begann kalt. Drei Gründe verhinderten jede Übernahme über Ordnergrenzen:

- der Schlüssel der Texturen enthielt den absoluten Texturordner (seine Daten trugen absolute Pfade);
- jeder Schlüssel enthielt den Hash des ganzen Generators – jede Codeänderung, auch eine Versionsnummer, machte alle
  Bilder ungültig;
- Icons, Kontaktbogen und Set-Reihen hingen am Datei-Hash der Vorschauen, und Blender stempelt Datum und Renderzeit in
  jede Vorschau (`tEXt` „Date“, „RenderTime“): gleiche Pixel, andere Bytes bei jedem Rendern.

**Umsetzung** (`cubegen/cache.py`, `cubegen/migrate.py`, `pipeline.py`):

- **Ein Speicher für den Rechner:** `~/Library/Caches/Cubegen/cache` (Linux `$XDG_CACHE_HOME/cubegen/cache`, sonst
  `~/.cache/cubegen/cache`; Windows `%LOCALAPPDATA%\Cubegen\cache`), `CUBEGEN_CACHE=<Ordner>` verlegt ihn,
  `CUBEGEN_CACHE=0` schaltet ihn ab. `objects/<ab>/<sha256>` hält Inhalte, `entries/<ab>/<Schlüssel>.json` Schlüssel →
  Rollen (`{"out": sha}` bzw. Dateinamen relativ zum Texturordner) und Daten. Haupt-Checkout, Worktrees, die macOS-App
  und `unity_check.py` teilen ihn.
- **Im Ausgabeordner nur, was an ihn gebunden ist:** `.cubegen_cache.json` Format 2 – welche Dateien dort aktuell sind,
  Pfade relativ (der Ordner darf umziehen); Format 1 wird beim Lesen umgerechnet.
- **Schlüssel nur aus Eingaben:** kein Pfad; der Code-Anteil ist `pipeline.image_code()` – der Hash von `imagemagick`,
  `textures` und allem, was sie importieren (`materials`, `seeds`; aus den Quellen ermittelt, Test). Die
  ImageMagick-Argumente der Set-Reihe, die in `pipeline.py` stehen, sind selbst Teil ihres Schlüssels (`SET_ROW_*`).
  Vorschauen gehen mit `png_content_hash` ein (alle PNG-Blöcke außer Text und Zeit).
- **Atomar:** jede Datei (Inhalt, Eintrag, Ordnerindex, kopierte Ausgabe) entsteht als Temp-Datei im Zielordner und wird
  umbenannt; Inhalte vor dem Eintrag; beim Kopieren wird der Hash geprüft – ein kaputter Inhalt wird verworfen, nie
  ausgegeben. Ein Fehler des Cache-Laufwerks bricht keinen Lauf ab (dann nur Ordnerindex).
- **Größe:** `CUBEGEN_CACHE_LIMIT_GB` (Standard 4). Ein Lauf prüft höchstens stündlich (Stempel `pruned`), ein Kürzer
  zur Zeit (`prune.lock`): erst Inhalte ohne Eintrag, dann die am längsten unbenutzten Einträge mit den Inhalten, die
  nur sie nennen – nie etwas aus den letzten zwei Stunden; ein Treffer frischt Eintrag und Inhalt auf.
- **`--force`** unverändert: verwendet nichts wieder, trägt aber ein (Ordner und Speicher).
- **Einmalige Übernahme** (`migrate.migrate_once`, Marker `migrated.json`): `output/` des Haupt-Checkouts und des
  eigenen Checkouts. Ein Eintrag zieht nur um, wenn sein alter Schlüssel sich aus dem Manifest exakt nachrechnen
  lässt (also die Eingaben bekannt sind), seine Dateien unverändert sind und der Generator denselben Bildcode hatte
  (`MIGRATABLE`: 0.24.0, Bildcode gleich – Test). Auf diesem Rechner lag nur `output/seed_707652` von 0.18.0 – anderer
  Bildcode (`materials.py` änderte sich mit 0.24.0), daher nichts übernommen; zwei 0.24.0-Ordner in einem Probe-Cache:
  42 + 7 Einträge, 0 übersprungen, der nächste 0.25-Lauf in einem neuen Ordner nahm alle 41 Bilder und die Texturen
  daraus. `python3 -m cubegen cache --migrate DIR` für weitere Ordner; `python3 -m cubegen cache` zeigt Ort und Größe.
- **Nicht im Cache, bewusst – Blender-Arbeit:** Das FBX enthält absolute Texturpfade, Zeitstempel und von Lauf zu Lauf
  andere Objekt-IDs (zwei 0.24-Läufe unterscheiden sich genauso), wäre also nur im eigenen Ordner gültig – dort
  übernimmt `build_key` die Modelle schon. Gebackene Karten passen nur zu den UVs desselben Exports (Robogen: UVs
  mitcachen), und Vorschauen kosten mit Workbench wenige Zehntelsekunden. Ein Back-Cache bräuchte einen Schlüssel aus
  Modell, UVs, Thema, Größe, Gerät und Blender-Version und die UVs im Cache – ROADMAP-Punkt „Blender-Ergebnisse
  gemeinsam cachen“.

**Messung** (Apple M5, 10 Kerne; frische Ordner, abwechselnd 0.24.0 und 0.25.0 in zwei frischen Worktrees, Last 2,4–5,2):

| Lauf | 0.24.0 (kalt, jeder Ordner) | 0.25.0 (neuer Ordner, Cache warm) |
|---|---|---|
| Bau-Kit 13 Typen × 2, `--set --textures tiled` (26 Modelle) | 4,10 / 4,25 / 4,40 s | 2,31 / 2,19 / 2,19 s |
| Anstrich `crystal`, 4 Modelle, 256 px (Backen) | 4,03 / 4,12 / 4,16 s | 3,59 / 3,71 / 3,71 s |

Der erste Lauf in einem frischen Worktree ist damit warm, sobald irgendein Checkout dieselben Bilder einmal erzeugt hat
(`shared cache: 41 image(s) copied`). Beim Anstrich bleibt das Backen in Blender (3,5 s Worker-Zeit) der Hauptteil.
Ein zweiter Lauf in denselben Ordner bleibt wie bisher bei 0,6–0,8 s (Modelle über `build_key`).

## 2. Tests ohne Auslassen (numpy)

**Fund.** Das System-Python des Macs (3.12) hat kein numpy; 13 Tests in `test_release_0180` und `test_release_0240`
übersprangen sich und mussten mit Blenders Python von Hand wiederholt werden.

**Umsetzung** (`tools/run_tests.py`): Module, die numpy importieren (aus der Quelle erkannt), bilden die Gruppe `numpy`
und laufen mit dem ersten Interpreter, der numpy hat – `$CUBEGEN_NUMPY_PYTHON`, das eigene Python, weitere `python3.x`
im PATH, dann das Python in Blender (`Blender.app/Contents/Resources/<Version>/python/bin/python3.x`, numpy 2.3.4).
Der Lauf nennt die Interpreter und listet jeden übersprungenen Test mit Grund; `CUBEGEN_UNITY_CHECK=1` und
`CUBEGEN_SLOW_TESTS=1` bleiben bewusst Opt-in. Dazu: `test_pipeline` (38 s) bekommt eine eigene Gruppe (vorher wartete
der ganze Lauf auf `rest`), und jeder Lauf nutzt einen eigenen, frischen Cache (`CUBEGEN_CACHE` temporär) – Tests
lesen und füllen nie den Cache des Rechners, ein warmer Cache verdeckt keinen kaputten Schritt.

**Messung** (frischer Worktree je Version, nacheinander, Last 4,3 bzw. 5,1):

| `python3 tools/run_tests.py --tier full` | 0.24.0 | 0.25.0 |
|---|---|---|
| Dauer | 127 s | 91 s |
| Tests | 381 | 407 (26 neu) |
| übersprungen | 15 (13 numpy, 2 Opt-in) | 2 (nur Opt-in, mit Grund) |

## 3. Ein schwerer Lauf zur Zeit

`tools/unity_check.py` startet Unity über Cube Escapes `verify.sh` und konkurrierte mit dessen eigenen Regressionen.
Seit 0.25.0 wartet er vor dem ersten Unity-Start auf die Sperre, die Cube Escape 0.59 „Turnstile“ für den ganzen Rechner
eingeführt hat (`HeavyLock`): exklusives `flock` auf `~/Library/Caches/CubeEscape/heavy-run.lock` (angelegt, wenn sie
fehlt; nie gelöscht), Halterzeile `{"pid", "what", "checkout", "since"}`, ein Wartender druckt den Halter und meldet sich
alle fünf Minuten; gehalten bis zum letzten Prüfsatz. Der Deskriptor ist nicht vererbbar (`O_CLOEXEC`) – ein
Hintergrundkind von `verify.sh` hält die Sperre nicht über das Ende hinaus (Test mit einem noch laufenden Kind). Kinder
bekommen `CE_HEAVY_HELD=1`, `CE_HEAVY_LOCK=0` überspringt (beides wie in Cube Escape). Der Bericht nennt die Wartezeit
(`heavy_lock`). Dokumentiert in `AGENTS.md` › Unity-Check.

## 4. Aufträge an andere Sitzungen

`AGENTS.md` hat eine kurze Vorlage: Art der Änderung, Prüfweg, erwartete Unterschiede, Release ja/nein, was zu berichten
ist.

## Prüfung

ABNAHME_PLATZHALTER

# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

Einstieg und globale Regeln: [Nexogen](https://github.com/ffunkfabian-hash/cubeescape-nexogen). Den vollen Wortlaut, Begründungen und
Messwerte der Abschnitte liefert `docs/DEVELOPER.md` (Teil 9 = frühere Langfassung dieser Datei); Entscheidungen des Nutzers
`docs/ENTSCHEIDUNGEN.md`; Techniken des Roboter-Generators `docs/TECHNIK.md`.

## Harter Kern

Quelle: Nexogen `templates/kern.md`, nur dort ändern; gilt auch in Cloud-Sitzungen.

1. Kein Commit direkt auf `main`.
2. Kein Force-Push, keine überschriebenen Branches oder Tags.
3. Nichts Fremdes anfassen oder löschen: andere Sitzungen, Worktrees, Stash, Haupt-Checkout.
4. Merge nach `main` nur mit Ja des Nutzers, außer Patch bis 100 Zeilen ohne Format, Vertrag, Kernpfad bei grünem `merge-check`; Tag, Release, Repo öffentlich machen immer nur mit Ja.
5. Tests nie löschen oder abschwächen, um grün zu werden.
6. Keine Zugangsdaten, kein fremdes Material, keine großen Binärdaten nach außen (öffentliche Repos, fremde APIs).
7. Formate, Verträge und IDs nur mit Migration; IDs sind ewig.
8. Nichts als fertig melden, was nicht geprüft ist.

## Projekt

- Cubegen: externer Low-Poly-Generator (Python + Blender-Batch + ImageMagick) für Modelle, FBX/GLB und Sidecar-Verträge, die
  Cube Escape importiert; dazu Blender-Add-on (`blender_addon/`), Desktop-Fenster (`cubegen/gui.py`) und macOS-App (`app/`).
- Quellen: `cubegen/` (Paket), `tests/`, `tools/`, `docs/` (Bedienung `docs/CLI.md`, Vertrag `docs/UNITY_INTEGRATION.md`).
- **Sprache:** Antworten und Docs auf Deutsch; Code, Bezeichner, Kommentare und Testnamen auf Englisch.
- Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt (gleiche Regel).

## Wahrheit und Aktualität

Version `cubegen/__init__.py`, Versionsgeschichte `CHANGELOG.md` und `docs/versions/<Hauptversion>.md`, Typen `python3 -m cubegen catalog`.
Erfahrungen stehen in `docs/DEVELOPER.md` und `docs/ENTSCHEIDUNGEN.md`; vor dem Bauen, das ein Schwesterprojekt berührt, dessen Stelle
lesen (Cube Escape `Docs/QUALITY.md`/`Docs/ARCHITECTURE.md`, Robogen/Toolgen `docs/TECHNIK.md`, cubeescape-design `docs/`).

## Befehle

- `./check` – schnelle Prüfung (`tools/run_tests.py --tier quick`, rund 30 s, ohne Blender); `./check --full` – ganze Suite
  (Blender, ImageMagick nötig). Befehle stehen in `.ce-repo.json`; `./ce` lädt die gemeinsamen Werkzeuge, `./ce docs` prüft Längen/Gliederung.
- Tests: `python3 tools/run_tests.py [--tier quick|standard|full]` (gleiches Ergebnis wie `python3 -m unittest discover -s tests`,
  nur schneller); `quick` vor Abschluss jeder Änderung, vor dem Release die volle Suite.
- Unity-Check (nur lokal): `python3 tools/unity_check.py [--quick] [--require]`; schwere Läufe nur mit `./ce lock unity|blender|gpu -- <Befehl>`.
- Erzeugen: `python3 -m cubegen generate …` (`docs/CLI.md`); App: `app/build.sh`, `app/test_app.sh`.
- Release (nur auf Wunsch): `./release` = Trockenlauf des gemeinsamen Standards, Cubegens eigener Ablauf `python3 tools/release.py`.

## Regeln

- **Passende Kollision für jedes Modell:** Kollisionsrezept passend zur tatsächlichen Geometrie/Funktion (intakt, beschädigt,
  zerstört, Parameterformen, LODs, bewegte Teile); feste Öffnungen bleiben frei, bewegte Teile tragen ihre Collider, eine
  Gesamtbox füllt keine Käfige/Durchgänge; Bounds-Prüfung ist kein Physiknachweis; alte Ausgabe nie als korrigiert erklären;
  Regressionen ergänzen, Tests nie löschen oder lockern; Unity-Prüfung nur in der Cube-Escape-Testkopie (9.1).
- **Generatorfehler** (Kollision, Geometrie, Export, Sidecar) sofort beheben und im Versionsbericht dokumentieren (9.1).
- **Leistung:** `--single-renderer` mit `asset.DECORATIVE_PARTS`; Byte-Grenzen nur für Bytes; Schritte in `timings.steps`
  benennen, Vergleiche mit `tools/perf_band.py`; in Schleifen nie linear suchen, jedes Modell einmal bauen (9.7).
- **Abwechslung:** zu wenig Varianten → kleine Details aus `cubegen/models/details.py` über `a.sub("variety")`, nie aus dem
  `rng` des Builders; Signatur nicht ändern (9.8).
- **Blender-Batch:** Cycles-Backen einmal je zusammengefügter Kopie, Bilder bytegleich, EEVEE nie `BLENDED`, `--jobs auto`,
  ImageMagick parallel nur mit `MAGICK_THREAD_LIMIT=1`; Prüfung/Modellbau bleiben reines Python (9.11).
- **Cache:** `~/Library/Caches/Cubegen/cache`; Schlüssel nur aus Eingaben, nie aus Pfaden; atomar schreiben; Tests mit
  frischem Cache (9.12).
- **Variantensets:** gleicher Umriss nur über Parameter (`Param(size=True)`/`OUTLINE_PARAMS`), Innenleben über `rng` (9.14).
- **Anstriche:** ein neutraler Back, Themen als Daten in `cubegen/paint.py`; Unity-Vertrag nur mit neuer `version` ändern;
  Themen für alle Typen prüfen (9.15). **App:** eine Quelle `cubegen catalog`, nach Änderungen `app/build.sh` + `app/test_app.sh` (9.16).
- **Ausrichtung gerichteter Modelle:** tatsächliche Funktionsfläche prüfen, nicht nur Rotation oder Bounds (9.17).
- **Texturen/ImageMagick:** reproduzierbar über `ImageMagick.run`, nie `magick` fest aufrufen (Linux hat IM 6) (9.9).
- **Actions:** ein Job je Lauf in `.github/workflows/tests.yml`; `app/**` und Doku lösen nichts aus (9.3, DEVELOPER 8).
- Aufträge an andere Sitzungen: Vorlage `~/.claude/templates/auftrag.md`; dazu Art der Änderung, Prüfweg, erwartete Unterschiede, Release ja/nein (9.13).

## Definition of Done

1. Umsetzung ohne Duplikate; Golden-Daten und Prüfsätze nur bewusst und begründet geändert.
2. `./check` grün; bei Generator-Code, Geometrie, Kollision, Texturen, Sidecar/Vertrag oder Add-on zusätzlich die volle Suite
   mit Blender und `unity_check.py --require` (Stufe 2) – sonst nur als „ungeprüft“ abschließen.
3. Betroffene `docs/` und der Versionsabschnitt aktuell; `./ce docs` ohne Fehler.
4. Abschlussbericht: was geändert, wie geprüft (Tests, Anzahl, übersprungen mit Grund), Merge-/Tag-/PR-Stand, Offenes.
   Eine Sitzung ohne Blender/Unity, die Generator-Code änderte, endet mit dem Prompt für den lokalen Test (Vorlage 9.6).

## Versionen, Branches und Worktrees

Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt. Der Weg folgt den globalen Regeln
(Nexogen `templates/regeln-details.md` › Patch-Aufträge, › Sitzungsnamen und Versionsregister):

- **Patch** (bis etwa 100 Zeilen Diff ohne Format-, Vertrags- oder Kernsystemänderung): `./ce session patch <kurzname>`, keine neue
  Minor-Version, 1–3 Zeilen im CHANGELOG-Eintrag der laufenden Version, kein Richter.
- **Version** (alles darüber): Minor +1 mit eigenem, ausgedachtem englischem Namen (cool, nie beschreibend deutsch),
  `./ce session reserve <Name> --about … --model …`, Branch `release/<Version>`, Versionsbericht, Richter vor Merge.
  Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` gemeinsam anheben (`tests/test_versions.py`).
- Bericht `docs/versions/<Haupt>.md` (Titel „# Cubegen <Haupt> – <Name>“, Abschnitt „## Cubegen <Version> – <Name>“); CHANGELOG-Eintrag
  „## <Version> „<Name>“ – unveröffentlicht“ mit 3–5 Zeilen und Link. Die letzten drei Hauptversionen in `docs/versions/`, ältere in `docs/archive/versions/`.
- Hauptordner schlank: nur `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md` und Konfiguration (keine `VERSION_*`, Notizen).
- Release nur auf Wunsch: Datum statt „unveröffentlicht“, Tests grün, `python3 tools/release.py` (Probelauf), `--apply` merged,
  taggt `v<Version>` und pusht atomar nach `origin`
  (GitHub ffunkfabian-hash/cubeescape-cubegen, `main` ist der Standard-Branch; Einzelheiten 9.4, 9.5).

## Abschluss in zwei Stufen

- **Stufe 1 „ungeprüft“** (ohne Blender/Unity, z. B. Cloud): `python3 -m unittest discover -s tests`, Branch pushen, PR mit
  „Vor dem Merge noch offen“, Versionsbericht trägt „ungeprüft: Blender-/Unity-Abnahme offen“; kein Tag. Reicht allein für
  Doku und Werkzeuge ohne Einfluss auf die Ausgabe.
- **Stufe 2 „abgenommen“** (lokal): volle Suite mit Blender und ImageMagick (`CUBEGEN_UNITY_CHECK=1 CUBEGEN_SLOW_TESTS=1
  python3 tools/run_tests.py --tier full`), echte Exporte, Sichtprüfung, `python3 tools/unity_check.py --require`, Vermerk
  „ungeprüft“ entfernen. Bleibt etwas rot oder ist eine Richtungsfrage offen: anhalten und fragen. Prompt-Vorlage: 9.6.

## Werkzeuge: ImageMagick und Blender-Plugin

`magick` (v7, `python3 -m cubegen doctor`) erzeugt Texturen und darf zum Gestalten und Prüfen dienen; reproduzierbar, über
`ImageMagick.run`. Blender-MCP: globale Regel (nur in eigener Szene, die Quelle bleibt der Generator).
`tools/unity_check.py` läuft nur lokal über Cube Escapes `verify.sh` in der Testkopie, nie auf einem Checkout, und nur unter
`./ce lock unity -- <Befehl>` (Sperre je Ressource, Details Nexogen `templates/regeln-details.md` › Schwere Läufe und Sperren). Vollständig: 9.9, DEVELOPER 7.

## Plugins und Hooks

`CLAUDE.md` importiert diese Datei. Repo-eigen: `.claude/agent-guard.json` (Profile), `.claude/hookify.ausgabe-nie-von-hand.local.md` und
`hookify.tests-vor-abschluss.local.md` (mit `git add -f`), Subagents `cg-test-runner` und `cg-doc-keeper`. Die Hookify-Warnungen
`git-nur-auf-wunsch`, `golden-daten` und `versionen-gemeinsam` entfielen (wirkungslos; das Git-Netz und `tests/test_versions.py`
tragen das). Vor einem Commit mit geänderten `*.md` warnt der Hook `precommit` (`ce_lint.py`, blockiert nie). Einzelheiten: 9.10;
globale Durchsetzung: Nexogen `templates/regeln-details.md` › Werkzeuge und Durchsetzung.

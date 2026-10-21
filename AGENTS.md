# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

Zentraler Repo-Einstieg: [Nexogen](https://github.com/ffunkfabian-hash/cubeescape-nexogen) – Repo-Links, Zuständigkeiten, Abhängigkeiten und Live-Status über `repos.json` / `./status`. Globale Regeln dort, Fachwissen und Prüfbelege hier.

**Werkzeuge:** `./ce check` · `./ce search query "Begriff"` · `./ce session topics` · `./ce codex quota|judge` · `./ce evidence clip|sheet|still|diff` · `./ce lock unity|blender|gpu -- <Befehl>` · `./ce report --since 7d`.

Kurzfassung in der Standard-Gliederung aller Repos. Den vollen Wortlaut, Begründungen und Messwerte jedes Abschnitts liefert
`docs/DEVELOPER.md` (Teil 9 = frühere Langfassung dieser Datei, 1–8 = Hintergründe). Entscheidungen des Nutzers:
`docs/ENTSCHEIDUNGEN.md`. Techniken des Roboter-Generators: `docs/TECHNIK.md`.

## Projekt

- Cubegen: externer Low-Poly-Generator (Python + Blender-Batch + ImageMagick) für Modelle, FBX/GLB und Sidecar-Verträge, die
  Cube Escape importiert; dazu Blender-Add-on (`blender_addon/`), Desktop-Fenster (`cubegen/gui.py`) und macOS-App (`app/`).
- Quellen: `cubegen/` (Paket), `tests/`, `tools/`, `docs/` (Bedienung `docs/CLI.md`, Vertrag `docs/UNITY_INTEGRATION.md`).
- **Sprache:** Antworten und Docs auf Deutsch; Code, Bezeichner, Kommentare und Testnamen auf Englisch.
- Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt (gleiche Regel).

## Wahrheit und Aktualität

1. **Code ist die Wahrheit**, dann `docs/`, dann Erinnerungen und alte Prompts; ein widersprechendes Doc im selben Zuge korrigieren.
2. Nichts Veränderliches auswendig annehmen: Version `cubegen/__init__.py` (`.ce-repo.json`), Stand `git log --oneline -15`,
   Versionsgeschichte `CHANGELOG.md` (einzige Übersicht) und `docs/versions/<Hauptversion>.md`; Typen `python3 -m cubegen catalog`.
3. Parallele Sitzungen arbeiten in eigenen Worktrees (`git worktree list`); fremde Worktrees nur lesen. Neue Befunde gehören in
   den Versionsbericht der Arbeitsversion; veröffentlichte Berichte bleiben historisch.
4. Ganze Leistung des Geräts: andere Sitzungen nur mit Cube Escapes `pause_sessions.py run -- <Befehl>` pausieren, so kurz wie
   nötig, im Bericht nennen (9.2).

## Befehle

- `./check` – schnelle Prüfung (`tools/run_tests.py --tier quick`, rund 30 s, ohne Blender); `./check --full` – ganze Suite
  (Blender, ImageMagick nötig). Befehle stehen in `.ce-repo.json`; die Werkzeuge liegen eingebettet in `tools/ce_tools/`
  (`ce_sync.py` im Plugin `ce-shared` schreibt sie, nie von Hand ändern). `python3 tools/ce_tools/ce_lint.py` prüft Längen/Gliederung.
- Tests: `python3 tools/run_tests.py [--tier quick|standard|full]` (gleiches Ergebnis wie `python3 -m unittest discover -s tests`,
  nur schneller); `quick` vor Abschluss jeder Änderung, vor dem Release die volle Suite.
- Unity-Check (nur lokal): `python3 tools/unity_check.py [--quick] [--require]`; Sperre für schwere Läufe siehe 9.9/DEVELOPER 7.
- Erzeugen: `python3 -m cubegen generate …` (`docs/CLI.md`); App: `app/build.sh`, `app/test_app.sh`.
- Release (nur auf Wunsch): `./release` = Trockenlauf des gemeinsamen Standards, Cubegens eigener Ablauf `python3 tools/release.py`.
- Vor jedem Commit mit geänderten `*.md`: Hook `precommit` des Plugins `ce-shared` ruft `ce_lint.py` und warnt (blockiert nie).
- Berichte schreibt eine Sitzung nach `report.md` im Worktree (ungetrackt, `info/exclude`); an den Auftraggeber geht eine Zeile.

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
- **GitHub Actions sparsam** (globale Regel `~/.claude/CLAUDE.md`, Repo `~/Claude/cubeescape-rules`): hier ein Job je Lauf in `.github/workflows/tests.yml`,
  `push` nur auf `main`, `app/**` und Doku lösen nichts aus (9.3, DEVELOPER 8).
- Aufträge an andere Sitzungen: Art der Änderung, Prüfweg, erwartete Unterschiede, Release ja/nein, Bericht ≤ 15 Zeilen (9.13).

## Definition of Done

1. Umsetzung ohne Duplikate; Golden-Daten und Prüfsätze nur bewusst und begründet geändert.
2. `./check` grün; bei Generator-Code, Geometrie, Kollision, Texturen, Sidecar/Vertrag oder Add-on zusätzlich die volle Suite
   mit Blender und `unity_check.py --require` (Stufe 2) – sonst nur als „ungeprüft“ abschließen.
3. Betroffene `docs/` und der Versionsabschnitt aktuell; `python3 tools/ce_tools/ce_lint.py` ohne Fehler.
4. Abschlussbericht auf Deutsch: was geändert, wie geprüft (Tests, Anzahl, übersprungen mit Grund), Merge-/Tag-/PR-Stand, Offenes.
   Eine Sitzung ohne Blender/Unity, die Generator-Code änderte, endet mit dem Prompt für den lokalen Test (Vorlage 9.6).
5. Committen, taggen, mergen und pushen nur auf Wunsch des Nutzers; nie `--force`; den Haupt-Checkout nie ungefragt ändern.

## Versionen, Branches und Worktrees

Jeder neue Branch, Worktree oder Auftrag ist eine **neue Version**: Minor +1 mit eigenem, ausgedachtem englischem Namen
(cool, nie beschreibend deutsch); eine Fortsetzung derselben Arbeit behält ihre Version. Gleich zu Beginn:

- Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` gemeinsam anheben
  (`tests/test_versions.py`).
- Branch `release/<Version>`; Bericht `docs/versions/<Haupt>.md` (Titel „# Cubegen <Haupt> – <Name>“, Abschnitt
  „## Cubegen <Version> – <Name>“; ein Patch ergänzt den Bericht seiner Hauptversion); CHANGELOG-Eintrag „## <Version> „<Name>“
  – unveröffentlicht“ mit 3–5 Zeilen und Link. Die letzten drei Hauptversionen in `docs/versions/`, ältere in `docs/archive/versions/`.
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
`ImageMagick.run`. Das Blender-MCP steuert nur das laufende Blender des Nutzers als Prüfstand (eigene Szene, nichts speichern).
`tools/unity_check.py` läuft nur lokal über Cube Escapes `verify.sh` in der Testkopie, nie auf einem Checkout, und wartet auf
`~/Library/Caches/CubeEscape/heavy-run.lock` (nie löschen, `CE_HEAVY_LOCK=0` überspringt). Vollständig: 9.9, DEVELOPER 7.

## Plugins und Hooks (Claude Code)

`CLAUDE.md` importiert diese Datei; andere Agenten befolgen dieselben Regeln aus dem Text. Plugins: `quick-gate-python` (schnelle
Prüfung, verbindlich bleibt die Suite), `code-review` vor jedem Release-Merge, `github`/`gh`, `unity` (Kollision in der
Testkopie), `hookify` (Repo-Regeln `.claude/hookify.*.local.md`, mit `git add -f`), `ce-shared` (gemeinsame Regeln, Hooks wie
`precommit`, Profile `.claude/agent-guard.json`), Blender-MCP. Hooks blockieren Unity auf einem Checkout, nacktes `git stash`,
Force-Push, Handarbeit an `output/`; sie warnen bei Commit/Merge/Tag/Push, Golden-Daten, Versionsdateien, Workflows.
Subagents `cg-test-runner` und `cg-doc-keeper`. Tabelle und Einzelheiten: 9.10.

Werkzeug-Erfahrungen: [docs/LESSONS.md](docs/LESSONS.md); die verlinkte Systemdokumentation bleibt die Langform.

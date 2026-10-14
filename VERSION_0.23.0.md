# Cubegen 0.23.0 – Wingman

*Ungeprüft: unveröffentlicht, Release auf Wunsch des Nutzers.* Release-Zweig `release/0.23.0`; vorherige Version
0.22.0 „Beacon“ (parallel auf eigenem Branch), auf `main` zuletzt [0.21.3](VERSION_0.21.3.md). Nur Agenten-Werkzeuge für Claude Code; Generator, Add-on und Ausgabe sind unverändert
(außer der Versionsnummer).

Gemeinsamer Auftrag mit Cube Escape 0.56 „Pit Crew“ und dem Roboter-Generator 1.18.0 „Ground Crew“.

## Subagents

Zwei Subagents in `.claude/agents/`, je mit eng gefassten Werkzeugen:

| Agent | Aufgabe | Werkzeuge |
|---|---|---|
| `cg-test-runner` | Testgruppen über `tools/run_tests.py` (quick/standard/full), einzelne Module, auf Wunsch `tools/unity_check.py`; berichtet Gruppen, Zahlen, Dauer, übersprungene Tests und Ursachen | Bash (nur diese Befehle und lesende), Read, Grep, Glob – kein Bearbeiten |
| `cg-doc-keeper` | Versionsbericht, Changelog, README, `docs/`, `AGENTS.md` mit dem Code abgleichen; veröffentlichte Berichte bleiben historisch | Edit nur auf vorhandene Markdown-Dateien, Bash nur lesend und `tests.test_versions` |

Was ein Agent mit seinen Werkzeugen tun darf, steht in `.claude/agent-guard.json` (Bash-Erlaubnisliste,
Schreibpfade); durchgesetzt vom Plugin `ce-shared`.

## Gemeinsames Plugin `ce-shared`

Privates Repo `ffunkfabian-hash/ce-agent-tools` (Marketplace `ce-agent-tools`, eingetragen in `.claude/settings.json`).
Vier hookify-Regeln, die bisher in mehreren Repos gepflegt wurden, kommen jetzt von dort: `git-kein-force-push`,
`git-stash-geteilt`, `unity-nie-auf-checkout` und `actions-sparsam` (aus diesem Repo), dazu `teleport-nur-frisch` und
`unity-cli-ziel-nennen`. Die alte Force-Push-Regel traf `-f` irgendwo nach dem Wort „push“ (auch `[ -f … ]` in einer
Schleife); die neue nur innerhalb eines Befehls. Repo-eigene Regeln bleiben in `.claude/`: `ausgabe-nie-von-hand`,
`git-nur-auf-wunsch`, `golden-daten`, `tests-vor-abschluss`, `versionen-gemeinsam`.

## Prüfung

- Plugin: `python3 -m unittest discover -s tests` im Plugin-Repo (jede Regel mit treffenden und nicht treffenden
  Befehlen, Gleichstand mit den ersetzten Regeln, Profile); frische Claude-Code-Sitzung mit dem Plugin: nacktes
  `git stash` blockiert, ein Subagent mit Profil darf nur seine Befehle.
- Profile dieses Repos gegen den Wächter: Testläufe, `unittest` und `unity_check.py` erlaubt, `perf_band.py`, Generator
  und Bearbeiten von Code, Golden-Daten oder `__init__.py` abgelehnt.
- `python3 -m unittest tests.test_versions`: grün.

## Vor dem Release noch offen

- Beim nächsten Öffnen in Claude Code den Marketplace `ce-agent-tools` bestätigen (oder
  `claude plugin install ce-shared@ce-agent-tools`); ohne Plugin fehlen die gemeinsamen Regeln.
- Volle Suite `python3 tools/run_tests.py --tier standard` vor dem Merge (nur Versionsnummer geändert).

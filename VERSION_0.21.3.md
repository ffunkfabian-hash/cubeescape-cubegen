# Cubegen 0.21.3 – Monolith

Korrektur vom 14. Oktober 2026, Release-Zweig `release/0.21.3`; vorherige Version [0.21.2](VERSION_0.21.2.md).
Nur der GitHub-Workflow und die Regeln; die Ausgabe ist unverändert.

## Fund

GitHub meldete am 14. Oktober: 1.802 von 2.000 Actions-Minuten verbraucht (90 %), Rücksetzung erst am 1. November.
Der Nutzer hat für Actions ein Budget von 0 $ gesetzt – ist das Kontingent leer, laufen keine Workflows mehr.
Alle Minuten stammen aus diesem Repo (Cube Escape und der Roboter-Generator haben keine Workflows).

## Ursache

- `tests.yml` lief bei **jedem Push auf jeden Branch** und zusätzlich bei jedem Pull Request – ein Push auf einen
  Branch mit offenem PR lief doppelt. Seit dem 1. Oktober: 132 Läufe (115 `push`, 17 `pull_request`), die meisten auf
  Worktree-Branches, einer allein mit 25 Läufen.
- Je Lauf **13 Jobs** (3 Python-Versionen × 4 Testgruppen + Blender). GitHub rechnet je Job und rundet auf volle
  Minuten auf; jeder Job zahlt seine Einrichtung (Python, `apt-get install imagemagick`, 15–45 s). Gemessen an fünf
  Läufen: 38–46 abgerechnete Minuten je Lauf, bei 1,5–3,5 min reiner Laufzeit je Job.
- Kein `timeout-minutes`: ein hängender Job hätte bis zu 6 h gekostet.

## Korrektur

`.github/workflows/tests.yml`:

- `push` nur auf `main`; andere Branches über ihren `pull_request`; `workflow_dispatch` (Actions › tests › Run
  workflow) für die volle Matrix auf einem beliebigen Branch.
- `concurrency` je Ref mit `cancel-in-progress`: ein neuer Push bricht den alten Lauf ab.
- `paths-ignore` für `**.md`, `docs/**`, `IDEEN.md`, `.claude/**`.
- Job `test` je Python-Version statt je Gruppe: `tools/run_tests.py --tier standard` startet alle Gruppen parallel.
  Ein PR testet Python 3.11 (Blenders Python), die volle Matrix 3.9/3.11/3.13 läuft auf `main` und auf Wunsch.
- `timeout-minutes: 20` an beiden Jobs.

Schätzung aus den gemessenen Laufzeiten: PR-Lauf etwa 11 min (1 Testjob + Blender) statt 2 × 40 min, Lauf auf `main`
etwa 25 min statt 40.

Regel global für alle Projekte in `~/.claude/CLAUDE.md` (Codex: `~/.codex/AGENTS.md` als Link); `AGENTS.md`
verweist darauf und beschreibt die Umsetzung hier („GitHub Actions sparsam“). Hook
`.claude/hookify.actions-sparsam.local.md` warnt beim Bearbeiten eines Workflows.

## Prüfung

- Workflow als YAML geprüft (Auslöser, Jobs, Matrix-Ausdruck).
- `python3 tools/run_tests.py --tier standard` lokal (der Befehl des neuen CI-Jobs).
- Der erste echte Lauf ist der PR dieses Branches (nur 3.11 + Blender); die volle Matrix nach dem Merge auf `main`.

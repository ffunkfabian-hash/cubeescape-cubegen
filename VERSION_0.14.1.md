# Cubegen 0.14.1 – Werkstattbuch

Release vom 12. Oktober 2026 (Doku und Agenten-Werkzeuge, Ausgabe unverändert). Release-Zweig `release/0.14.1`;
vorherige Version [0.14.0](VERSION_0.14.0.md). Gemeinsam mit Cube Escape 0.45.1 und Roboter-Generator 1.9.1.

## Inhalt

- **`CLAUDE.md`:** importiert `AGENTS.md`. Bisher lud Claude Code die Regeln dieses Repositorys nicht automatisch.
- **AGENTS.md › „Plugins und Hooks (Claude Code)“:** Einsatz der installierten Plugins in Cubegen.
- **Hooks (`.claude/hookify.*.local.md`):**
  - blockieren: `unity-nie-auf-checkout`, `git-stash-geteilt`, `git-kein-force-push`, `ausgabe-nie-von-hand`;
  - Sitzungsende: `tests-vor-abschluss` (Python geändert → `python3 -m unittest discover -s tests`);
  - warnen: `git-nur-auf-wunsch`, `golden-daten`, `versionen-gemeinsam`.
  Jede Regel ist mit treffenden und nicht treffenden Beispielen gegen die hookify-Logik geprüft.

Generator, Geometrie, Kollision, Materialien, Sidecar und Add-on-Logik sind unverändert; Golden-Daten unverändert.

# Cubegen 0.26.1 – Stockpile

Veröffentlicht am 15. Oktober 2026; Release-Zweig `release/0.26.1`; vorherige Version [0.26.0](VERSION_0.26.0.md).
Nur Doku (`AGENTS.md`); kein Code, keine Ausgabe geändert – nur die Versionsangabe im Sidecar.

## Anlass

`AGENTS.md` wird über `CLAUDE.md` in jeder Claude-Code-Sitzung geladen und war auf 462 Zeilen (42 KB) gewachsen, davon
vieles Hintergrund (Versionsliste, Messwerte, Begründungen), den nur wenige Aufgaben brauchen.

## Änderung

`AGENTS.md`: 462 → 281 Zeilen (42 → 23 KB). Keine Regel entfällt: Regeln und Befehle bleiben, Begründungen, Messwerte
und Einzelheiten wörtlich in `docs/CLI.md` › 16 „Entwicklerhintergrund“, in `AGENTS.md` je Abschnitt ein Verweis.

| Abschnitt in `AGENTS.md` | Hintergrund jetzt in |
|---|---|
| Versionsliste im Kollisionsabschnitt | `CHANGELOG.md`, `VERSION_<Version>.md` |
| Leistung und Grenzen | `docs/CLI.md` 16.1 |
| Blender-Batch schnell halten | 16.2 |
| Gemeinsamer Cache | 16.3 |
| Variantensets, Anstriche, macOS-App | 16.4, 16.5, 16.6 |
| Neural Engine, schwerer Lauf (Sperre) | 16.7 |
| GitHub Actions in diesem Repo | 16.8 |
| Release-Befehl (Prüfliste) | Kopf von `tools/release.py` |

## Prüfung

- `python3 tools/run_tests.py --tier quick` und `tests/test_versions.py` (siehe Abschlussmeldung); kein Blender-, kein
  Unity-Lauf nötig, da die Ausgabe unverändert bleibt.

# Cubegen 0.29.0 – Crossflow

Release-Zweig `release/0.29.0` (unveröffentlicht); vorherige Version [0.28.0](VERSION_0.28.0.md).
Nur Doku; kein Code, keine Ausgabe geändert – nur die Versionsangabe im Sidecar.

## Anlass

Der Roboter-Generator hat in `docs/TECHNIK.md` gesammelt, wie er arbeitet und was sich bewährt hat. Cubegen soll
davon profitieren, ohne dass jede Sitzung das Robogen-Repo neu liest.

## Änderung

- Neu: `docs/TECHNIK.md` – Übersichtstabelle mit Stand je Technik in Cubegen, Abschnitte je Gruppe mit Umsetzungs-
  vorschlag und Aufwand, abgehakte Checkliste, empfohlene Reihenfolge.
- `AGENTS.md` und `docs/DEVELOPER.md` verweisen darauf; `docs/CLI.md` bleibt reine Bedienungsanleitung.

## Prüfung

Siehe Abschlussmeldung: `tests/test_versions.py` und Stufe `quick`.

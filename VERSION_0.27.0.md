# Cubegen 0.27.0 – Fieldbook

Release-Zweig `release/0.27.0` (unveröffentlicht); vorherige Version [0.26.1](VERSION_0.26.1.md).
Nur Doku; kein Code, keine Ausgabe geändert – nur die Versionsangabe im Sidecar.

## Anlass

`docs/CLI.md` ist die Bedienungsanleitung; Abschnitt 16 (Entwicklerhintergrund, 16.1–16.8) gehört nicht dorthin.

## Änderung

- Neu: `docs/DEVELOPER.md` mit den Abschnitten 1–8 (Leistung und Grenzen, Blender-Batch, Cache, Variantensets,
  Anstriche, macOS-App, Neural Engine und schwerer Lauf, GitHub Actions), Text unverändert.
- `docs/CLI.md` › 16 ist ein Verweis auf das neue Doc; `AGENTS.md` verweist mit „DEVELOPER.md n“ statt „16.n“.

## Prüfung

Siehe Abschlussmeldung: `tests/test_versions.py` und Stufe `quick`.

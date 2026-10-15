# Cubegen – Entscheidungen des Nutzers

Eine Zeile je Entscheidung (neueste unten); Begründungen im Versionsbericht, falls dort ausgeführt. Neue Entscheidungen hier
ergänzen, nicht in `AGENTS.md` verstreuen.

| Datum | Entscheidung | Grund |
|---|---|---|
| 2026-10-15 | Codex-Regeln gelockert: Umsetzung durch Codex erlaubt (eigener Worktree), Prüfung Standard `gpt-6-luna`, `gpt-6.1-sol` bei „Keine Befunde“ ab etwa 300 Diff-Zeilen, `gpt-6-astra` gesperrt | Wunsch des Nutzers: Codex-Nutzung lockern, Kontingent und Arbeit sparen |
| 2026-10-15 | Keine Wartemeldungen: Sitzungen melden sich erst mit dem Ergebnis, nicht mit „ich warte noch“ | Jede Meldung kostet Kontingent (Aussage des Nutzers) |
| 2026-10-15 | Versionsberichte je Hauptversion unter `docs/versions/`, Patches als Abschnitt (umgesetzt in 0.30.0), ältere im Archiv | Wunsch des Nutzers: zu viele .md-Dateien |
| 2026-10-15 | Apple-Notarisierung der macOS-App gestrichen (`app/notarize.sh` entfernt) | Entscheidung des Nutzers |
| 2026-10-15 | Vertrag 4 ist der Standard von `--contract` | Neue Sidecars tragen Zonenkarte und Effektblock; ältere Versionen bleiben wählbar |
| 2026-10-15 | Cube Escape 0.62 liest den Cubegen-Vertrag 1–4; `--contract 2` wird nur für ältere Stände gebraucht | Stand der Zulieferung: Cube Escape 0.62 liest die Versionen 1–4; ältere Fassungen bleiben mit `--contract` wählbar |
| 2026-10-15 | Facetten- und Lochform (`--shape facet\|holes`) werden umgesetzt | Mehr Formvielfalt aus denselben Teilen, Collidern und Atlas (umgesetzt in 0.30.0) |

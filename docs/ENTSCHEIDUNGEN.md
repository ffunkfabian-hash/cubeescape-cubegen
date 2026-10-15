# Cubegen – Entscheidungen des Nutzers

Eine Zeile je Entscheidung (neueste unten); Begründungen im Versionsbericht, falls dort ausgeführt. Neue Entscheidungen hier
ergänzen, nicht in `AGENTS.md` verstreuen.

| Datum | Entscheidung | Grund |
|---|---|---|
| 2026-10-15 | Codex-Regeln gelockert: Umsetzung durch Codex erlaubt (eigener Worktree), Prüfung Standard `gpt-6-luna`, `gpt-6.1-sol` bei „Keine Befunde“ ab etwa 300 Diff-Zeilen, `gpt-6-astra` gesperrt | Kontingent schonen, Prüfungen trotzdem tief genug für große Diffs |
| 2026-10-15 | Keine Wartemeldungen: Sitzungen melden sich erst mit dem Ergebnis, nicht mit „ich warte noch“ | Weniger Rauschen im Kontext des Auftraggebers |
| 2026-10-15 | Versionsberichte je Hauptversion unter `docs/versions/`, Patches als Abschnitt (umgesetzt in 0.30.0), ältere im Archiv | Weniger Dateien, schlanker Hauptordner, weniger zu ladender Kontext |
| 2026-10-15 | Apple-Notarisierung der macOS-App gestrichen (`app/notarize.sh` entfernt) | Die App ist nur für den eigenen Rechner; kein Entwicklerkonto nötig |
| 2026-10-15 | Vertrag 4 ist der Standard von `--contract` | Neue Sidecars tragen Zonenkarte und Effektblock; ältere Versionen bleiben wählbar |
| 2026-10-15 | Cube Escape liest bis 0.62 nur Vertrag 2; bis zum Einbau von 4 wird mit `--contract 2` erzeugt und geprüft (`unity_check.py` richtet sich nach dem Spiel) | Das Spiel soll nicht von neuen Vertragsfeldern überrascht werden |
| 2026-10-15 | Facetten- und Lochform (`--shape facet\|holes`) werden umgesetzt | Mehr Formvielfalt aus denselben Teilen, Collidern und Atlas (umgesetzt in 0.30.0) |

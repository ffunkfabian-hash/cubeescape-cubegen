# Cubegen 0.20.0 – Gatekeeper

Release vom 13. Oktober 2026, Release-Zweig `release/0.20.0`; vorherige Version [0.19.1](VERSION_0.19.1.md).
Ein fester Unity-Check vor jedem Release; die Ausgabe der Modelle ist unverändert (Golden-Daten).

## Auftrag

Frage des Nutzers: „Wäre ein Unity-Test sinnvoll zu integrieren?“ – Entscheidung für Variante A: kein eigenes
Unity-Projekt in Cubegen (das wäre ein zweiter Importer, der vom Spiel abweicht) und kein Unity in GitHub Actions
(Lizenz, Laufzeit), sondern ein Werkzeug, das feste Exporte durch den **echten** Import von Cube Escape schickt.

## Warum

Bis 0.19 wurde der Unity-Import vor jedem Release von Hand geprüft – mit jeweils anderen Modellen. Er hat echte Fehler
gefunden (0.17: Material `MTP_` statt `MTA_` abgelehnt; 0.18.1: der Leuchtschlitz folgte dem Thema nicht), war aber
nicht reproduzierbar und leicht zu vergessen.

## Umsetzung

`tools/unity_check.py`:

| Prüfsatz | Inhalt | Unity-Test |
|---|---|---|
| `kit` | die 13 Bau-Kit-Typen als Sets (je 2) | Editor-Import |
| `variety` | Typen mit Zusatzdetails (je 2) | Editor-Import |
| `gameplay` | Tür, Hebel, Knopf, Ventil, Drehteller, Förderband, Tastenfeld, Lift | Editor-Import |
| `paint` | Anstrich Crystal, Anbauten an Boden/Säule/Steg, facettierte Kristalle, Modulwand | Editor-Import |
| `custom` | eigenes Thema aus `paints/custom_example.json` | Editor-Import |
| `textures` | Kacheltexturen | Editor-Import |
| `damage` | beschädigte Varianten | Editor-Import |
| `runtime` | alle Typen als GLB | Werkbank-Laufzeit |

- Je Prüfsatz ein fester `cubegen generate`-Lauf (Seed, Optionen), dann `verify.sh test` des Cube-Escape-Checkouts
  (`--ce`, `$CUBEGEN_CE_ROOT`, sonst `~/Claude/Cube Escape`) – Unity läuft nur in dessen Testkopie, die Regeln von
  Cube Escape (nie Unity auf einem Checkout) bleiben gewahrt.
- Auswertung: Ergebniszeile von `verify.sh`, Zählzeile „cubegen CLI integration: …“ aus dem Unity-Log, beim
  Laufzeitpfad `runtime-audit.json`; Bericht `output/unity_check/report.json` mit Cube-Escape-Stand.
- Ohne Cube Escape: „übersprungen“, Rückgabe 0; `--require` (Release): Rückgabe 2. Fehlschlag: Rückgabe 1, die
  Ausgabe des Tests und die Exporte bleiben stehen.
- AGENTS.md › „Abschluss in zwei Stufen“: Stufe 2 enthält `python3 tools/unity_check.py --require`; neue Merkmale
  bekommen einen eigenen Prüfsatz.

## Ergebnis (erster Lauf, Cube Escape `919ff679`)

| Prüfsatz | Modelle | Ergebnis |
|---|---|---|
| kit | 26 | 2 Gameplay, 24 statisch, 0 Fehler |
| variety | 16 | 8 Gameplay, 6 statisch, 2 Items offen (Werkzeug als Inventar-Item), 0 Fehler |
| gameplay | 8 | 8 Gameplay, 0 Fehler |
| paint | 6 | 6 statisch, 0 Fehler |
| custom | 4 | 1 Gameplay, 3 statisch, 0 Fehler |
| textures | 3 | 3 statisch, 0 Fehler |
| damage | 4 | 4 statisch, 0 Fehler |
| runtime | 187 | 179 angenommen, 8 Story-Items (`ItemPickup`, für Spielerlevel bewusst gesperrt), 0 fehlgeschlagen |

**254 Modelle, 0 Fehler, 2 min 57 s.** Gegenprobe: ein leerer Exportordner lässt den Unity-Test scheitern – das
Werkzeug meldet ihn als fehlgeschlagen (die Zeile heißt dann `Failed(Child)`; der erste Ausdruck kannte nur `Failed`).

## Prüfung

- `tests/test_release_0200.py` (7 Tests): Auswertung echter `verify.sh`-Ausgaben (bestanden, `Failed(Child)`, belegt),
  Zählzeile, Laufzeit-Audit, feste Prüfsätze mit gültigen Kommandozeilen, „übersprungen“ und `--require`; ein echter
  Unity-Lauf (`gameplay`) mit `CUBEGEN_UNITY_CHECK=1` – lokal grün.
- `tools/run_tests.py` (volle Stufe, mit Blender und ImageMagick): **329 Tests grün** (189 s), Golden-Daten unverändert.

## Grenzen

- Nur lokal (Cube Escape und Unity); kein Unity in GitHub Actions.
- Der Check prüft Import-Vertrag, Hierarchie, Materialien, Kollision, LODs und stabilen Wiederimport – kein Gameplay
  im Spiel und keine Sichtprüfung; eine Screenshot-Probe der Prüfsätze steht in der ROADMAP.

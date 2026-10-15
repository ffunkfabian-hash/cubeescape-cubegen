# Cubegen 0.27.0 – Fieldbook

Release-Zweig `release/0.27.0` (unveröffentlicht); vorherige Version [0.26.1](VERSION_0.26.1.md).
Doku und ein Werkzeug (`tools/unity_check.py`, Sperre für schwere Läufe); keine Ausgabe geändert – nur die
Versionsangabe im Sidecar.

## Anlass

`docs/CLI.md` ist die Bedienungsanleitung; Abschnitt 16 (Entwicklerhintergrund, 16.1–16.8) gehört nicht dorthin.

## Änderung

- Neu: `docs/DEVELOPER.md` mit den Abschnitten 1–8 (Leistung und Grenzen, Blender-Batch, Cache, Variantensets,
  Anstriche, macOS-App, Neural Engine und schwerer Lauf, GitHub Actions), Text unverändert.
- `docs/CLI.md` › 16 ist ein Verweis auf das neue Doc; `AGENTS.md` verweist mit „DEVELOPER.md n“ statt „16.n“.

## Prüfung

Siehe Abschlussmeldung: `tests/test_versions.py` und Stufe `quick`.

## Sperre für schwere Läufe: Anlass

Ein Codex-Review von Toolgen 0.4 „Fieldstrip“ fand im gemeinsamen Sperrprotokoll für schwere Läufe
(`~/Library/Caches/CubeEscape/heavy-run.lock`): Ein Signal erreichte nur den direkten Kindprozess, und die Sperre war
frei, sobald dieser endete – ein Enkelprozess (Blender unter `check_output.sh`, Unity unter `verify.sh`) lief ohne
Sperre weiter. In Cubegen war es noch etwas schärfer: Ein TERM für `tools/unity_check.py` beendete Python sofort, die
Sperre war frei, `verify.sh` und Unity liefen weiter. Behoben gemeinsam mit Cube Escape 0.61.3 (`Tools/heavy_lock.py`),
dem Roboter-Generator 1.20.5 und Toolgen 0.4.0 (`scripts/heavy_lock.py`).

## Sperre: Änderung

`run_in_group` in `tools/unity_check.py` ersetzt `subprocess.run` für den Unity-Schritt (`_unity`):

- der Schritt startet in einer eigenen Prozessgruppe (`start_new_session`); der Dateideskriptor der Sperre bleibt nicht
  vererbbar (`O_CLOEXEC`);
- TERM/HUP/INT für den Check gehen an die ganze Gruppe; ist sie leer, endet der Check mit 128 + Signal und gibt die
  Sperre dabei frei;
- der Schritt gilt erst als beendet, wenn die Gruppe leer ist; bleibt nach dem Ende von `verify.sh` noch etwas übrig,
  sagt der Check nach fünf Sekunden, welche Prozessgruppe die Sperre hält. Prozesse, die sich absichtlich lösen
  (Cube Escapes warmer Editor, `start_new_session`), halten sie nicht.

## Sperre: Prüfung

- `tests/test_release_0270.py`: ein Enkelprozess hält die Sperre, nachdem sein Schritt endete; ein TERM an den Check
  erreicht den Enkelprozess, bevor die Sperre frei wird.
- `python3 -m unittest discover -s tests` (Stufe 1, ohne Blender/Unity); kein Unity-Check nötig, die Prüfsätze und ihre
  Auswertung sind unverändert.

# Cubegen 0.15.0 – Stoppuhr

*ungeprüft: Unity-Abnahme offen* – Generator-Code geändert (Backen, Bilder, Parallelbetrieb); Python-Suite mit Blender
und ImageMagick grün, echte Exporte geprüft, Import in der Cube-Escape-Testkopie steht aus.
Unveröffentlicht, Branch `release/0.15.0`; vorherige Version [0.14.2](VERSION_0.14.2.md).

## Inhalt

Abgleich der Leistungserfahrungen des Roboter-Generators (1.8 „Turbo“, 1.9 „Afterburner“; Repo
`ffunkfabian-hash/cubeescape-robogen`) mit dem Cubegen-Code, ein Hinweis aus Cube Escape (Backen auf der CPU) und eine
Prüfung der ImageMagick-Nutzung. Sechs ROADMAP-Punkte umgesetzt, dazu der ältere Punkt „Schnellere Blender-Läufe“;
drei Erfahrungen entfallen. Der Kopf der ROADMAP stand noch auf 0.11.3/0.12.0 und beschreibt jetzt den aktuellen Stand.

### Befund: PNG-Dateien mit Zeitstempel (behoben)

ImageMagick schrieb in jede PNG `tIME`, `date:create` und `date:modify` – gleiche Pixel, andere Bytes bei jedem Lauf,
obwohl AGENTS.md `-define png:exclude-chunks=date,time` verlangt. Folge: Unity importierte unveränderte Texturen und
Icons neu, Datei-Hashes taugten nicht als Cache-Schlüssel. Korrektur: `imagemagick.REPRODUCIBLE` vor jedem Aufruf
(`ImageMagick.run`, `bake._magick`). Geprüft: Texturen, Icons, Kontaktbogen, Material-Übersicht und gebackene Karten
zweier Läufe bytegleich (vorher z. B. `MTA_Door_000_Albedo.png` verschieden); Blenders eigene PNG (Normal-Map) waren es
schon. Golden-Daten unberührt (sie prüfen Geometrie).

### Umgesetzt

| Punkt | Umsetzung | Messung (Apple M5, Blender 5.2.2, ImageMagick 7.1.2; Last 3–28, siehe Grenzen) |
|---|---|---|
| Zusammengefügte Kopie backen | `bake._joined_copy`: eine Cycles-Sitzung je Durchgang | CPU, 10 Modelle: 18,9 → 14,0 s; `sliding_puzzle` 3,7 → 1,1 s, `conveyor` 2,4 → 1,1 s; Modelle mit 1–3 Teilen gleich |
| Backen auf der GPU | `--bake-device auto\|cpu\|gpu`, `bake.use_device` (wie Robogen: nur GPU-Geräte) | 512 px CPU 14,0 / GPU 19,1 s; 1024 px CPU 18,7 / GPU 10,3 s; 2048 px CPU 73,0 / GPU 26,9 s; einzeln gebacken GPU 66,9 s → `auto` = GPU ab 1024 px |
| Bake-UVs reproduzierbar | gemessen, kein Umbau; Blender-Test | zwei Läufe und `--jobs 2`: alle `MTA_`-Karten pixel- bzw. bytegleich; GPU 1024 px zwei Läufe bytegleich |
| PNG bytegleich | siehe Befund | 33 Texturdateien + Übersicht zweier Läufe bytegleich |
| Cache für Bilder | `cubegen/cache.py`, `.cubegen_cache.json` (Ausgabe- und Texturordner) | Station-Kit (35 Modelle, gebacken) unverändert: 8,1 → 1,4 s |
| `--jobs` mit Arbeitspaketen | Anspruchsdatei je Modell, größtes zuerst, Ergebnis in Spec-Reihenfolge | Station-Kit `--jobs 3`: 47–49 s (vorher 48–51 s) |
| Zeitbudget je Stufe | `manifest.json` › `timings`, `STAGE_BUDGETS`, Warnung im Log | Budgets ≈ dreifache Messung |
| Teststufen | `tools/run_tests.py --tier quick\|standard\|full`, `$CUBEGEN_SKIP_BLENDER=1`, vierte Gruppe `params` (auch CI) | quick 26 s, Suite ohne Blender sequenziell 207 s |

**Gemessen und verworfen:** `-t Kerne/Jobs` für die Blender-Worker (Robogen-Regel für Python-lastige Worker) – Cycles
backt auf der CPU echt parallel, das Station-Kit wurde langsamer (abwechselnd gemessen: 49,8 / 54,1 s mit Grenze,
46,7 / 49,1 s ohne). `MAGICK_THREAD_LIMIT=1` bleibt für die parallelen Worker; für Texturen, Icons und Kontaktbogen
(nacheinander im Hauptprozess) ohne Wirkung (4,8 s mit und ohne).

**Ausgabeänderung:** Das gemeinsame Backen ändert das Rauschen der Umgebungsverdeckung minimal (Station-Kit,
105 Karten alt gegen neu: RMSE im Mittel 0,14 %, höchstens 2,5 % beim Portalrahmen, im Differenzbild nur feines
Rauschen). Normal-Maps, Geometrie, Kollision, Sidecar und Golden-Daten unverändert. Neu im Manifest: `timings`,
je gebackenem Modell `bake_device`; in `config` `bake_device`.

**Entfallen:** Paletten aus Gewichtskarten (Cubegen backt keine Paletten), EEVEE-`BLENDED` (kein transparentes
Material), `foreach_get` als `float32` (nicht verwendet) – in AGENTS.md als Regeln für künftige Fälle vermerkt.

## Prüfung

- `python3 -m unittest discover -s tests`: **273 Tests grün**, keiner übersprungen (Blender 5.2.2, ImageMagick 7.1.2),
  287 s, am 12. Oktober 2026. `tools/run_tests.py --tier quick`: grün, 26 s.
- Neu: `tests/test_release_0150.py` (11 Tests: bytegleiche PNG ohne Zeitstempel, Cache inklusive veränderter Datei und
  `--force`, Zeitbericht und Budgets, Bake-Gerät, Arbeitspakete, Teststufen, gebackene Karten über zwei Läufe und
  `--jobs 2` bytegleich).
- Echte Läufe: Station-Kit gebacken mit `--jobs 3` (35 FBX, Vertragsprüfung im Lauf grün), Wiederholung ohne Änderung,
  1024-px-GPU-Back zweimal.

## Grenzen

- Zeiten unter wechselnder Last gemessen (zwei Unity-Prozesse anderer Sitzungen, Last bis 28); Vergleiche deshalb
  abwechselnd gefahren. Als Größenordnung verwenden.
- GPU-Schwelle 1024 px nur auf Apple M5 (Metal) gemessen; andere GPUs können anders liegen (`--bake-device`).
- Unity-Import der neu gebackenen Texturen in der Cube-Escape-Testkopie steht aus (Stufe 2).

## Lokaler Test (Stufe 2)

```text
Abnahme und Release nach Cubegen-AGENTS.md (Stufe 2):
Branch: release/0.15.0 · Version: 0.15.0 „Stoppuhr“ · PR: noch keiner (Branch nicht gepusht)
Tag: v0.15.0 · Release-Branch: release/0.15.0 · Umfang: Abnahme und Release
Vor dem Merge noch offen:
- Unity-Import in der Cube-Escape-Testkopie: Station-Kit mit --textures baked (512 px, CPU) und eine Auswahl mit --texture-size 1024 (GPU) neu exportieren, importieren, Materialien/Texturen und Wiederimport ohne Fehler
- Sichtprüfung: Kontaktbogen und gebackene Karten alt gegen neu (Rauschen der Umgebungsverdeckung minimal anders)
- Zweiter Export ohne Änderung: Unity darf Texturen und Icons nicht neu importieren (bytegleiche PNG)
Abnahme: eigener Worktree; volle Python-Suite mit Blender und ImageMagick ohne übersprungene Tests, echte Exporte der
geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Bericht VERSION_0.15.0.md auf
Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```

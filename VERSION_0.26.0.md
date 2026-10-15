# Cubegen 0.26.0 – Stockpile

Veröffentlicht am 15. Oktober 2026; Release-Zweig `release/0.26.0`; vorherige Version [0.25.0](VERSION_0.25.0.md).
Cache, Werkzeuge und CI (Python). Geometrie, Materialien, Texturen und Sidecars bleiben wie in 0.25.0 – nur die
Versionsangabe im Sidecar ändert sich; Nachweis unten (alle zehn Prüfsätze des Unity-Checks gegen 0.25.0).

## 1. Blender-Ergebnisse im gemeinsamen Cache

**Fund.** 0.25.0 teilte die ImageMagick-Arbeit zwischen Ordnern und Checkouts; Export, Backen und Vorschau liefen in
jedem neuen Ordner neu – beim Anstrich ist das Backen fast der ganze Lauf (sechs Modelle, 512 px: 22 s Worker-Zeit
von 14 s Wanduhr). ROADMAP-Punkt aus 0.25.0. Was die Wiederverwendung verhinderte, nachgemessen an zwei Exporten
derselben Modelle in zwei Ordner (Anstrich, FBX + GLB + OBJ):

- **FBX:** absolute Texturpfade in `Texture.FileName`, `Video.Filename` und der Eigenschaft `Path` des Videos; dazu
  Zeitstempel (`CreationTimeStamp`) und Objekt-IDs, die Blender bei jedem Export neu zieht (auch zweimal in denselben
  Ordner). `RelativeFilename` ist relativ zum FBX, `DocumentUrl` ein fester Platzhalter.
- **GLB, OBJ, MTL, alle gebackenen Karten** (`MTA_`, `MTP_`, `MTN_`, `Neutral/`): bytegleich in beiden Ordnern.
- **Vorschauen:** pixelgleich, nur Blenders Renderstempel (Datum, Renderzeit) unterscheiden die Bytes.
- **UVs:** Smart UV Project ist auf diesem Rechner deterministisch – auch mit anderen Arbeitspaketen
  (`test_release_0150`, seit 0.15.0); der Cache verlässt sich trotzdem nicht darauf (unten).

Was Cube Escape aus dem FBX liest: Hierarchie, Pivots, Meshes und Materialnamen; die Texturen setzt der Import aus
dem Sidecar (`textures.manifest`, `textures.baked`, `textures.neutral`, relativ zum Modellordner). Ob die Pfade im FBX
umgeschrieben sind, darf also keinen Unterschied machen – geprüft mit dem vollen Unity-Check (unten), dessen
Prüfsätze diesmal fast ganz aus dem Cache kamen.

**Umsetzung** (`cubegen/modelcache.py`, `cubegen/fbxpath.py`, `bake.py`, `stylebake.py`, `blender_worker.py`,
`pipeline.py`):

- **Ein Modell ist eine Einheit:** Export(e) mit Nebendateien (MTL eines OBJ, Puffer und Bilder eines getrennten
  glTF), gebackene oder angestrichene Karten und die Vorschau – alles aus demselben Blender-Lauf, die Karten liegen also
  immer auf den UVs des gecachten FBX. Einträge im gemeinsamen Speicher von 0.25.0 (`Store`, Schritt `model`), Rollen
  statt Pfaden (`models/…`, `textures/…`, `previews/…`).
- **Schlüssel = jede Eingabe des Workers:** der Auftrag, wie der Worker ihn bekommt (Formate, Texturmodus, Größe, Set,
  Palette, Anstrich samt Daten eines eigenen Themas, Back-Gerät, Render-Engine und Kamera) und die Spec des Modells
  (Typ, Seed, Name, Parameter, Stil, LOD, Set, Vertrags-Rückweg …); Ordner werden zu Rollen, der Texturordner zählt
  relativ zum Modellordner (`RelativeFilename`, `map_*` im MTL), die Kacheltexturen über ihren eigenen Schlüssel
  (`texture_key`). Dazu der Code (`model_code`: das ganze Paket samt Datendateien ohne die Versionszeile – der Worker
  importiert 70 von 73 Modulen, die Importhülle aus den Quellen zu lesen kostete 0,4 s je Lauf, das Hashen aller
  Dateien 5 ms), Blender- und ImageMagick-Version und die Plattform (CPU- und GPU-Backen rauschen anders). Bleibt nach
  dem Ersetzen ein absoluter Pfad übrig, bekommt das Modell keinen Schlüssel und wird wie bisher gebaut. Neue Felder
  des Auftrags sind damit automatisch Teil des Schlüssels.
- **Nur das FBX wird umgeschrieben:** `fbxpath` liest den Knotenbaum eines binären FBX (32- und 64-Bit-Köpfe) und
  schreibt ihn neu – Endoffsets, Längen und die Fußpolsterung, wie Blenders Exporter sie setzt. Erst wenn das
  unveränderte Schreiben dieselben Bytes ergibt, wird umgeschrieben (sonst bleibt das Modell draußen). Der Cache hält
  das FBX kanonisch (`<cubegen:textures>/MTP_….png`), ein Treffer setzt den Texturordner des neuen Laufs ein; jedes
  andere Byte bleibt, wie Blender es schrieb. Vor dem Eintragen wird geprüft, dass kein Ordner des Laufs (auch als
  aufgelöster Pfad, `/tmp` → `/private/tmp`) mehr in der Datei steht – sonst kein Eintrag.
- **Backen allein** (Schritt `bake`): Verfehlt die Einheit, weil sich nur etwas *nach* dem Backen geändert hat
  (Formate, Vorschau-Kamera, ein eigenes Thema mit gleichem Leuchtton), kommen die Karten des Backens samt den
  **Atlas-UVs** aus dem Cache (`bake.read_uvs`: float32 je Schleife und Objekt). Der Worker setzt die UVs statt Smart UV
  Project (`apply_uvs`, mit derselben Edit-Mode-Runde und denselben Cycles-Einstellungen, die ein Backen hinterlässt)
  und überspringt Cycles; Anstrich zusammensetzen, Export und Vorschau laufen wie sonst. Passen die UVs nicht zu den
  Objekten (Anzahl Schleifen, Namen), wird normal gebacken. Der Schlüssel enthält die Spec (der Leuchtton steht in
  jedem Backen dort, wo Leuchtflächen liegen), Texturgröße, Gerät, Render-Engine (die Vorschau-Szene steht vor dem
  ersten Backen) und Kacheltexturen, nicht Formate, Kamera oder Anstrich.
- **Ablauf:** erst der eigene Ordner (`build_key`, wie bisher), dann Einheiten, dann Backen; Gebautes wird danach
  eingetragen (`--force`: baut alles, trägt aber ein). Neue Schritte in `timings`: Stufe `cache`, Schritt
  `model_cache`. Ein voller Treffer startet Blender nur für die Übersichts-`.blend` (`--no-blend`: gar nicht); das
  Manifest nennt dieselbe Render-Engine wie ein gebauter Lauf.
- **Nicht im Cache:** die Übersichts-`.blend` (absolute Bildpfade, je Lauf ein Blender-Start von etwa 0,6 s) und die
  Proben vor dem ersten Blender-Lauf (`blender --version` 0,25 s, Engine-Probe 0,7 s) – beide sind Eingaben des
  Schlüssels (Version, aufgelöste Engine) und bleiben ehrlich gemessen.

**Messung** (Apple M5, 10 Kerne, Blender 5.2.2 LTS; Anstrich `crystal`, sechs Modelle `floor_tile, pillar, catwalk,
rock, wall, crate`, 512 px, jeder Lauf in einen neuen Ordner; Last 1 min 2,8–9,6 – überwiegend die eigenen
Cycles-Läufe, der Unity-Editor des Nutzers lief nebenher):

| Lauf | Wanduhr | CPU (mit Blender) |
|---|---|---|
| 0.25.0, frischer Worktree, vier Läufe | 14,43 / 15,08 / 13,48 / 13,38 s | 89–94 s |
| 0.26.0, erster Lauf überhaupt (Einheiten werden eingetragen) | 13,40 s | 96 s |
| 0.26.0, zweiter frischer Worktree, vier Läufe | 1,89 / 1,92 / 2,00 / 1,82 s | 1,7–1,8 s |

Der Rest von 1,9 s: Planen 1,0 s (Blender-Version, Engine-Probe, Vertrag), Cache 0,05–0,07 s, Blender für die
`.blend` 0,6–0,7 s. Eintragen kostet im ersten Lauf 0,08 s. Größe: sechs Modelle mit Anstrich 512 px ≈ 13 MB (Karten,
Neutral-Rohkarten, FBX, Vorschauen); der ganze gemeinsame Cache nach allen Messungen und Prüfsätzen 68 MB, davon
51 MB Modelle (332 Einheiten) und 5 MB Backen (Grenze 4 GB).

## 2. GitHub Actions mit einem Job je Lauf

**Fund** (`gh api …/actions/runs/<id>/jobs`): ein Push auf `main` startete vier Jobs (`test` 3.9/3.11/3.13 mit Stufe
`standard`, `blender`), 2:30–6:00 min je Job; abgerechnet (je Job aufgerundet) 18, 18, 19 und 17 min für die letzten
vier Releases. Ein PR startete zwei Jobs (3.11 und Blender), etwa 8 min. Im Oktober 22 Pushes auf `main` in zehn Tagen.

**Umsetzung** (`.github/workflows/tests.yml`, Regeln aus `~/.claude/CLAUDE.md`): `push` nur auf `main`, PRs über
`pull_request`, „Run workflow“; `concurrency` mit Abbruch; `paths-ignore` für Doku, `.claude/**` und neu `app/**`
(die App wird nur lokal geprüft); Zeitgrenze je Job; Blender aus dem Actions-Cache.

- **Push auf `main`:** nur der Job `quick` (Stufe `quick`, Python 3.11). Auf `main` kommt ein Release erst nach der
  vollen lokalen Suite mit Blender und dem Unity-Check (Stufe 2), der Push-Lauf ist die Rauchprobe.
- **PR:** ein Job `full` – die ganze Suite mit Blender (`run_tests.py --tier full`, Gruppen parallel, numpy-Gruppe mit
  Blenders Python) statt zwei Jobs mit doppelter Einrichtung.
- **„Run workflow“:** `quick`, `standard` (wie ein PR) oder `full` (dazu 3.9 und 3.13, Stufe `standard`, für die
  bitgleichen Modelle über Python-Versionen).

**Schätzung** (Minuten je Lauf × Läufe im Monat; ~60 Pushes auf `main` beim heutigen Takt, ~10 PRs):

| | vorher (0.21.3–0.25.0) | nachher (0.26.0) |
|---|---|---|
| Push auf `main` | 4 Jobs, 17–19 min × 60 ≈ 1.080 min | 1 Job, ≈ 2 min × 60 ≈ 120 min |
| PR | 2 Jobs, ≈ 8 min × 10 ≈ 80 min | 1 Job, ≈ 7 min × 10 ≈ 70 min |
| Monat | ≈ 1.160 min (58 % von 2.000) | ≈ 190 min (10 %) |


## 3. Release-Befehl

`tools/release.py` macht die Schritte aus AGENTS.md › „Versionen, Branches und Worktrees“: Probelauf ohne
`--apply` (alle Prüfungen und der Plan, nichts ändert sich), mit `--apply` Merge, Tag und Push. Er läuft im
Release-Worktree (oder mit `--branch` überall im Repo) und prüft den Release-Zweig, wie er committet ist:

- Version an allen drei Stellen, Zweig `release/<Version>`, Changelog-Eintrag mit Datum, `VERSION_<Version>.md` mit
  Titel und ohne „ungeprüft“;
- Release-Worktree und Haupt-Checkout sauber (den Haupt-Checkout findet er über `git worktree list`, er wechselt nie
  dessen Zweig), `main` = `origin/main` nach `git fetch`, `main` im Release-Zweig enthalten (kein Konflikt beim Merge),
  Tag frei (lokal und auf GitHub), ein vorhandener Release-Zweig auf GitHub im lokalen enthalten (kein Force);
- in allem, was der Push sendet (`git rev-list --objects` gegen `origin/main`): keine Datei über 100 MB (über 50 MB ein
  Hinweis) und nichts, was nach Zugangsdaten aussieht (private Schlüssel, GitHub-/AWS-/Slack-/OpenAI-/Anthropic-/
  Google-Schlüssel, Passwörter in URLs, Dateien wie `.env`, `id_rsa`, `*.pem`) – gemeldet mit Datei und Zeile, nie mit
  dem Wert. Der ganze heutige Baum (1.116 Dateien) ergibt keinen Fund.

Dann `git merge --no-ff release/<Version> -m "Cubegen <Version> – Release übernehmen"` (`--trailer` hängt Zeilen wie
`Co-Authored-By` an), `git tag -a v<Version> -m "Cubegen <Version> – <Name>"` und `git push --atomic origin main
release/<Version> v<Version>` – alle drei oder keiner, nie mit Force; danach die Links. Dieses Release lief damit.
Außerdem steht in `AGENTS.md`, `README.md`, `docs/CLI.md` und `tools/install.sh` der neue Repo-Name
`cubeescape-cubegen` statt `lowpoly_cubeescape_model_generatior` (alte Versionsberichte bleiben historisch).

## Prüfung

Lokal auf dem Mac (Apple M5, Blender 5.2.2 LTS, ImageMagick 7.1.2, Python 3.12; numpy-Gruppe Blenders Python 3.13),
Cube Escape-Checkout `~/Claude/Cube Escape`:

- **Volle Suite** `CUBEGEN_UNITY_CHECK=1 CUBEGEN_SLOW_TESTS=1 python3 tools/run_tests.py --tier full`: **442 Tests grün,
  0 übersprungen** (models 41, quality 12, params 38, pipeline 13, numpy 34, rest 304), 462 s samt echtem Unity-Lauf
  und 2048-px-Kiste (Unity-Editor des Nutzers lief nebenher). Golden- und Digest-Tests unverändert grün.
- **Neue Tests** (`tests/test_release_0260.py`, 34): FBX-Umschreiben an einem echten Blender-FBX (`tests/fixtures/
  crate_tiled.fbx`, Pfade neutral) – unverändert bytegleich, nur ganze Pfadteile, 64-Bit-Köpfe, unbekanntes Layout
  abgelehnt, Vergleichsform ohne IDs und Zeit; Schlüssel (gleich in anderem Ordner, jede Eingabe ändert ihn, Ordner
  außerhalb → kein Schlüssel, Backen ohne Formate/Kamera/Anstrich, Code ohne Versionszeile); Einheit und Backen in
  einen anderen Ordner mit anderem Aufbau (FBX umgeschrieben, nichts im Speicher nennt einen Ordner), kaputter Inhalt,
  Verweigern; echte Läufe mit Blender (zweiter Ordner gleich einem frischen Export, zweiter Checkout ohne
  Blender-Start, `--force`, andere Eingabe verfehlt, Backen für andere Formate, eigenes Thema und `--textures baked`
  jeweils gleich einem ungecachten Lauf); Workflow-Regeln; Release-Befehl an Wegwerf-Repos (Probelauf ändert nichts,
  `--apply` mit `--no-ff`, annotiertem Tag und atomarem Push, aus dem Haupt-Checkout, unfertige Version, Versionen
  ungleich, offene Änderungen, `main` hinter/vor `origin`, große Datei und Zugangsdaten – auch in der Historie);
  alter Repo-Name weg.
- `test_release_0150` (Atlas bytegleich über Läufe und Arbeitspakete) läuft jetzt mit `CUBEGEN_CACHE=0` – sonst
  kämen die Läufe b und c aus dem Cache und der Test prüfte nicht mehr Smart UV Project.
- **Gleich zu 0.25.0:** alle zehn Prüfsätze des Unity-Checks (270 Modelle: Bau-Kit-Sets, Zusatzdetails, Gameplay,
  Anstrich, eigenes Thema, Kacheln, Schäden, ein Renderer mit LODs, alle Typen als GLB, Anstrich neutral mit Vertrag 3)
  mit 0.25.0, mit 0.26.0 frisch gebaut und mit 0.26.0 aus dem Cache: 20 von 20 Vergleichen gleich – GLB, OBJ, MTL,
  alle Karten und Texturen **bytegleich**, Vorschauen **pixelgleich** (gleicher Bildinhalt, nur Renderstempel), FBX
  knotenweise gleich bis auf Zeitstempel, Objekt-IDs und den Ausgabeordner in den Texturpfaden, Sidecars bis auf
  `"generator"` gleich, Manifeste bis auf Version, Zeiten und Code-Hash gleich. Ebenso der Messlauf oben (0.25.0 gegen
  0.26.0 frisch und aus dem Cache).
- **Echte Exporte zweimal:** Messlauf oben – der erste Lauf in einem zweiten frischen Worktree kam ganz aus dem Cache
  (`shared cache: 6 model(s) copied (export, bake, preview)`, Blender nur für die `.blend`).
- **Unity-Check** `python3 tools/unity_check.py --require` (alle Prüfsätze) gegen Cube Escape `a228d7d3` (0.59
  „Turnstile“, Vertrag Version 2): **bestanden, 10 Prüfsätze, 270 Modelle**, 0 abgelehnt / 0 Fehler; Laufzeitpfad 187
  GLB: 179 angenommen, 8 mit nicht unterstütztem Verhalten, 0 fehlgeschlagen (wie 0.22–0.25); `neutral` mit Vertrag 3
  lehnt der Import alle 8 wie erwartet ab, mit Version 2 nimmt er sie an. Die Prüfsätze kamen bis auf `neutral` mit
  Vertrag 2 aus dem gemeinsamen Cache (Erzeugen 1,1–1,4 s je Prüfsatz ohne Anstrich-Vergleichsbilder) – der echte
  Import nimmt die umgeschriebenen FBX also genauso an. Sperre frei (0 s gewartet), 3:10 min.
- **CI:** lokal geprüft (Workflow-Test, Stufen `quick` und `full` laufen hier grün); der Push des Releases auf `main`
  startet nur den Job `quick`.
- Keine neuen Typen, keine Änderung an Geometrie oder Kollision – keine eigene Physikprüfung.

## Offen

- Ein voller Treffer startet Blender noch für die `.blend` und zwei Proben (zusammen etwa 1,6 von 1,9 s). Die
  Engine-Probe ließe sich je Blender-Programm merken – nur sinnvoll, wenn sie auf demselben Rechner nie anders ausfällt
  (headless mit oder ohne OpenGL); bewusst offen gelassen, die aufgelöste Engine ist Teil des Schlüssels.
- Ein Anstrich mit anderem Leuchtton verfehlt auch den Back-Cache (das Backen schreibt den Leuchtton in die Atlas-Bereiche
  der Leuchtflächen). Nur bei gleichem Leuchtton – eigene Themen auf derselben Basis, Formate, Vorschau – spart er.
- Auf GitHub laufen die neuen Jobs erst mit dem nächsten Push auf `main` (`quick`) bzw. dem nächsten PR oder „Run
  workflow“ (`full`); ein eigener Probelauf nur zum Ausprobieren hätte Minuten gekostet. Die Schätzung oben ist an
  diesen ersten Läufen nachzumessen (`gh run list`, `gh api …/runs/<id>/jobs`).

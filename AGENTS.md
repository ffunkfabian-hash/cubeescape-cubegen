# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

## Passende Kollision für jedes Modell

Jedes neue oder geänderte Modell braucht ein zur tatsächlichen Geometrie und Funktion
passendes Kollisionsrezept. Das gilt für Gameplay und statische Dekoration, intakte,
beschädigte und zerstörte Varianten, Parameterformen, LODs und bewegte Unterteile.
Ein erfolgreicher Export oder eine reine Prüfung der Bounds ist kein Physiknachweis.

- Feste Öffnungen und Zwischenräume bleiben frei. Eine Gesamtbox oder konvexe Hülle
  darf Käfige, Rohre, Tresore, Durchgänge oder Trümmerzwischenräume nicht auffüllen.
  Ein einfacher Box-/Hull-Collider ist nur für eine tatsächlich passende solide Form geeignet.
- Bewegte Teile und ihre Kinder tragen ihre Collider mit; Meshes unter bewegten
  Rigidbodies sind konvex. Feste komplexe Geometrie erhält genaue nichtkonvexe Meshes
  oder passend zerlegte einfache Shapes. Eine Schadenszone ersetzt keinen festen Collider.
- Rein visuelle Teile und Pickups werden ausdrücklich passend behandelt; Pickups
  behalten ihre Interaktionstrigger. Sichtbarkeit allein verlangt keine feste Kollision.
- Eigene vorhandene Shapes vor Änderungen prüfen. Generation 3 ergänzt fehlende
  Gameplay-/statische Shapes; ältere Generationen sind historische Ausgabe. Erhaltene
  alte Ausgabe niemals als korrigiert deklarieren. Alte fehlerhafte Exporte müssen
  mit dem aktuellen Rezept neu erzeugt und in Unity erneut geprüft werden.
- Dünne feste Teile (z. B. Stegstützen) zusätzlich durch tatsächliche Innenpunkte und
  exportierte Unity-Physik prüfen; Mindestvolumen-/Dickenfilter allein sind kein vollständiger Nachweis.
- Fehlende Kollisionsdeckung und blockierte Freiräume sind Fehler. Qualitätsprüfung
  muss den tatsächlichen Unity-Import abbilden, keine ersatzweise angenommene Hülle.
- Regressionen für Modelle, Seeds, Parameter und Zustände ergänzen. Bestehende Tests
  nicht löschen oder Importprüfungen lockern. Bei bewusster Änderung Golden-Daten
  gezielt aktualisieren und unveränderte Geometrie separat belegen.
- Python-Suite und echte FBX in der isolierten Cube-Escape-Testkopie prüfen:
  Geometrie-/Shape-Zuordnung, freie Öffnungen, bewegte Collider, Reimport und passende
  Laufzeit-/Physiktests. Kein Unity-Start auf einem Checkout.

Belegte Generatorfehler (Kollision, Geometrie, Export, Sidecar-/Metadaten) sofort beheben. Neue Befunde
gehören in den Versionsbericht der laufenden Arbeitsversion `VERSION_<Version>.md` (siehe „Versionen,
Branches und Worktrees“). 0.11.0 übernimmt das frühere 0.10.6-Vorhaben und besitzt den Bericht
`VERSION_0.11.0.md`. 0.12.0 (10. Oktober 2026) veröffentlicht die Arbeitsstände 0.11.1–0.11.4
(`VERSION_0.11.2.md` bis `VERSION_0.11.4.md`, Release-Bericht `VERSION_0.12.0.md`). 0.13.0 „Patina“ (10. Oktober 2026,
`VERSION_0.13.0.md`) ist veröffentlicht; die nächste Version ist 0.14.0.
Veröffentlichte Berichte bleiben historisch.
Fund, Ursache, Korrektur, geprüfte Varianten und verbleibende Grenzen festhalten.
Diese Regel gilt auch in allen späteren Integrationsphasen.

## Versionen, Branches und Worktrees

Jeder neue Branch, Worktree oder Arbeitsauftrag ist eine **neue Version**: Minor +1 (0.12.0 → 0.13.0 → 0.14.0 …)
mit einem eigenen, ausgedachten Namen (kurz, sprechend, z. B. „Eisenwald“). Setzt eine Sitzung dieselbe Arbeit in
einem Folge-Worktree fort, behält sie deren Version. Gleich zu Beginn, nicht erst beim Release:

- Version in `pyproject.toml`, `cubegen/__init__.py` und `blender_addon/cubegen_addon/__init__.py` (`bl_info`)
  gemeinsam anheben – `tests/test_versions.py` prüft die Gleichheit samt gebautem Add-on-ZIP.
- Branch `release/<Version>`, Bericht `VERSION_<Version>.md` mit Titel „Cubegen <Version> – <Name>“ und
  Changelog-Eintrag „## <Version> „<Name>“ – unveröffentlicht“.
- Release (nur auf Wunsch des Nutzers): Datum statt „unveröffentlicht“, Tests grün, `git merge --no-ff` in `main`
  („Cubegen <Version> – Release übernehmen“), Tag `v<Version>`, Push von `main`, `release/<Version>` und Tag.
  `main` ist der Standard-Branch auf GitHub (ffunkfabian-hash/lowpoly_cubeescape_model_generatior).

Generatorversionen sind keine Cube-Escape-Versionen; beide Projekte zählen getrennt nach derselben Regel.

## Abschluss in zwei Stufen

Sitzungen ohne Blender und Unity (z. B. in der Cloud, claude.ai/code) dürfen meist nur ihren eigenen Branch pushen –
keine Tags, kein `main`, keine Release-Branches – und können keine echten Exporte und keinen Unity-Import prüfen.

- **Stufe 1 „ungeprüft“** (ohne Blender/Unity): `python3 -m unittest discover -s tests` (Blender-/ImageMagick-Tests
  werden ohne die Werkzeuge übersprungen – das im Bericht nennen), bei Bedarf `--no-blender`-Erzeugung; Branch pushen,
  PR mit Abschnitt „Vor dem Merge noch offen“; der Versionsbericht `VERSION_<Version>.md` trägt oben
  *„ungeprüft: Blender-/Unity-Abnahme offen“*. Danach darf der Nutzer den PR auf GitHub mergen; kein Tag, kein Release.
- Stufe 1 reicht als Abschluss **nur für Doku oder Werkzeuge ohne Einfluss auf die Ausgabe**. Bei Generator-Code,
  Geometrie, Kollision, Materialien/Texturen, Sidecar/Vertrag oder Add-on ist sie ein Vorab-Stand: Der Bericht endet
  **immer** mit dem ausgefüllten Prompt für den lokalen Test (Vorlage unten) als kopierbarem Codeblock.
- **Stufe 2 „abgenommen“** (lokal): volle Python-Suite **mit** Blender und ImageMagick (keine übersprungenen Tests),
  echte Exporte der geänderten Typen, Sichtprüfung (Kontaktbogen, Blender-Plugin), Import und Physik in der
  Cube-Escape-Testkopie (Skill `ce-cubegen` dort), Vermerk „ungeprüft“ entfernen; danach Release wie oben.
  Bleibt etwas rot oder ist eine Richtungsfrage offen: anhalten und fragen, nicht releasen.

Vorlage – wörtlich übernehmen, `<…>` durch echte Werte ersetzen („Umfang: nur Abnahme“ für eine Prüfung ohne Release):

```text
Abnahme und Release nach Cubegen-AGENTS.md (Stufe 2):
Branch: <branch> · Version: <0.x.0 „Name“> · PR: <PR-Link>
Tag: <v0.x.0> · Release-Branch: <release/0.x.0> · Umfang: Abnahme und Release (oder: nur Abnahme)
Vor dem Merge noch offen:
- <offener Punkt aus dem PR, z. B. Exporte von …, Unity-Import in der Testkopie, Kontaktbogen ansehen>
Abnahme: eigener Worktree; volle Python-Suite mit Blender und ImageMagick ohne übersprungene Tests, echte Exporte der
geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Bericht VERSION_<Version>.md auf
Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```

## Werkzeuge: ImageMagick und Blender-Plugin

- **ImageMagick** (`magick`, Version 7; `python3 -m cubegen doctor` zeigt, ob es gefunden wird) erzeugt die Texturen
  (`--textures tiled|baked|palette`) und ist ausdrücklich auch zum **Gestalten** erwünscht: Symbole, Schilder,
  Leucht-Masken, Paletten, Kontaktbögen; zum Prüfen von Vorschauen zuschneiden, vergrößern, `montage`,
  `compare -metric AE`. Bilder reproduzierbar erzeugen (feste Seeds, `-define png:exclude-chunks=date,time`).
- **Texturen sind erlaubt** (seit Cube Escape 0.35): Standard bleibt `none` (einfarbige `M_…`-Materialien); die Option
  gibt es in CLI, Blender-Add-on, Desktop-Fenster und in der Cube-Escape-Werkbank. Glow-/Status-, Glas- und
  Kristallmaterialien bleiben untexturiert (`docs/UNITY_INTEGRATION.md`).
- **Blender-Plugin** (MCP, Werkzeuge `mcp__Blender__*`): steuert das **laufende** Blender des Nutzers (Add-on „MCP“
  aus dem Extensions-Repository von Blender Lab, Port 9876). Als Prüfstand nutzen: Exporte laden und nachmessen
  (Maße, Pivot, Vorderseite, Teil-/Materialnamen, Öffnungen für die Kollision), Texturen am Modell ansehen, Ansichten
  rendern. Immer in einer eigenen Szene, nichts speichern – die Quelle bleibt der Generator. Ohne laufendes Blender
  (Cloud, Batch) fehlt das Plugin; dann gilt nur der Batch-Export.

## Ausrichtung gerichteter Modelle

Bei Kameras und anderen gerichteten Modellen die tatsächliche Funktionsfläche prüfen,
nicht nur die Objektrotation: Blender-/Unity-Achsen, Neigung und beide Schwenkvorzeichen
gegen die exportierte Geometrie testen. Ein Anker- oder Bounds-Test ersetzt keinen
Nachweis der Blickrichtung. Beabsichtigte Korrekturen gegenüber alten Generationen
ausdrücklich dokumentieren und historische Ausgaben getrennt prüfen.

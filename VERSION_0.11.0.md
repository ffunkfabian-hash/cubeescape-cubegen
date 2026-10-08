# Cubegen 0.11.0 · Fragmentkollision und Unity-Integration

Stand: 8. Oktober 2026. Version 0.11.0, Release-Branch `release/0.11.0`.
Auf ausdrücklichen Nutzerwunsch ersetzt 0.11.0 die bisher geplante 0.10.6.
Die früheren lokalen Abnahmen bleiben unten als Historie erhalten.

## Analyse vor dem Bau

**Bestand:** Generation 3 nutzt Compound-Fragmente (`Fragment_*`/`Shard_*`),
vorhandene Kollisionsrezepte und Unitys Bruch-/Reset-Lebenszyklus. Das bisherige
Patch-Vorhaben umfasst inzwischen Strukturprofile, Hohlrohre/Ringe, konkave
Extrusionen, profilierte Drehkörper und verformte Kästen sowie mehrere Modell-
und Exportkorrekturen. Die Versionsumstellung bündelt diese Arbeit als 0.11.0.

**Aktueller Auftrag:** Die neun verbliebenen Quellen mit verformten radialen
Oberflächen untersuchen und passende Zerlegung ergänzen. Zuerst gemeinsame
Fels-/Schutt-Geometrie verwenden, dann weitere nachweisbar geschlossene Netze.
Vorhandene Dreiecks-/Volumen-/Konvexitätsprüfungen wiederverwenden. Rendering und
Kollision verwenden dieselben expliziten Flächen; kein pauschaler Hull-Ersatz.

**Golden Rule und Kompatibilität:** Bestehende Systeme und Budgets verwenden;
keine neuen Save-/Level-Formate, keine Umbenennung persistenter IDs oder automatische
Gameplay-Freigabe. Generation 1/2 bleiben historische Ausgabe. Offene, invertierte
oder nicht sicher partitionierbare Teile bleiben mit genauer fester Kollision.

**Versionsumfang:** Paket, CLI, Blender-Quell-Add-on und eigenständiges ZIP auf
0.11.0 bringen; lokale Add-on-Aktualisierung erst mit geprüftem Bundle. Alte
Prüfbelege bleiben ihrem tatsächlichen Generatorstand zugeordnet. Haupt-Checkout
von Cube Escape bleibt bis zu einem gesonderten Integrationsauftrag unverändert.

## Übernommene Änderungen aus dem bisherigen 0.10.6-Vorhaben

- Generation-3-Fragmente besitzen Compound-Parents und passende einzelne Collider.
  Ein Rigidbody je Fragment; getrennte Stäbe und freie Zwischenräume werden nicht
  durch eine gemeinsame konvexe Hülle verschlossen.
- Fragmentpivots auf das vorhandene Sidecarraster quantisiert; Z-Fighting-Korrektur
  verschiebt ganze Körper und erhält Konvexität. Tatsächliche Fragment-Draw-Calls
  werden gezählt; keine angenommene kostenlose Kombination.
- Fehlender `FX_Steam`-Anker ergänzt; Unity verwendet vorhandene Audio-/FX-Ereignisse
  und ausdrücklich authorierte Modellprofile.
- Vorhandene konvexe Komponenten zusammengesetzter Strukturprofile wiedergewonnen.
  Hohlrohr-/Ring-/Torus-Wandsegmente erhalten ihre Öffnungen.
- Konkave Extrusionsprofile und profilierte Drehkörper erhalten genaue konvexe
  Teilstücke; Volumen, Außenflächen und Materialrollen bleiben erhalten.
- Verformte achtpunktige Kästen verwenden gemeinsame explizite Render-/Collider-
  Dreiecke und eine begrenzte Partition. Plane konvexe Körper bleiben unverändert.
- Blender-View-Layer vor der Collection-Auswahl aktualisiert; wiederholter Export
  nach Löschen/Neuaufbau greift nicht auf veraltete Objekte zu.
- Breite kurze `fallen_pillar`-Stümpfe begrenzen aktuelle Verformungen an ihrer
  tatsächlichen Höhe; obere Ecken können nicht mehr unter die Grundfläche geraten.

Die damaligen Befunde, Ursachen, Kompatibilitätsausnahmen und Ergebnisse stehen
im [archivierten 0.10.6-Arbeitsbericht](docs/archive/VERSION_0.10.6_WORKING.md).
Bisheriger Prüfsatz: 175 Typen, Master-Seed 42, Index 0, Generation 3; Quellen mit
nichtkonvexen Shapes **34 → 9**. Letzte damalige Abnahme: 222 Generator-Tests und
888 Unity-Tests grün, acht gezielte Kasten-/Extremvarianten-FBX ohne Fehler.
Diese Zahlen sind historische Nachweise, keine neue 0.11.0-Abnahme.

## Verbindlicher Auftrag für kommende Phasen

Belegte Cubegen-Fehler sofort korrigieren und einen Regressionstest ergänzen.
Die Befunde dieser Version sind hier dokumentiert; kommende Befunde gehören in
den nächsten unveröffentlichten Versionsbericht. Fund, Ursache, geprüfte Varianten
und echte Unity-Nachweise festhalten. Keine gelockerten Importprüfungen oder pauschalen
Ablehnungsausnahmen als Reparatur. Nach Veröffentlichung gilt der nächste
unveröffentlichte Versionsbericht.

## Radiale Oberflächen · Umsetzung von Punkt 3

Die neun verbliebenen Quellen verwenden jetzt die vorhandene exakte Volumenpartition
auch für nachweisbar geschlossene radiale Netze. Außen-Dreiecke, Vertiefungen und
Materialrollen bleiben erhalten. Ein geprüfter innerer Punkt verbindet die
Dreiecke zu konvexen Tetraedern; nur nachweisbar konvexe Nachbarvereinigungen werden
zusammengeführt. Renderer und Collider verwenden dieselben expliziten Dreiecke.
Die Fragmentanzahl steigt dabei nicht; mehrere Shapes gehören zu einem Rigidbody.

Begrenzung: 4–64 Punkte, 4–128 Dreiecke, endliche Koordinaten, verbundene orientierte
Oberfläche, jede Kante genau zweimal entgegengesetzt, Eulerzahl 2. Der innere Punkt
muss strikt hinter allen Außenflächen liegen; sphärische Windung und erhaltenes
Volumen werden geprüft. Die Suche endet nach höchstens 128 Projektionsschritten;
eine zusätzliche Zweiebenenlösung verwendet höchstens 16 aktive Ebenen. Offene,
invertierte, degenerierte, größere oder nicht nachweisbar sternförmige Körper
bleiben ohne dynamische Freigabe. Dies ist keine universelle Mesh-Zerlegung.

Zwei Seed-Grenzfälle sofort korrigiert und durch Regression abgesichert:
`cocoon` Seed 1 besitzt fast gegenüberliegende Flächen, bei denen die einfache
Projektion innerhalb des festen Limits nicht konvergierte. Die begrenzte
Zweiebenenlösung liefert einen überprüfbaren inneren Punkt. `stalagmite` Seed 1
besitzt sehr kleine Außen-Dreiecke; flächenabhängiger Innenabstand verhindert
numerisch degenerierte Tetraeder. Nicht plane Flächen passieren keinen reinen
Polygon-Konvexitätskurzschluss und keinen ungeeigneten Voronoi-Schnitt mehr.

### Vergleich und Kosten

175 Typen, Master-Seed 42, Index 0, Generation 3: **9 → 0 Quellen** mit
nichtkonvexen Shapes, **166 Digests unverändert** gegenüber dem Kasten-Schritt.
Kumulativ gegenüber den ursprünglichen Generation-3-Shards: **34 → 0**, 34
geänderte und 141 unveränderte Digests. Diese Aussage gilt für den beschriebenen
Prüfsatz, nicht für jede beliebige Parameterkombination.

| Quelle | Körper vorher → danach | Shapes vorher → danach |
|---|---:|---:|
| `asteroid` | 3 → 3 | 10 → 54 |
| `cocoon` | 3 → 3 | 8 → 51 |
| `crashed_pod` | 8 → 8 | 18 → 56 |
| `floating_island` | 9 → 9 | 13 → 63 |
| `hanging_crystals` | 5 → 5 | 23 → 34 |
| `rock` | 4 → 4 | 8 → 66 |
| `rubble_pile` | 7 → 7 | 28 → 42 |
| `scrap_heap` | 6 → 6 | 28 → 42 |
| `stalagmite` | 2 → 2 | 6 → 108 |

Zusätzliche Shapes und Innenflächen haben Physik-/Renderingkosten. Die bestehenden
Grenzen gelten weiter: höchstens 16 Körper/256 Shapes pro Objekt, global 96 Körper/
1024 Shapes, automatische Aufräumzeit 4 s. Keine Zerlegung zur Laufzeit und keine
neuen Abhängigkeiten. Der gezielte 175-Typen-Vergleich dauert rund 5 s ohne Blender,
FBX-Export oder Rendering. Das ist keine FPS-Messung.

### Geprüfte Ergebnisse

- Vollständige Generator-Suite: **227 Tests grün (139 s)**; gezielter Fragmentlauf:
  **36 Tests grün (11,41 s)**.
- **36 aktuelle Seed-Fälle** der neun Familien (0, 1, 42 und abgeleiteter Seed):
  alle Shapes konvex, maximal 127 Shapes pro Objekt. Historische Generationen 1/2
  sowie normale intakte/beschädigte/zerstörte Vergleichszustände bleiben geprüft.
- Ein Blender-Batch: neun reale Standardquellen, zwei Seed-Grenzfälle und drei
  isolierte radiale Proben. **14 echte FBX-Importe/Wiederimporte ohne Fehler oder
  Ablehnung**, ein Unity-EditMode-Test grün (7,70 s). Bei den drei Proben werden
  tatsächliche FBX-Dreiecksindizes und Punkte mit den Quelldreiecken verglichen.
- Drei Proben mit je einem Körper und 18/15/40 Shapes: freie Vertiefungen und feste
  Flächen, gedrehte Modelle, Fallenlassen, Pause, Aufräumen, Wiedereintritt und
  insgesamt 30 serialisierte Resets je Lauf. Regulärer PlayMode-Test grün (0,57 s),
  Screenshotlauf grün (0,99 s), **neun neue Bilder geprüft**. Produktionssettings
  bleiben erhalten; kumulativ 55 Phase-5-Bilder.
- Vollständige Unity-Regression: **888/888 grün (393 s)**, sechs Stufen: 213
  Tier-0/EditMode, 9 Smoke, 143 gezielt, 62 Related, 241 weitere Full EditMode,
  220 Full PlayMode. Testkarte ohne Lücken; zwölf Skill-Dateien ohne Befund.

Belege im Unity-Worktree: `QA/Reports/Cubegen0110RadialSurfaces/README.md`.

## Version und lokale Installation

`pyproject.toml`, Paketversion, CLI und Blender-Add-on sind **0.11.0**.
`dist/cubegen_blender_addon_0.11.0.zip` enthält den eigenen geprüften Generator.
SHA-256: `c143306712eaf98152a4fbf277266eb074d11f8e41c9661044dd93da66cdf53f`.

Das vorhandene Blender-5.2-Add-on ist lokal auf 0.11.0 aktualisiert. Sicherung des
vollständigen vorherigen 0.10.5-Add-ons:
`/Users/ffunk/.codex/backups/cubegen-addon-0.10.5-20261008-201023`.
Ein separater Blender-Factory-Start hat Registrierung, Add-on-/Paketversion,
tatsächlich installierten vendorten Modulpfad, alle neun Quellen und einen echten
FBX-Export geprüft. Alle 72 Bundle-Dateien stimmen bytegenau mit dem installierten
ZIP-Inhalt überein. Benutzereinstellungen wurden nicht gespeichert. Ein bereits
geöffnetes Blender lädt den neuen Code nach Neustart/Neuladen des Add-ons.

Bestehende Vorschauen, FBX-Dateien und Unity-Prefabs werden dadurch nicht automatisch
neu erzeugt. Dieser ursprüngliche Abnahmestand lag zunächst nur im Worktree; die
anschließende ausdrücklich beauftragte Integration steht im nächsten Abschnitt.
Weitere Gameplayprofile benötigen ihre eigene Abnahme.


## Sichtbarer Spieltest und Integration · Folgeauftrag 8. Oktober 2026

Auf Nutzerwunsch folgt die Übernahme des geprüften Standes in den Unity-Haupt-
Checkout. Dafür sind zwölf Bruchprofile (Kiste/Käfig/Rohr plus die neun radialen
Quellen, Master-Seed 42/Index 0) und 13 bestehende Phase-4-Profile mit 0.11.0 neu
exportiert. Alle **25 tatsächlichen FBX** wurden gegen ihre exakten Quellrezepte
geprüft und im bestehenden Unity-Importer in der Testkopie importiert.

Die neue Daten-Testanlage Z-1 verwendet den bestehenden LevelLoader, Bruchadapter
und die vorhandenen Signalports. Je Station: BRUCH links, RESET rechts; Modelle
hängen 1,6 m über dem Fangboden. Zugang: Hauptmenü OPTIONEN > ENTWICKLUNG >
DEV-MENÜ einschalten, dann ENTWICKLERWERKZEUGE > Bruch-Testanlage Z-1.
Weitere Parameter-/Modellformen bleiben eigene Abnahmen; die Freigabe betrifft die
konkreten Profile und erweitert kein Save-/Level-Format.

Abnahme: sechs Editor-Vertragsprüfungen grün (1,11 s), zwei tatsächliche
Button-Spieltests in Iso/Ego grün (3,65 s), jeweils alle zwölf Stationen. Jeder
Spieltest bricht jedes Modell zweimal, setzt dieselben Körper/Collider zurück und
prüft auch Reset nach vier Sekunden Cleanup. Ein Screenshotlauf grün (5,71 s), sechs Bilder
geprüft. Vollständige Unity-Regression **891/891 grün (406 s)**: 222 Tier-0/EditMode,
11 Smoke, 158 gezielt, 77 Related, 233 weitere Full EditMode, 190 Full PlayMode.
Bestands-GUIDs und Root-fileIDs aller 17 geänderten Gameplay-Prefabs erhalten.
Auf ausdrücklichen Nutzerwunsch in Unity-`main` übernommen: **`464717e`**,
Fast-Forward von `847d90f` am 8. Oktober 2026 bei sauberem Haupt-Checkout.
Keine Szenen neu aufgebaut, kein Cube-Escape-Release-Tag. Cubegen 0.11.0 und das
geprüfte installierte Add-on sind der zugehörige Generatorstand. Die anschließende
Quellcode-Veröffentlichung auf GitHub erfolgt über den ausdrücklich gewünschten
Branch `release/0.11.0`.


## GitHub-Übernahme · 8. Oktober 2026

Nutzerauftrag: Cubegen auf GitHub auf 0.11.0 aktualisieren, den Arbeitsbranch
`release/0.11.0` nennen, committen und mergen. Der bestehende GitHub-Standardbranch
ist `claude/quirky-galileo-bsz6fk` und bleibt das Merge-Ziel; keine Änderung des
Standardbranches oder Löschung bestehender Remote-Branches.

Paket-/CLI-/Add-on-Version einheitlich 0.11.0. Alle bisherigen Phase-5-Korrekturen
und der eigene Versionsbericht gehören in denselben Release-Stand. Lokale
Generator-Gesamtsuite vor Push, anschließend die bestehende GitHub-Matrix
(Python 3.9/3.11/3.13, Gruppen models/quality/rest) vor Merge prüfen.
Unity-Phase 5 ist bereits als `464717e` plus Dokumentation `f11867e` in main;
891/891 Unity-Tests grün. Keine weitere Unity-Code-/Asset-Änderung in diesem Auftrag.

Abnahme vor Push erneut vollständig ausgeführt: **227/227 Generator-Tests grün
(131 s)**, Gruppen models 41, quality 12, rest 174. Versioniertes Add-on-ZIP
0.11.0 geprüft, SHA-256 weiterhin
`c143306712eaf98152a4fbf277266eb074d11f8e41c9661044dd93da66cdf53f`.

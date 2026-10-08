# Cubegen 0.10.6 · Arbeitsstand aus Unity-Integrationsphase 5

Stand: 8. Oktober 2026. Unveröffentlicht; installierte Paket-/CLI-Version bleibt 0.10.5.

## Verbindlicher Auftrag für kommende Phasen

Belegte Cubegen-Fehler sofort korrigieren, einen Regressionstest ergänzen und hier bis
zur Veröffentlichung dokumentieren. Fund, Ursache, geprüfte Varianten und echten
Unity-Nachweis festhalten. Keine Fehler bis zu einer späteren Phase verschieben,
keine Ablehnungsausnahmen als Reparatur. Veröffentlichte Berichte bleiben historisch;
nach Veröffentlichung wandern neue Befunde in den nächsten unveröffentlichten Bericht.

## Fragmentkollision

Befund: `fracture_asset` vereinte alle Körper einer Voronoi-Zelle in einem Mesh mit
einem konvexen Collider. Getrennte Stäbe eines Käfigs erzeugten dadurch feste Hüllen
über freie Zwischenräume. Bei Seed 42: Kiste 19 Primitive in fünf Hüllen, Käfig
176 in acht Hüllen; jede der Gesamthüllen umfasste nichtkonvexe Geometrie.

Korrektur für Generation 3: `Fragment_<nn>` sind Compound-Parents; je ursprünglichem
Körper entsteht ein `Shard_<nn>_<nnn>` mit eigenem Mesh-Collider. Konvexe Körper
bleiben konvex, seltene nichtkonvexe Teile erhalten genaue feste Mesh-Collision.
Solche Quellen sind für dynamische Fragmentphysik noch nicht freigegeben. Der
Unity-Adapter prüft Konvexität und das Körper-/Shape-Budget ausdrücklich. Visuelle
Geometrie und Volumen bleiben erhalten; mehr Teilrenderer sind ein bewusster Preis
für korrekte Zwischenräume. Generation 1/2 behalten historische Einzelhüllen.
Die Anschluss-/Qualitätsprüfung verwendet für die getrennten Shards die wirklichen
Volumina statt ihrer Bounding-Boxen. Der alte Z-Fighting-Pass verschob nur einzelne
Flächen und konnte konvexe Schnitte konkav machen. Er verschiebt bei aktuellen
Fragmenten ganze Körper mit einem kleinen deterministischen Tangentialanteil.
Gleichfarbige Shards desselben starren Fragment-Parents werden wie zuvor die
Primitive desselben Objekts behandelt; unterschiedlich gefärbte oder unabhängig
bewegte Gruppen bleiben geprüft. Der Draw-Call-Bericht zählt Fragment-Submeshes
statt pauschal Static Batching anzunehmen.

## FBX-Pivots der Fragment-Parents

Der echte Volltypen-Export fand am `cryo_pod` eine Rundungsabweichung von 0,1 mm
an `Fragment_06`: Python-Sidecar und Blender-float32 lagen an unterschiedlichen
Seiten eines halben Rasterwerts. Neue Generation-3-Fragmentpivots werden vor dem
Export auf das bestehende 0,1-mm-Sidecarraster quantisiert. Keine Geometrie-/
Pivot-Prüfung gelockert. Ein echter Blender-/FBX-Regressionstest reproduziert
Master-Seed 42; Generation 1/2 bleiben unverändert.

## Dampfanker

`steam_vent` hatte nur `Audio_Hiss`, obwohl Phase 5 einen Partikelausstoß am erhaltenen
Modellanker benötigt. Generation 3 ergänzt `FX_Steam` am selben Auslasspunkt für
beide Formen und intakte/beschädigte Varianten. Unity richtet den Effekt nach der
bestehenden Jet-Steuerung und deren Reichweite aus.

## Prüfstatus

Phase 5 ist im Unity-Worktree `6082` abgenommen: **888/888 Unity-Tests grün in
377 s** (Tier 0/EditMode 213, Smoke 9, gezielt 143, Related 62, Full EditMode 241,
Full PlayMode 220). Der echte Generation-3-FBX-Audit prüfte **175 Quellen ohne
Ablehnung oder Fehler**; sieben Bilder dokumentieren Zerfall, Aufräumen, Reset,
Dampf und Werkbank. Die dynamische Freigabe umfasst nur die drei authorierten Profile
Kiste, Käfig und Rohr. Nichtkonvexe Shards bleiben statisch, bis eine konvexe
Zerlegung vorliegt; weitere Mechaniken und Profile folgen in eigenen Phasen.
Paket, CLI und Add-on bleiben bis zu einer ausdrücklichen Veröffentlichung auf 0.10.5.

## Nacharbeit · strukturelle Kastenprofile ressourcenschonend zerlegen

### Analyse vor dem Bau

Die 34 gesperrten Quellen des Master-Seed-42-Audits gehören mehreren Formfamilien an:
zusammengesetzte Kastenprofile, Hohlrohre/offene Schalen, Ringkörper, konkave
Extrusionspolygone und verformte bzw. eingeschnürte Körper. Erste gezielte Familie:
zusammengesetzte Kastenprofile. U-/L-/T-/I-Profile und Gitter besitzen bereits einzelne
geschlossene konvexe Körper, deren Vertex-Indizes beim Zusammenfügen getrennt bleiben.
Diese vorhandene Struktur ersetzt hier eine allgemeine geometrische Zerlegung.

Generation 3 gewinnt die verbundenen Komponenten über Vertex-/Kantenindizes zurück.
Jede Komponente muss geschlossen, konvex und von positivem Volumen sein; sonst bleibt
die ganze Quelle unverändert gesperrt. Es werden keine Punkte verschweißt, neuen
Flächen erzeugt oder Hüllen angepasst. Teilflächen, Materialrollen und Volumen der
Grundform bleiben erhalten. Alle Komponenten bleiben im bisherigen Fragment-Parent:
kein zusätzlicher Rigidbody und keine Zerlegung während des Spiels. Historische
Generationen 1/2 bleiben unverändert.

### Gemessener Umfang

`python3 -m tools.audit_fragment_profiles` vergleicht alle 175 Typen, Generation 3,
Master-Seed 42, Index 0 ohne Blender oder Rendering. Mit Digestvergleich: **4,18 s**.
Sieben Typen profitieren; die übrigen **168 Quellen haben unveränderte Modell-Digests**
(Geometrie, Pivots, Materialien, Collider und Metadaten; bestehendes 10⁻⁶-Floatraster). Quellen
mit mindestens einem nichtkonvexen Shape sinken von **34 auf 32**. Das ist keine
Gameplay-Freigabe der experimentellen Modelle. Hohlrohre, Ringe und tatsächlich
konkave zusammenhängende Formen bleiben für spätere gezielte Schritte offen.

| Quelle | Körper vorher → danach | Shapes vorher → danach | nichtkonvexe Shapes vorher → danach |
|---|---:|---:|---:|
| `geometry_test` | 8 → 8 | 8 → 28 | 6 → 1 |
| `test_magnetic_lock` | 5 → 5 | 17 → 19 | 7 → 6 |
| `test_pipe_rack` | 5 → 5 | 13 → 17 | 11 → 9 |
| `test_power_routing` | 4 → 4 | 17 → 18 | 4 → 3 |
| `test_scanner_pad` | 4 → 4 | 8 → 29 | 3 → 0 |
| `test_utility_trench` | 4 → 4 | 10 → 12 | 4 → 3 |
| `test_warning_beacon` | 6 → 6 | 17 → 19 | 2 → 0 |

Das isolierte U-Profil benötigt **einen Körper und drei Shapes**, mit unveränderter
Öffnung. Bestehende Objekt-/globale Physikbudgets bleiben verbindlich.

Abschluss: **201 Generator-Tests grün (210 s)**. Drei gezielte echte FBX-Quellen
importiert/reimportiert: 0 Ablehnungen, 0 Fehler (1 EditMode-Test, 1,58 s). Der echte
U-Physiktest prüft freie Öffnung, feste Basis, einen Körper/drei Shapes, Bewegung,
zehn Sequenz-Resets und Aufräumen (1 Test grün, 65,31 s inklusive Asset-Import).
Drei zusätzliche Bilder geprüft (1 Test, 4,19 s). Erneute volle Unity-Regression:
**888/888 grün in 384 s**, sechs Stufen (213 EditMode, 9 Smoke, 143 gezielt,
62 Related, 241 weitere Full EditMode, 220 Full PlayMode).
Belege im Cube-Escape-Worktree unter `QA/Reports/Cubegen0106Profiles`.

Die frühere pauschale Zeitschätzung für sämtliche Restformen war nicht ausreichend
begründet und wurde zurückgenommen. Folgearbeit wird nach konkreter Grundform
beurteilt; Prüfzeiten und Abdeckung werden tatsächlich gemessen. Die 32 beziehen
sich auf den Abschluss dieses ersten Seed-42-Prüfsatzes; der nächste Schritt folgt unten.

## Nacharbeit · Hohlrohre und einfache Ringe

### Analyse vor dem Bau

Der Nutzer beauftragt den nächsten gezielten Schritt und das Bündeln der Prüfungen.
`pipe_section`, `ring` und `torus` besitzen bekannte prozedurale Querschnitte.
Ein Rezept über die vorhandenen Vertex-Indizes beschreibt deren geschlossene
Wandsegmente. Das Rezept bleibt beim normalen Meshaufbau erhalten und wird erst
bei Generation-3-Fragmentexporten verwendet. Translation, Rotation, Skalierung und
Normalisierung verändern die zugrunde liegenden Punkte weiterhin gemeinsam mit
der visuellen Geometrie; keine veralteten separaten Kollisionskoordinaten.

Jedes Segment wird nach den Modelltransformationen auf Konvexität, geschlossene
Kanten und positives Volumen geprüft. Ungültige/verformte Rezepte behalten genaue
feste Kollision. Bestehende Außenflächen und Materialrollen bleiben erhalten;
Segment-Abschlussflächen werden ergänzt. Beim bislang offenen Rohr-/Band-Mesh wird
auch die fehlende Wandabschlussfläche geschlossen, während die zentrale Öffnung
frei bleibt. Alle Segmente bleiben im bisherigen Fragment-Parent: kein zusätzlicher
Rigidbody, keine Zerlegung im Spiel und keine externe Geometriebibliothek.
Generation 1/2 und normale intakte/beschädigte/zerstörte Ausgabe bleiben erhalten.

### Aktueller Prüfumfang

`python3 -m tools.audit_fragment_profiles --baseline structural` vergleicht gegen
den vorherigen Profil-Schritt. Alle 175 Typen, Master-Seed 42, Index 0, Generation 3:
**32 → 20 Quellen mit nichtkonvexen Shapes**, zwölf weitere Quellen vollständig
konvex; 163 unveränderte Modell-Digests. Körperzahl überall unverändert. Zusätzliche
36 Fälle (die zwölf Typen je Seed 0/1/42) haben ebenfalls ausschließlich konvexe
Shapes und bleiben unter 256 Shapes. Das ersetzt keine Freigabe beliebiger Varianten.

| Quelle | Körper | Shapes vorher → danach |
|---|---:|---:|
| `cable_reel` | 2 | 8 → 53 |
| `geometry_test` | 8 | 28 → 35 |
| `hologram` | 8 | 34 → 64 |
| `reactor_core` | 9 | 82 → 109 |
| `test_coolant_loop` | 5 | 17 → 89 |
| `test_lens_array` | 5 | 22 → 55 |
| `test_magnetic_lock` | 5 | 19 → 73 |
| `test_pipe_rack` | 5 | 17 → 98 |
| `test_power_routing` | 4 | 18 → 33 |
| `test_relay_box` | 6 | 24 → 38 |
| `test_thermal_switch` | 4 | 22 → 47 |
| `test_utility_trench` | 4 | 12 → 33 |

Die drei isolierten Proben benötigen je einen Körper: Rohr acht Shapes, Band und
Torus je zehn Shapes. Mehr Shapes/Teilrenderer kosten Physik-/Renderingarbeit;
keine pauschale FPS-Verbesserung behauptet. Bestehende globale und Objektbudgets
bleiben verbindlich. Zwanzig andere Quellen bleiben statisch; technisch korrekte
Fragmente sind noch keine automatische Unity-Werkbankfreigabe.

### Sofortkorrektur · Collection-Auswahl beim gebündelten Blender-Export

Der neue Batch entfernte eine Collection und baute die nächste in derselben Blender-
Sitzung. Blender 5.2.2 lieferte dabei veraltete View-Layer-Einträge (`None`) an
`select_collection`; der Export brach an `obj.select_set(False)` ab. Der gemeinsame
Exporthelfer aktualisiert nun den View-Layer vor Auswahl und Export. Ein echter
Blender-Regressionstest entfernt/baut/exportiert drei Collections nacheinander,
prüft ihre FBX-Hierarchie und den Sidecar-Vertrag. Keine Prüftoleranz gelockert.

### Prüfung

**205 Generator-Tests grün (130 s)**. Die gezielten Exporte verwenden den vorhandenen
Mesh-/FBX-Builder, einen Blender-Prozess und keine Vorschaurenderings: zwölf reale
Modelle und drei isolierte Proben. Echte Unity-Import-/Wiederimportprüfung: **15 Quellen
ohne Ablehnung oder Fehler** (1 EditMode-Test, 6,71 s). Der gebündelte PlayMode-
Nachweis prüft Rohr/Band/Torus: feste Wand, freie Öffnung/Raycasts, gedrehte Modelle,
Bewegung, Pause, je zehn serialisierte Sequenz-Resets, Aufräumen, Wiedereintritt und
erhaltene Collider-Identitäten. Mit regulärem Renderer grün (1 Test, 1,14 s), mit
temporärem Screenshot-Renderer grün (1 Test, 0,90 s); neun Bilder geprüft.
Der Screenshot-Renderer ist eine nur für die Aufnahme verwendete URP-Kopie ohne
GPU Resident Drawer, um dessen veraltete manuelle `Camera.Render()`-Instanzen zu
vermeiden. Produktionskonfiguration und Assets bleiben erhalten; kein FPS-Beleg.

Erneute vollständige Unity-Regression: **888/888 grün in 382 s**. Stufen: 213 Tier-0/
EditMode, 9 Smoke, 143 gezielt, 62 Related, 241 weitere Full EditMode und 220 Full
PlayMode. Testkarte ohne Lücken und Skillprüfung ohne Befund. Belege im Unity-
Worktree unter `QA/Reports/Cubegen0106RoundWalls`. Beide Repositories uncommittiert;
kein Release, Tag oder Merge. Das installierte Blender-Add-on bleibt beim
veröffentlichten 0.10.5-Stand; die neuen Rezepte liegen im lokalen 0.10.6-Arbeitsstand.

## Nacharbeit · konkave Extrusionsprofile

### Analyse vor dem Bau

Der Nutzer beauftragt die dritte Formfamilie: Torbögen, Stahlträger und Symbole,
zusätzlich verwandte konkave Extrusionen im verbleibenden Prüfsatz. Die vorhandenen
Wandsegment-Rezepte und der Fragment-Lebenszyklus werden wiederverwendet. Keine
neue Laufzeitzerlegung, kein neues Save-/Level-Format oder automatische Gameplay-
Freigabe. Konvexe und historische Ausgabe behalten ihren bestehenden Vertrag.

Einfache konkave Querschnitte mit höchstens 128 Punkten werden deterministisch
per Ear-Clipping in Dreiecke zerlegt. Benachbarte Teile werden nur bei konvexer
Vereinigung zusammengeführt. So braucht ein L-Profil zwei und die isolierten
Torbogen-/I-Träger-/Pfeilproben je drei Shapes an einem bisherigen Körper. Alle
Punkte stammen aus dem Originalprofil: Fläche, Volumen, Umfang und Materialrollen
bleiben erhalten, innere Abschlussflächen werden ergänzt. Ungültige, selbst-
schneidende/-berührende oder degenerierte Profile bekommen kein dynamisches Rezept.
Nach den Modelltransformationen gelten weiterhin die 3D-Konvexitäts-/Volumenprüfungen.

### Aktueller Prüfsatz

`python3 -m tools.audit_fragment_profiles --baseline round`: 175 Typen, Generation 3,
Master-Seed 42, Index 0. **20 → 15 Quellen mit nichtkonvexen Shapes**, fünf weitere
vollständig konvexe Quellen, 170 unveränderte Modell-Digests. Körperzahl unverändert.

| Quelle | Körper | Shapes vorher → danach |
|---|---:|---:|
| `archway` | 6 | 28 → 30 |
| `fungus_carpet` | 5 | 36 → 38 |
| `girders` | 5 | 8 → 14 |
| `puddle` | 3 | 5 → 9 |
| `symbol_plate` | 4 | 17 → 23 |

Zwanzig Seed-Fälle (0/1/42 und jeweiliger Master-Seed-42-Modellseed) sowie acht
Torbogen-Form-/Maßkombinationen sind zusätzlich geprüft. Weitere freie/verformte
Geometrie bleibt ein eigener Schritt. Paket-/CLI-Version bleibt 0.10.5; keine
Änderung am installierten Add-on und keine Veröffentlichung.

### Prüfung

**210 Generator-Tests grün (121 s)**. Neue Regressionen prüfen Umfang, Volumen,
Cap-/Seitenmaterialien, Aussparungen, Transformationen, ungültige Profile,
Körper-/Shape-Budgets und deterministische Ausgabe. Der vorhandene Blender-Batch
exportiert nun wahlweise `--family extrusion`: fünf reale Quellen und drei isolierte
Profile in einem Prozess ohne Vorschaurendering. Echter Unity-Import/Reimport:
**8 Quellen ohne Ablehnung oder Fehler**, 1 EditMode-Test grün (4,12 s).
Gemeinsame Physik-/Bildprüfung: **1 PlayMode-Test grün (0,88 s)** mit neun geprüften
Bildern; die neue explizite Extrusionsfixture am regulären Renderer ebenfalls
grün (1 Test, 0,54 s). Torbogen, I-Träger und Pfeil behalten freie Aussparungen/Raycasts und feste
Profilflächen; gedrehte Modelle, Bewegung, Pause, insgesamt 30 serialisierte Resets,
Aufräumen nach Ablauf und Wiedereintritt geprüft. Collider-Identitäten bleiben
erhalten. Temporärer Screenshot-Renderer ohne Änderung der Produktionskonfiguration.
Finale Unity-Regression: **888/888 grün (385 s)**, sechs Stufen (213 Tier-0/EditMode,
9 Smoke, 143 gezielt, 62 Related, 241 weitere Full EditMode, 220 Full PlayMode).
Testkarte ohne Lücken und Skillprüfung ohne Befund. Belege im Unity-Worktree:
`QA/Reports/Cubegen0106Extrusions/README.md`. Haupt-Checkout unverändert.
Kein Commit, Tag, Merge oder Release; keine neue automatische Gameplay-Freigabe.


## Nacharbeit · profilierte Drehkörper — Analyse vor dem Bau

Der Nutzer beauftragt die Untersuchung der verbliebenen 15 Quellen. Der feste
Master-Seed-42-Prüfsatz enthält drei wiederkehrende Drehprofile (Antennenschüssel,
Kristallsockel, Transformator-Isolatoren); die anderen Quellen enthalten verformte
Kästen, Kugel-/Kegel-/Drehkörper oder eingedrückte Oberflächen. Ein Quellenname
ist keine Geometrie-Freigabe: Mischmodelle können mehrere Ursachen enthalten.

Der nächste gezielte Schritt verwendet vorhandene Profile und Vertex-Rezepte:
monotone volle Drehkörper in geschlossene Kegelstümpfe, geschlossene radiale
Querschnitte in konvexe Winkelstücke zerlegen. Flächen und Materialrollen am
Original erhalten; kein neuer Körper pro Shape, keine Laufzeitzerlegung und keine
Änderung des Speicherformats. Geschlossene Topologie, plane Flächen, Konvexität
und positives Volumen nach Transformationen prüfen. Verformte oder ungültige
Rezepte bleiben statisch. Bereits konvexe Körper sollen unverändert bleiben.

Prüfplan: Ursachenbericht aller 15 Quellen; pure Geometrie-/Seed-/Formregressionen,
volle Generator-Suite, gezielter Blender-FBX-Batch und Unity-Import/Reimport,
gebündelte Physik-/Öffnungs-/Resetprüfungen und Bilder. Der Impact-Plan fordert
wegen des noch uncommittierten Phase-5-Katalogs weiterhin volle Unity-Regression.
Haupt-Checkout und installiertes Add-on bleiben unverändert.


Die Ursachenanalyse aller 15 Quellen liegt unter
`QA/Reports/Cubegen0106LatheProfiles/remaining-analysis.json`. Drei profilierte
Drehkörper, drei verformte Kästen und neun verformte radiale Oberflächen;
Mischmodelle können mehrere betroffene Teile enthalten. Alle untersuchten
Teilstücke sind als geschlossen markiert; diese Markierung allein beweist
weder Konvexität noch eine sichere Zerlegung.

### Umsetzung und aktueller Prüfsatz

`lathe` liefert zusätzliche Rezepte über Originalpunkte: volle monotone Profile
als geschlossene Kegelstümpfe, geschlossene radiale Querschnitte mit Achsen-Enden
als konvexe Winkelstücke. Ein Endpol in der Ebene des letzten Rings bleibt eine
flache Abschlussfläche und wird kein Stück ohne Volumen. Umfang, Volumen und
Außenmaterialien bleiben erhalten. Die vorhandene Polygonzerlegung wird für
radiale Profile wiederverwendet. Bereits konvexe Körper bleiben ein einzelnes
Shape. Offene, selbstschneidende/-berührende, nicht endliche oder zu große Profile
bekommen kein Rezept; Profil und Seitenzahl sind auf höchstens 128 begrenzt.

Nach Modelltransformationen prüft der bestehende Fragmentvertrag zusätzlich
die Planarität jeder Rezeptfläche. Ein verdrehtes Viereck darf durch konvexe
Physikkochung keine andere Fläche erhalten. Invalides bleibt mit genauer fester
Kollision erhalten. Kein neuer Rigidbody pro Teilstück; bestehende Budgets gelten.
Die rezeptebedingten Zusatzflächen erhöhen Mesh-/Physikkosten; kein FPS-Gewinn
ist daraus abgeleitet.

Vergleich `python3 -m tools.audit_fragment_profiles --baseline extrusion`:
175 Typen, Master-Seed 42, Index 0, Generation 3. **15 → 12 Quellen mit
nichtkonvexen Shapes**, **172 Digests unverändert**. Körperzahl überall gleich.

| Quelle | Körper | Shapes vorher → danach |
|---|---:|---:|
| `antenna` | 9 | 14 → 37 |
| `crystal_cluster` | 9 | 38 → 40 |
| `transformer` | 8 | 89 → 134 |

### Prüfung und nächste Grenze

**215 Generator-Tests grün (141 s)**, darunter 20 reine Fragment-Geometrietests
(3,68 s): Volumen, Originalflächen/Materialrollen, freie Vertiefungen und schmale
Profilstellen, affine Transformationen und geschützter Rückfall bei ungültiger
Geometrie. Zwölf weitere aktuelle Seed-Fälle plus sechs Antennen-Form-/Höhenfälle
sind vollständig konvex und unter dem Shape-Budget. Generation 1/2 und intakte,
beschädigte, zerstörte Ausgabe erhalten ihre Digests.

Drei reale Modelle und drei isolierte Schüssel-/Isolator-/Sockelproben in einem
Blender-Prozess ohne Rendering exportiert. Echter Unity-Import/Reimport: **sechs
Quellen ohne Fehler oder Ablehnung**, 1 EditMode-Test grün (2,81 s). Die vorhandene
Physikfixture wird mit Profildaten und begrenzter Strahlstrecke wiederverwendet:
die Schüssel hat eine freie Vertiefung und einen festen Boden, keinen Durchgang.
Regulärer Renderer: 1 PlayMode-Test grün (0,60 s); mit Screenshot-Renderer:
1 Test grün (1,09 s), neun Bilder geprüft. Je Lauf insgesamt 30 serialisierte
Resets, gedrehte Modelle, Bewegung, Pause, Aufräumen, Wiedereintritt und erhaltene
Collider-Identitäten. Isolierte Proben: je ein Körper mit 24/6/5 Shapes.
Temporäre URP-Kopie ausschließlich zur Aufnahme; Produktionssettings erhalten.

Die zwölf verbleibenden Quellen benötigen Behandlung der tatsächlich verformten
Oberflächen. Nächste eng begrenzte Familie: verformte Kästen (`broken_wall`,
`burnt_console`, `fallen_pillar`). Dafür zuerst eine eindeutige Triangulierung
zwischen Render- und Kollisionsflächen nachweisen; keine pauschale konvexe Hülle.
Die neun radialen Quellen (`asteroid`, `cocoon`, `crashed_pod`, `floating_island`,
`hanging_crystals`, `rock`, `rubble_pile`, `scrap_heap`, `stalagmite`) benötigen
zusätzliche Prüfung der verformten Flächen und einer volumengetreuen Partition.
Genauer fester Rückfall bleibt bis dahin erhalten. Keine universelle Freigabe
beliebiger Parameter und keine neue automatische Gameplay-Freigabe.

Abschlussregression: **888/888 grün in 387 s**, sechs Stufen (213 Tier-0/EditMode,
9 Smoke, 143 gezielt, 62 Related, 241 weitere Full EditMode, 220 Full PlayMode).
Testkarte ohne Lücken und Skillprüfung ohne Befund. Kumulativer Vergleich gegen
die ursprünglichen Generation-3-Shards: im selben Prüfsatz **34 → 12 Quellen**,
22 geänderte und 153 unveränderte Digests. Belege im Unity-Worktree unter
`QA/Reports/Cubegen0106LatheProfiles/README.md`. Haupt-Checkout und installiertes
Blender-Add-on unverändert; Paket-/CLI-Version bleibt 0.10.5. Kein Commit, Tag,
Merge oder Release.


## Nacharbeit · verformte Kästen — Analyse vor dem Bau

Der Nutzer beauftragt Punkt 3 weiter. Die nächsten drei Familien sind
`broken_wall`, `burnt_console` und `fallen_pillar`. Ihre achtpunktigen Kästen
haben teils nicht plane Vierecke. Eine Prüfung der gemittelten Flächennormale
allein kann solche Flächen fälschlich für konvex halten. Vor einer Zerlegung
muss daher die Render-/Kollisionstriangulierung eindeutig sein.

Begrenzter Ansatz: ausschließlich die bestehende Kasten-Topologie (acht Punkte,
sechs bekannte Vierecke) behandeln. Die vorhandene Fächertriangulierung definiert
zwölf Außen-Dreiecke mit Originalmaterialien. Ein nachgewiesener innerer Punkt
teilt diese Fläche in höchstens zwölf Tetraeder; benachbarte Teile nur zusammen-
führen, wenn die Vereinigung konvex bleibt. Keine angenäherte Hülle, kein zusätz-
licher Physikkörper und keine allgemeine Zerlegung organischer Netze. Bei nicht
nachweisbarer innerer Lage, Nullvolumen, ungültiger oder invertierter Geometrie
bleibt die feste Kollision erhalten. Die Zerlegung betrifft Generation 3 im
fragmentierten Zustand; historische Generation 1/2 bleiben erhalten. Belegte
Modellfehler aktueller Varianten sofort korrigieren. Bestehende Fragmentphysik
und Export-/Importprüfungen wiederverwenden.

Prüfplan: Volumen/Außenflächen/Materialien, freie Vertiefungen, Transformationen,
invalides Netz, Seeds und Parameterformen; echte FBX mit expliziten Dreiecken,
Unity-Import/Reimport, Physik/Bewegung/Pause/Reset und Bilder. Der aktuelle Impact-
Plan verlangt weiterhin volle Regression wegen des uncommittierten Phase-5-Katalogs.
Haupt-Checkout, Add-on und Paketversion bleiben bis zur Integration unverändert.


### Umsetzung und Prüfsatz

Kästen mit acht Punkten und der vorhandenen Sechs-Viereck-Topologie erhalten
eine feste Fächertriangulierung. Zwölf orientierte Außendreiecke mit unveränderten
Materialrollen werden mit einem nachgewiesenen inneren Punkt verbunden. Positive
Teilvolumen und einmalige geschlossene Raumabdeckung (Raumwinkelsumme) sind
Voraussetzungen. Benachbarte Teile werden nur bei konvexer Vereinigung zusammen-
geführt; Abschlussflächen liegen innen. Bereits konvex triangulierte Körper
brauchen nur ein Shape, plane konvexe Kästen behalten ihre bisherige Ausgabe.

Die Ausgabe besteht ausdrücklich aus Dreiecken, die Renderer und Collider
gemeinsam verwenden. Nicht plane Kästen werden in Generation 3 vor dem üblichen
Voronoi-Schnitt behandelt: eine gemittelte Vierecknormale ist kein geeigneter
Konvexitätsnachweis. Ungültige/offene/invertierte/degenerierte Geometrie oder eine
fehlende innere Lage erhält keine dynamische Freigabe. Keine allgemeine Zerlegung
organischer Netze, keine Laufzeitzerlegung, keine zusätzlichen Rigidbodies.

`python3 -m tools.audit_fragment_profiles --baseline lathe`: 175 Typen, Master-Seed
42, Index 0, Generation 3. **12 → 9 Quellen mit nichtkonvexen Shapes**,
**172 Modell-Digests unverändert**. Verteilung der Kasten-Geometrie auf Voronoi-
Regionen kann sich durch den entfallenen ungeeigneten Schnitt ändern; Körperzahl
im Prüfsatz gleich oder geringer. Noch nicht ausdrücklich freigegebene Quellen
bleiben Dekoration.

| Quelle | Körper vorher → danach | Shapes vorher → danach |
|---|---:|---:|
| `broken_wall` | 8 → 7 | 37 → 41 |
| `burnt_console` | 8 → 8 | 41 → 49 |
| `fallen_pillar` | 9 → 9 | 22 → 28 |

### Sofort korrigierter Generatorfehler

Die Parameterprüfung fand einen eigenständigen Modellfehler: `fallen_pillar`,
Seed 42, Breite 2 m, ein Segment, Stumpf aktiv. Der nur aus der Breite abgeleitete
Zufallsversatz zog Stumpfecken unter dessen Grundfläche. Generation 3 begrenzt
den Versatz jetzt auf 60 % der tatsächlichen Stumpfhöhe; die Zufallsfolge bleibt
erhalten. Generation 1/2 bleiben historisch. Diese Modellkorrektur gilt auch für
intakte, beschädigte und zerstörte aktuelle Varianten und kann deren Geometrie
ändern; sie ist eine begründete Ausnahme zur sonst reinen Fragment-Nacharbeit.

Regression zeigt die alte Inversion und die erhaltene Grundfläche im aktuellen
Modell. Ein vorhandener Anker-Test verlangte bisher vollständige Vertexgleichheit
zwischen Generation 2/3. Seine bereits bestehende Kamerakorrektur-Ausnahme wird
um diesen belegten Modellfix ergänzt: Topologie, Materialrollen und Ankerprüfungen
bleiben erhalten; die neue Stumpf-Regression prüft das bewusst geänderte Verhalten.
Keine Golden-Daten oder Importtoleranzen verändert.

### Prüfung und verbleibende Grenze

**222 Generator-Tests grün (133 s)**; nach Korrektur der historischen Vergleichs-
annahme erneut vollständig geprüft. **34 gezielte Tests grün (8,62 s)**, darin
26 reine Fragment-Geometrie-/Seed-/Zustandsprüfungen sowie echte FBX-Regressions-
und Ankertests. Zwölf aktuelle Seed-Fälle plus zwanzig Parameterformen konvex und
unter dem Shape-Budget; zusätzlich drei echte Wandloch-Proben im reinen Geometrie-
vertrag frei. Generation 1/2 bleiben erhalten.

Gezielter Blender-Batch ohne Rendering: drei reale Standardquellen, breite kurze
Säule intakt/fragmentiert und drei isolierte Kastenproben. **Acht echte FBX ohne
Fehler oder Ablehnung**, 1 Unity-Import-/Wiederimporttest grün (4,27 s). Für die
isolierten Proben werden die echten FBX-Dreiecksindizes und Punkte mit der Quelle
verglichen; ein Bounds-/Dreieckszahlvergleich allein wäre unzureichend.

Gebündelte Physikprüfung: je Probe ein Körper mit 7/8/7 Shapes, freie Vertiefungen
und feste Flächen, gedrehte Modelle, Bewegung, Pause, Aufräumen, Wiedereintritt
und gleiche Collider-Identitäten. Insgesamt 30 serialisierte Resets je Lauf;
regulärer Renderer 1 Test grün (0,60 s), Screenshot-Renderer 1 Test grün (0,97 s),
neun Bilder geprüft. Keine Änderung der Produktionssettings und keine FPS-Aussage.
Zusätzliche Shapes/Innenflächen haben Kosten; vorhandene Budgets gelten weiter.

Abschlussregression: **888/888 grün in 387 s**, sechs Stufen (213 Tier-0/EditMode,
9 Smoke, 143 gezielt, 62 Related, 241 weitere Full EditMode, 220 Full PlayMode).
Testkarte ohne Lücken und Skillprüfung ohne Befund. Kumulativer Vergleich gegen
die ursprünglichen Generation-3-Shards: **34 → 9 Quellen**, 25 geänderte und
150 unveränderte Digests. Belege: `QA/Reports/Cubegen0106WarpedBoxes/README.md`.
Verbleibend sind neun Quellen mit verformten radialen Oberflächen: `asteroid`,
`cocoon`, `crashed_pod`, `floating_island`, `hanging_crystals`, `rock`, `rubble_pile`,
`scrap_heap`, `stalagmite`. Ihre genaue feste Kollision bleibt bis zu einer
nachgewiesenen passenden Zerlegung erhalten. Haupt-Checkout und installiertes
Add-on unverändert; Paket-/CLI-Version 0.10.5, Änderungen im lokalen Arbeitsstand
für 0.10.6. Kein Commit, Tag, Merge oder Release.

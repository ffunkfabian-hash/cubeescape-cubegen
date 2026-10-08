# Cubegen 0.10.5 · Versions- und Prüfbericht

Grundlage: 0.10.4.1, `549a263`, 7. Oktober 2026. Integrationsphase 4 von Cube Escape
und ausdrücklicher Folgeauftrag zur grundsätzlichen Kollisionskorrektur.
Am 8. Oktober 2026 vom Nutzer zur Version 0.10.5 sowie zum Commit/Merge freigegeben.
Paket, CLI und Blender-Add-on sind gemeinsam auf 0.10.5 gesetzt. Branch: `release/0.10.5`.
Die folgenden Arbeitsnachweise behalten ihren jeweiligen historischen Stand;
der Abschnitt „Release-Abnahme“ beschreibt den abschließenden Stand.

## Verbindlicher Auftrag für diese und kommende Phasen

Belegte Generatorfehler sofort korrigieren, mit Regression und echtem Unity-Nachweis.
Neue Befunde bis zur Veröffentlichung hier sammeln; veröffentlichte Berichte bleiben
historisch. Kein Verschieben bis zur nächsten Integrationsphase, keine Ablehnungsausnahmen.
Kollisionen an festen und bewegten Teilen, freie Öffnungen, Laufzeit und Reimport prüfen.

## Ursache der gehäuften Kollisionsfehler

`families.collision_boxes` nahm ohne explizite Collider oder Kollisionsrollen eine
Gesamthülle an. Das war für die Layoutschätzung brauchbar, aber für Gameplay falsch:
Unity erzeugt bei reinen Licht-/Drehrezepten keine solche Hülle. Die Qualitätsprüfung
meldete dadurch Deckung, obwohl das tatsächliche Exportrezept keine feste Kollision hatte.
Der Export-Kommentar behauptete denselben falschen allgemeinen Rückfall.

## Korrektur

- `quality.uncovered_geometry` prüft standardmäßig den tatsächlichen Gameplay-Import;
  die historische Gesamthülle bleibt nur als ausdrücklich gewählte Layoutschätzung.
  Pickups verwenden ihren Interaktionstrigger und werden nicht als feste Hüllen behandelt.
- Generation 3 ergänzt bei Gameplay-Rezepten ohne eigene Collider eindeutige
  Mesh-Collider an den Teilen. Feste Teile bleiben nichtkonvex: Türen, Käfige,
  Rohre und Tresore behalten Öffnungen. Bewegungsziele und ihre Kinder erhalten
  konvexe, mitbewegte Collider. Vorhandene explizite Rezepte werden nicht ersetzt.
  Generation 1/2 bleiben historische Ausgaben. Die anfangs ebenfalls ausgenommene
  zerstörte Dekoration wird durch die unten beschriebene Nachkorrektur für Generation 3 repariert.
- Beide Dampfventilformen exportieren feste Body-Kollision; eine vorhandene Wheel
  bekommt eine eigene bewegte Kollision. Eigener modellnaher Regressionstest.
- Die breitere Suite fand eine zweite Prüflücke: genaue feste Mesh-Collider wurden
  beim Anschlusscheck wieder als Gesamtbox behandelt. `MeshCollision` prüft die
  geschlossenen Geometrieteile als Vereinigung; die Öffnung bleibt auch im Prüfer frei.
- Physik-/Importtests und Kollisionsregressionen prüfen Fehlannahme, feste Öffnungen,
  bewegte Ziele, ältere Generationen, Pickups und 90 Phase-4-Modell/Seed-Kombinationen.

## Kompatibilität und Nachweise

Geometrievergleich ohne Kollisionsdaten gegen unverändertes 0.10.4.1-HEAD:
**4725 Modell-/Seed-/Style-/Generationsfälle ohne Abweichung**. Golden-Änderungen
betreffen die absichtlich ergänzten Collider, nicht Meshes, Pivots oder Materialrollen.
Echter Unity-Audit aller **175 aktuellen FBX-Typen bestanden**: 82 Gameplay,
85 statisch, 8 offene Pickup-Item-Zuordnungen, 0 Ablehnungen und 0 Fehler;
82,12 s. Generator-Suite **184/184 grün**, 162 s (41 Modell-, 12 Qualitäts-/Golden-,
131 übrige Tests). Strenger Qualitätscheck mit **1750 Varianten über 175 Typen**:
0 fehlende Kollisionsdeckung und 0 Fehler. Die abschließende Unity-Regression wird
unten ergänzt. Phase 4 erzeugt 13 ausdrücklich authorierte Spielvarianten;
ein Sidecar allein ist weiterhin keine Werkbank-Freigabe.

Belege: Cube-Escape-Worktree `9add`, `QA/Reports/Cubegen01041Phase4`.


## Unity-Abschlussprüfung · 8. Oktober 2026

**873/873 Tests grün, 374 s**, einschließlich Related und voller Regression:
222 EditMode, 12 Smoke, 135 Targeted, 67 Related, 227 weitere Full EditMode,
210 weitere Full PlayMode. Sieben gezielte Laufzeittests für die neuen Profile;
zehn Reset-Durchläufe je Falle/Bruchdeck. Laden in beiden Ansichten, Gefahrenschaden,
Materialisierungsbelegung, Becken und tatsächlicher Portal-Durchgang geprüft.
Sieben 1280×720-Zustandsbilder angesehen. Cube-Escape- und Generatorstand bleiben
uncommittiert; kein Release, Tag oder Merge. Die acht offenen Item-Zuordnungen des
breiten FBX-Audits betreffen weiterhin nicht freigegebene Pickup-Rezepte.

Finaler echter FBX-Audit mit verstärkten Kollisionsassertionen: **175 Quellen ohne Fehler**,
1 Test, 74,52 s. Nicht-Pickup-Gameplay muss reale feste Kollision besitzen;
Mesh-Collider unter einem Rigidbody müssen konvex sein. Keine Ablehnungsausnahmen.


## Nachkorrektur · statische und zerstörte Modelle (8. Oktober 2026)

Der Nutzer fragte zu Recht, ob zerstörte Dekoration weiterhin eine falsche Kollision
behält. Tatsächlich löschte `registry.generate_asset` nach der Zerstörung die Shapes;
der Unity-Import wählte für viele Typen daraufhin eine Gesamtbox. Diese konnte leere
Zwischenräume blockieren. Die vorige Formulierung war deshalb zu weit gefasst.

Auf den anschließenden ausdrücklichen Auftrag „alle Modelle passend“ wird auch die
statische Rückfallausgabe der aktuellen Generation 3 korrigiert:

- Statische Modelle ohne eigenes Shape-Rezept erhalten pro Mesh genaue nichtkonvexe
  Collider; dies gilt für intakte Dekoration und die übrig gebliebene zerstörte Geometrie.
  Leere Zwischenräume werden nicht mehr ersatzweise als Gesamtbox gefüllt.
- Eigene Kollisionsrezepte bleiben erhalten und müssen zu Form/Funktion passen.
  Ein einfacher Collider ist für eine wirklich solide einfache Form weiterhin geeignet.
- Generation 1/2 sind unveränderte historische Ausgaben, kein Reparaturnachweis.
  Schon exportierte Dateien ändern sich nicht automatisch: Reexport mit Generation 3
  und anschließender Reimport sind erforderlich.
- Neue Regressionen prüfen alle Typen mit mehreren Seeds, genaue Kollisionszuordnung
  zerstörter Varianten, freie Zwischenräume in intakten Trümmermodellen und den Erhalt
  alter Generationen. Echte neue FBX-/Unity-Nachweise werden nach dem Lauf ergänzt.

Dauerhafter Auftrag für weitere KI-Agenten: `AGENTS.md` in Cubegen und die globale
Asset-Regel in Cube Escape mit Ablauf in `ce-editor-assets`. Passende Kollision ist
für alle Modelle und relevanten Varianten Pflicht; allgemeine Hüllen/Bounds dürfen
keinen ungeprüften Physiknachweis ersetzen.


## Nachkorrektur · Kameraneigung und zerbrochene Exportflächen

Der Screenshot zeigte einen Vorzeichenfehler der Kastenkameras: Die Vorderseite liegt
auf Blender −Y, deshalb kippt eine negative X-Neigung nach oben. Generation 3 nutzt
nun positive 15–30° und schaut nach unten. Dieselbe Zufallsziehung bleibt erhalten;
Generation 1/2 und die bereits nach unten gerichtete Dome-Bauform bleiben historisch
unverändert. `test_camera_pitch.py` prüft 40 Seeds jeweils im Stillstand und mit beiden
Schwenkvorzeichen, zusätzlich den Erhalt der älteren Ausgabe. Der Generationenvergleich
im Ankertest nimmt diese beabsichtigte Meshkorrektur ausdrücklich aus; die Ankerprüfung
selbst bleibt für Kameras erhalten. Die beiden integrierten Cube-Escape-Kameras werden
mit ihren vorhandenen GUIDs neu exportiert/importiert.

Beim echten Audit zerstörter FBX fand sich am Kran eine nichtplanare, zerbrochene
Abschlussfläche. Unity verwarf diese Fläche samt Materialrolle. Der Blender-Builder
trianguliert jetzt zerstörte Generation-3-Meshes vor dem Export ausdrücklich und erhält
Material-/UV-Zuordnungen je ursprünglicher Fläche. Quelldreiecksbudget und Modellrezept
bleiben unverändert. Eine Blender-Regression prüft den echten FBX sowie die erhaltene
Fraktur-Materialrolle im GLB.

Echte Unity-Audits der erweiterten Kollision: **175 intakte Quellen bestanden**, 1 Test
in 75,98 s; **175 zerstörte Quellen bestanden**, 1 Test in 129,55 s. Der zerstörte
Kran wird vollständig mit Materialrollen und realen Mesh-Collidern importiert.
Finale Generator- und Unity-Regression samt Kamerabild folgen im Prüfarchiv.


Abschließende Generator-Suite: **191/191 grün**, 130 s (41 Modell-, 12 Qualitäts-/
Golden-, 138 übrige Tests). Neuer Geometrievergleich: **4725 Fälle, sieben absichtliche
Abweichungen ausschließlich an Generation-3-Kameras**; alle anderen Fälle identisch
zu 0.10.4.1. Die frühere Null-Abweichungsprüfung dokumentiert den Stand vor der Kamera-
korrektur. Bestehende Blender-Vorschauen übernehmen lokale Quelländerungen nicht
automatisch; erneute Generierung mit dem korrigierten Quellstand ist erforderlich.
Das installierte Blender-5.2-Add-on war anhand von 71 Quelldateien unverändert zu
0.10.4.1. Vor Aktualisierung wurde es als ZIP gesichert; 72 Dateien des geprüften
Arbeitspakets wurden übernommen und byteweise abgeglichen. Die laufende Sitzung
verwendet weiter die geladenen Module bis zum Neustart. Die ungespeicherte Szene
wurde nicht verändert. Sicherung: `dist/cubegen_blender_addon_0.10.4.1_vor_korrektur_20261008.zip`.

Das tatsächlich installierte Add-on wurde in einem separaten Blender-Prozess mit
Factory-Startup geladen und registriert: Kameralinse nach unten und genaue nichtkonvexe
Kran-Trümmerkollision bestanden. Keine Änderung der laufenden Nutzer-Sitzung.


## Abschließende Nachprüfung · 8. Oktober 2026

**873/873 Unity-Tests grün, 388 s**, fünf Stufen ohne Cache: 218 EditMode,
12 Smoke, 135 Targeted, 231 weitere Full EditMode und 277 weitere Full PlayMode.
Der tatsächliche FBX-Schwenktest belegt die Richtung nach unten für Box-/Dome-Kamera
und beide Vorzeichen während der Bewegung. Alle Phase-4-Laufzeitprüfungen bleiben grün.
Acht geprüfte Zustandsbilder einschließlich des neuen Kamerabildes. Belege im
Cube-Escape-Prüfordner `QA/Reports/Cubegen01041Phase4/followup/unity-final*`.
Generatorstand und Cube-Escape-Worktree bleiben uncommittiert; kein Release oder Merge.


## Release-Abnahme · 8. Oktober 2026

Der Nutzer hat Commit und Merge ausdrücklich beauftragt. Version 0.10.5 enthält die
Kollisionskorrekturen für Gameplay sowie statische/zerstörte aktuelle Modelle, genaue
Öffnungsprüfungen, korrigierte Kameraneigung und stabile zerstörte Exportflächen.
Paket, CLI, Blender-Add-on und README verwenden einheitlich 0.10.5. Release-Branch:
`release/0.10.5`; Ziel ist der bestehende GitHub-Standardbranch
`claude/quirky-galileo-bsz6fk`. Noch offene Pickup-Item-Zuordnungen bleiben ausdrücklich
außerhalb der Werkbank-Freigabe. Neue Befunde nach dieser Version gehören in den
nächsten unveröffentlichten Versionsbericht, auch in künftigen Integrationsphasen.

Release-Abnahme: Generator-Suite am Versionsstand **191/191 grün (133 s)**.
Die vollständige Cube-Escape-Regression ist vor Integration erneut vorgeschrieben.
Die bisherigen 191 Generator-/873 Unity-Tests,
350 intakten/zerstörten FBX-Audits und acht Bilder bleiben als Arbeitsbelege erhalten.

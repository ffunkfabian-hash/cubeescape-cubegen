# Cubegen 0.11.4 – Modellprüfung und Familien-Kits

> **Veröffentlicht mit 0.12.0** (10. Oktober 2026, Release-Zweig `release/0.12.0`, Bericht [VERSION_0.12.0.md](VERSION_0.12.0.md)).
> Die Angaben unten beschreiben den damaligen Arbeitsstand.

Arbeitsstand vom 9. Oktober 2026. Ausgangspunkt ist der lokale 0.11.3-Arbeitsstand;
CLI/Paket melden noch 0.11.2. Kein Release, Tag oder Paketversionswechsel wurde vorgenommen.

## Analyse vor dem Bau

Unity meldete zu kleine Portalflächen und eine falsche Wandmontage des Bodenportals. Diese beiden
Fehler liegen im Unity-Adapter/Vorschauvertrag und werden dort korrigiert. Die Generatorprüfung
belegt außerdem Modellfehler an Waschbecken, Wasserreservoir und Brückenpfosten. Modell-Kits
verwenden die vorhandenen Familien, keine zusätzliche Modell-Datenbank.

## Korrigierte Generatorfehler

- `washroom.style=sink`: Vollblock plus Metallplatte verschlossen das Becken. Generation 3 baut
  einen festen Boden, vier Randwände und einen Ablauf; die Vertiefung bleibt geometrisch und physisch frei.
- `coffee_machine`: Ein einziger massiver blauer Glaskasten war als Tank kaum erkennbar. Generation 3
  baut dünne Glaswände, Deckel/Bodenfassung, Halterung und Füllmarken; die Standvariante hat einen
  kompakteren Tank. Die vorhandenen Materialrollen bleiben erhalten.
- `retractable_bridge`: Die Statuslampen-Pfosten standen seitlich außerhalb der festen Auflage.
  Generation 3 verbindet sie durch feste, kollidierende Halterungen mit dem Gehäuse. Pfosten sind
  Statusanzeigen am festen Brückenende; sie fahren nicht mit dem Deck mit.
- Familienauflösung: Ein Overlay wie `Kits/lab.json`, das `family: lab` verwendet, wurde wegen seines
  Dateinamens als neue dimensionslose Familie behandelt. Bekannte Familien werden für Overlays ohne
  eigenen `dims`-Vertrag jetzt aus dem eingebauten Familienvertrag geladen. Explizite Familiendefinitionen
  mit `dims` bleiben möglich. `tests/test_wave_0114.py` reproduziert den Fehler.

Historische Modellgenerationen 1/2 bleiben unverändert. Neue Geometrie verändert ausschließlich
Generation-3-Digests der drei betroffenen Typen; Golden- und Qualitätsdaten wurden gezielt angepasst.
Der Anker-Wächter nimmt diese ausdrücklich korrigierten Meshes vom früheren Gleichheitsvergleich
mit Generation 2 aus; Ankerprüfungen und historische Golden-Nachweise bleiben bestehen.

## Inhalt

Sieben kompakte Kits mit je neun statischen Modellen: Station, Gießerei, Labor, Krankenstation,
Wrack, Gewächshaus und Reaktor. Jeweils 38 Anschlussprüfungen ohne Abweichung. Weitere zwölf
Modelle aus IDEEN.md ergänzen Bauabschlüsse, Böden/Decken, Rampen und organische/Gesteinsdekoration.
Ein Deckenpaneel verwendet den bereits freigegebenen SignalLight-Vertrag; keine neue Mechanik.
Unity bietet Kategorien-/Kitsuche, gemerkte Kategorien als Schnellzugriff und beliebige datenbasierte
Kit-Mitgliedschaften. Die weitere Gameplay-Freigabe vollständiger Familien bleibt ein eigener Schritt.

## Prüfung

- 248 Python-Tests grün mit `python3 tools/run_tests.py` (204 s): Modelle 41, Qualität/Golden 12,
  übrige 195 einschließlich Blender-FBX-Audit. Die Rezeptprüfung validiert jetzt JSON-Dateien rekursiv,
  damit neue Kit-Unterordner vollständig geprüft werden; sieben Rezepttests zusätzlich grün.
- Vier neue Regressionstests: freies Waschbecken mit festem Boden, beide Reservoirformen,
  feste Pfostenhalterungen und Familienoverlay-Auflösung. Anker-/Regressionsteil sieben Tests grün.
- 54 historische Golden-Digests der drei korrigierten Typen (Generation 1/2, jeweils 18) gegenüber
  dem vor der Änderung gespeicherten Zustand identisch.
- Sieben Familienexporte mit jeweils 38 geprüften Anschlüssen ohne Abweichung; 75 neue Modelle
  exportiert und über den vorhandenen Unity-Katalog integriert.
- Unity: 921/921 Prüfungen grün im vollständigen Stufenplan (832 s inklusive Import/Kompilierung):
  276 EditMode, 12 Smoke, 224 Targeted, 196 weitere Full EditMode und 213 Full PlayMode.
- Zusätzlich 24 gezielte EditMode-Prüfungen (2,94 s), 20 UI-/Portal-/Screenshotprüfungen (7,88 s),
  Mausklick auf den Boden für das Bodenportal und kleinere Bildschirmprobe (2 Prüfungen, 1,34 s).
- Echte externe FBX in Unity importiert und erneut importiert: 78 Modelle, davon 76 statisch und
  2 Gameplay (Deckenpaneel/Brücke), ohne Warnung/Ablehnung/Fehler; Hierarchie, Materialreferenzen,
  Kollision und Wiederimportstabilität geprüft (1 Batchprüfung, 70,99 s). Eindeutige Texturmanifeste
  für die Prüfquellen erhalten die bestehende Eigentümerprüfung.
- 32 Browser-/Werkbankbilder bei 1470 × 956 und 1280 × 800 angesehen. 75 neue Modelle integriert,
  Bestands-IDs erhalten. Endabgleich des Builders schreibt auch das neue Signal-Deckenpaneel
  direkt in den gespeicherten Katalog; kein manueller Menüschritt nötig.

Nachweise im Cube-Escape-Worktree: `QA/Reports/ModelReview/abnahme.json`, `exports.json`,
`identitaeten.json`, vollständige Unity-Ergebnisse und Generatorprotokoll; Bilder unter
`Docs/Images/ModelBrowser/review_*`. Sämtliche neuen Typ-/Verhaltensfreigaben bleiben auf die
beschriebene Verwendung begrenzt; die visuelle Prüfung ist keine pauschale Abnahme aller Bestandsmodelle.

Ein erster Volltestlauf scheiterte ausschließlich an der bisherigen flachen Rezept-Dateisuche, die
`recipes/kits` als Datei öffnete. Die rekursive Prüfung korrigiert das; der abschließende vollständige
Gruppenlauf ist grün. Keine fehlschlagenden Prüfungen wurden entfernt.

## Maschinenlesbarer Katalog für die Werkbank

`cubegen catalog --json` liefert das Format `catalog: 1`: alle registrierten Typen mit tatsächlichen
Parameterschemata, Stil-/Texturoptionen aus dem `generate`-Parser, Familien und Paletten. Referenzverhalten
und Maße stammen aus einem Seed-0-Bau ohne Blender. Diese Angaben sind eine UI-Hilfe; die Freigabe prüft
der echte Laufzeitimport anhand jedes erzeugten Sidecars. `--out` schreibt UTF-8-JSON in eine Datei.

Fünf Katalogtests prüfen Vollständigkeit gegen Registry/Parser, Familien/Paletten, Referenzverhalten und
deterministische JSON-Ausgabe. Cube Escape liest den Katalog im Hintergrund und erhält deutsche Parameter-
beschriftungen unabhängig von der Prozess-Locale mit explizitem UTF-8. Der Paketstand meldet weiter 0.11.2.
Die bisherigen Geometriegenerationen und historischen Nachweise bleiben unverändert.

## Standardmodelle: Spinde, Betten, Bodenluken und Stegkreuzungen

Nutzerbilder aus der Cubegen-Werkbank zeigen verdeckte Spindfächer, eine durchgehende Absturzsicherung vor dem Leitereinstieg und einen kleinen orangefarbenen Wartungsdeckel in der Ecke einer großen Bodenplatte. Generation 3 korrigiert diese Formen: Spindkorpus als Rückwand/Trennwände/Boden mit zwei sichtbaren Ablagen und Kleiderstange statt massivem Block, geteilte vordere Bett-Sicherung mit 46 cm Einstieg und zusätzlicher hinterer Sicherung, mittiger Boden-Wartungsdeckel mit Rahmen, Scharnieren, Griff und umliegender Plattenaufteilung. Boden-Wartungsdeckel bleiben statische geschlossene Dekoration.

Stegkreuzungen besitzen bereits Geländerlinien mit offenen Anschlüssen. Die bisherigen abgeschrägten Geländerprimitiven überschritten bei großen Kreuzungen das normale Dreiecksbudget. Generation 3 verwendet dort einfache feste Geländerprofile; freie Anschlüsse, Collider und Höhe bleiben erhalten. Das ermöglicht die erneute strenge Freigabe aller Kreuzungsformen mit Geländer. Bestehende Generationen 1/2 bleiben bytegleich in ihren Golden-Fingerprints.

Fünf neue Regressionen prüfen freie Spindfächer und feste Ablagen, den tatsächlichen Leitereinstieg und die hintere Sicherung, mittige eingefasste Luken, Geländerbudgets/freie Steganschlüsse sowie Kollisionsdeckung in intakten, beschädigten, zerstörten und fragmentierten Zuständen. Die vorhandene Anchor-Regression berücksichtigt die absichtlichen Generation-3-Geometriekorrekturen; historische Ausgaben werden weiterhin separat geprüft. Nur 16 aktuelle Golden-Fälle der vier korrigierten Typen aktualisiert; alle 72 historischen Fälle dieser Typen unverändert. Vollständige Python-Suite: 258 Prüfungen grün (261 s).

Cube Escape ergänzt und erneuert daraufhin seine Standardsets über tatsächliche GLB-/FBX-Exporte. Das Türschild TUER war ein dort gesetzter Rezeptparameter, kein Generatorstandard; die Standardrezepte lassen die optionale Beschriftung nun weg. Unity-Import-/Physik-/Bildnachweise werden im Systemdoc der Integration dokumentiert.

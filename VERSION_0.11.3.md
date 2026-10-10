# Cubegen 0.11.3 – zweite Stationswelle und vollständige Stegkollision

> **Veröffentlicht mit 0.12.0** (10. Oktober 2026, Release-Zweig `release/0.12.0`, Bericht [VERSION_0.12.0.md](VERSION_0.12.0.md)).
> Die Angaben unten beschreiben den damaligen Arbeitsstand.

Arbeitsbericht vom 9. Oktober 2026, unveröffentlicht und uncommittet.
Ausgangsstand: `/Users/ffunk/cubegen`, CLI/Paket/Quell-Add-on 0.11.2.
Keine Paketversion oder Veröffentlichung wurde vorgezogen.

## Analyse und Umfang

Cube Escape führt Standard-, Cubegen- und Kit-Modelle in einer gemeinsamen funktionalen Kategorienliste
zusammen. Fünf zusätzliche Gruppen: Labor/Medizin, Lager/Transport, Wartung/Werkzeuge,
Aufenthalt/Versorgung und Sicherheit/Notfall. Das Rezept `recipes/station_wave2.json` erzeugt
28 Modelle aus bereits registrierten Typen; die Registry bleibt bei 186 Typen. Natur/Ruinen/Roboter
werden zusätzlich befüllt. Die Auswahl und Freigabeverträge stehen in [IDEEN.md](IDEEN.md).

## Fehler: eingestürzter Steg hatte nur Bodenkollision

**Fund:** `collapsed_catwalk`, Generation 3, Seeds 0, 7, 113 und tatsächlicher Wave-2-Export.
Der Builder authorierte nur die gedrehte 8-cm-Bodenbox. Dadurch blieb der automatische
Fallback für `Wreck` und `Rubble` aus; die stehenden Stützen, Geländer und Trümmer waren nicht fest.
Ein Stützen-Innenpunkt des reproduzierbaren Beispiels `(−0,6; 1,349; 0,814)` war von keinem Shape gedeckt.
Die allgemeine Qualitätsprüfung meldete dennoch keine Lücke: ihre Mindestvolumen-/Dickenfilter
sind für dünne Stützen kein vollständiger Physiknachweis.

**Ursache und Korrektur:** `cubegen/models/wrecks.py` behält die historische Bodenbox nur für
Generation 1/2. Generation 3 überlässt die Kollisionsvervollständigung dem vorhandenen statischen
Fallback: genaue nichtkonvexe Mesh-Collider für `Wreck` und `Rubble`. Öffnungen und Trümmerzwischenräume
bleiben frei. Kein neuer Kollisionsmechanismus, keine zusätzliche Box über die gesamte Ruine.

**Kompatibilität:** Alle 27 Golden-Geometriefälle (Vertices, Faces, Materialien, Pivots und Parents)
des Typs vor/nach der Änderung identisch. Generation 1/2 behalten ihre Digests. Acht Generation-3-Digests
ändern sich durch die Kollision; gezielt in `tests/golden.json` aktualisiert. Zerstörte Modelle besaßen
bereits den vollständigen statischen Fallback. Alle Wave-2-Exporte wurden danach neu erzeugt;
Unity reimportiert mit erhaltenen GUIDs und fileIDs.

## Tests und Grenzen

`tests/test_wave_0113.py` prüft den vollständigen Wellenvertrag, deterministische Seeds,
Kollisionsdeckung für 28 Typen × drei Zustände × drei Seeds und explizit beide Stegstützen.
Historische Generationen werden separat belegt. 243 Python-Tests bestanden in 253,9 s; die vier gezielten Wellen-/Stützenprüfungen zusätzlich
bestanden in 1,0 s (die vierte Prüfung wurde nach Start der vollen Suite ergänzt). Der echte FBX-Audit
aller 28 korrigierten Exporte weist 0 Ablehnungen und 0 offene Item-Zuordnungen aus.
Cube Escape: 917 Prüfungen der vollen Regression grün in 495 s (232 Tier-0/EditMode,
10 Smoke, 192 Targeted, 39 Related, 237 Full EditMode, 207 Full PlayMode). Abschließend
14 Kategorie-/Wellenprüfungen grün (0,32 s), 18 UI-/Laufzeit-/Screenshotprüfungen grün (2,57 s).
Alle acht Browseransichten bei 1470 × 956 visuell geprüft. Der tatsächliche CharacterController
wird an beiden Stegstützen gestoppt; der Raum zwischen ihnen bleibt frei, das Deck trägt ihn.
Roboterkörper sind fest und bleiben stationär.

Ein isolierter Unity-Import-/Wiederimport-Audit importiert alle 28 echten FBX (13,0 s, eine
explizite Batchprüfung) und prüft Hierarchie, Materialien, Collider sowie erhaltene Identitäten.
Audit-Präfix `Gen_Wave2Audit_`, separates Texturset `wave2audit`: Beim ersten Versuch mit erneut
kopiertem Stationstexturmanifest griff der Material-Eigentumsschutz korrekt ein (neue Manifest-GUID,
bereits belegte Materialnamen). Der Schutz bleibt unverändert; keine fremden Materialien überschrieben.

Nachweise im Cube-Escape-Arbeitsbaum `1489`: `QA/Reports/CubegenWave2/abnahme.json`,
`QA/Reports/CubegenWave2/exports.json`, `Docs/Images/ModelBrowser/wave2_*.png`.
Die abschließende Schrift-/Standard-Prop-Zuordnung wurde durch die gezielten Prüfungen nach
der vollständigen Regression abgesichert.

Die vier Roboter sind stationäre Modelle mit vorhandener SignalLight-Funktion, keine NPCs mit Bewegung.
Die anderen 24 Modelle sind statisch; Labor/Kryo/Küche/Automaten besitzen keine neue Gameplay-Logik.
Die Zustandsmatrix in Python ersetzt nicht die Physikprüfung jeder denkbaren Parameterkombination.
Die produktiv integrierte Welle enthält die oben genannten expliziten intakten Rezeptformen.

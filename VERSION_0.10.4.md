# Cubegen 0.10.4 · Releasebericht

Grundlage: veröffentlichte 0.10.3 (`a947827`), Integrationsphase 3 in Cube Escape,
7. Oktober 2026. Auf Nutzerauftrag als **0.10.4** auf Branch `release/0.10.4` veröffentlicht.
Paket, CLI und Blender-Add-on werden gemeinsam auf 0.10.4 aktualisiert.

## Verbindlicher Auftrag für diese und kommende Phasen

Belegte Cubegen-Fehler sofort im Generator korrigieren, Regressionstest ergänzen und hier
Fund, betroffene Varianten/Seeds, Ursache, Korrektur und erneuten echten Unity-Nachweis
festhalten. Keine Ablehnungsausnahmen oder gelockerten Importprüfungen als Reparatur.
Die Regel gilt auch für alle späteren Integrationsphasen. Veröffentlichte ältere Berichte
bleiben historisch; neue Befunde gehören in diesen nächsten Versionsbericht.

## Phase 3 · Schwenkrichtung

- `sweep_rotator` buk immer den Startwinkel −arc/2 (Unity) ein. Bei negativer
  Geschwindigkeit schwenkt `Rotator` weiter ins Negative: bei 90° entsteht −45° bis −135°
  statt −45° bis +45°. Die Vorrotation folgt jetzt dem Vorzeichen: positiver Speed
  startet links, negativer rechts; beide decken denselben symmetrischen Bereich ab.
- Kamera und Geschütz erlaubten trotz des vorzeichenfähigen Laufzeitvertrags keine
  negative Geschwindigkeit. Parameterbereiche jetzt −180..180 bzw. −360..360;
  README-Parametertabelle mit dem bestehenden Werkzeug neu erzeugt.
- Ein ausdrücklich gesetztes `speed: 0` wurde bei `sweep > 0` zu 30°/s geändert.
  Generation 2/3 respektiert jetzt den ausdrücklich angeforderten Stillstand.
  Impliziter Sweep ohne Speed-Vorgabe und Generation 1 bewahren den historischen
  30°/s-Vertrag; Generation 1 bleibt geometrisch kompatibel.
- Regressionen: Spiegelung der gesamten Zielgeometrie bei Kamera/Geschütz (Seed 42),
  expliziter Stillstand und Generation-1-Kompatibilität. Bestehender positiver
  Sweep-Test bleibt unverändert.

Prüfstatus: abgeschlossen; siehe abschließende Nachweise unten.

## Phase 3 · fehlende Druckplatten-Kollision

Echter Laufzeitbefund: Der Roboter fällt durch die Druckplattenfläche; das Sensor-Signal
verschwindet sofort. Die Generation-3-Sidecars von `pressure_plate` enthielten weder
eine feste Grundfläche noch einen Collider am bewegten `Plate`. Das Anzeiger-Rezept
allein erzeugt diese Flächen nicht. Quadratische und runde Platten exportieren jetzt
konvexe Mesh-Collider für `Body` und `Plate`; die Kollisionskontur folgt der Form und
die Deckfläche bewegt sich mit. Generation 1/2 bleiben unverändert. Unity weist den
Sensor ausdrücklich zu und setzt den bewegten Deck-Collider kinematisch.
Regression prüft beide Formen und die erhaltene Generation-1-Ausgabe.

## Phase 3 · Kamera-/Geschütz-Kollision

Die volle Unity-Regression fand das gleiche fehlende Kollisionsfundament an den
veröffentlichten Schwenk-Beispielen: Kamera und Geschütz hatten keine solide Fläche.
Generation 3 exportiert jetzt `Body`/`Rotor` beziehungsweise `Body`/`Turret`/`Gun`
als konvexe Mesh-Collider; verschachtelte Teile bleiben an ihrem bewegten Parent.
Generation 1/2 bleiben unverändert. Regression prüft beide Richtungen und alte Generationen.
Die Golden-Referenzen werden ausschließlich für die absichtlich ergänzten Collider
der drei betroffenen Typen aktualisiert; Geometrie, ältere Generationen und zerstörte
Varianten bleiben unverändert.

## Abschließende Nachweise (7. Oktober 2026)

- **170 Generator-Tests grün**: 41 Modell-, 12 Qualitäts-/Golden- und 117 übrige Tests,
  einschließlich echtem Blender-/Add-on-Export. Gruppen-Testzeiten 75,9 / 74,9 / 132,2 s;
  Orchestrierungslog 1313 s Wandzeit. Vier neue Regressionen, bestehender Sweep-Test unverändert.
- **14 aktuelle Generation-3-Beispiele** im Cube-Escape-Worktree `f8ac`, feste Seeds,
  Namen und Parameter. Alle Quellen mit den lokalen Korrekturen exportiert. Paket-
  und Sidecar-Metadaten melden weiterhin den installierten 0.10.3-Arbeitsstand.
- **16 echte externe FBX** im zusätzlichen aktuellen Unity-Audit, einschließlich
  positivem/negativem Sweep und explizitem Stillstand: keine Ablehnungen, keine
  offenen Item-Zuordnungen und keine Importfehler. Ein Batchtest grün (2,88 s Testzeit).
- **859 Unity-Tests grün**, einschließlich voller Regression (378 s). Zehn gezielte
  Laufzeittests grün (4,03 s), wiederholbarer Reimport mit erhaltenen GUIDs/fileIDs,
  keine Asset-Abweichungen nach dem finalen Lauf. Neun 1280×720-Bilder angesehen.
- Belege, Exporte-Rezepte, Seeds/Hashes, Generator-Patch, Regression und komprimierte
  Unity-Logs: `<Cube-Escape-Worktree>/QA/Reports/Cubegen0103Phase3`.

Die anfänglichen Fehlläufe bleiben im Prüfbericht erhalten. Keine Importtoleranz oder
Ablehnungserwartung wurde gelockert. Bewusst ergänzte Collider begründen die 24
aktualisierten Golden-Fingerprints; alle alten Generationen und zerstörten Fälle
bleiben erhalten. Der Release-Auftrag für 0.10.4 umfasst Commit, Integration und einen
neu gebauten Add-on-ZIP. Die unten dokumentierten Phase-3-Quellen bleiben als tatsächlich
geprüfte 0.10.3-Exporte erhalten; eine reine Versionsänderung erzeugt keine neue Geometrie.

## Release-Prüfung 0.10.4

Auf dem einheitlichen 0.10.4-Stand erneut **170/170 Tests grün** (135 s Wandzeit):
41 Modell-, 12 Qualitäts-/Golden- und 117 übrige Tests. Die Versionsprüfung und
der echte Blender-/Add-on-Smoke bestätigen Paket, CLI und ZIP mit derselben Version.
Das installierbare Paket liegt unter `dist/cubegen_blender_addon.zip`.
GitHub-Integration erfolgt über `release/0.10.4`; der Branch bleibt erhalten.

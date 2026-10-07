# Cube Escape Generator – Version 0.10.3

## Release vom 7. Oktober 2026

Auf Nutzerauftrag wird der Stand 0.10.2.5 als 0.10.3 fortgeführt. Paket, CLI und
Blender-Add-on melden einheitlich 0.10.3. Geometrie, Seeds, Modellnamen und Unity-Vertrag
bleiben unverändert; die Unity-Nachweise unten beziehen sich auf den tatsächlich
geprüften 0.10.2.5-Exportstand, nicht auf einen zusätzlichen Volltypen-Audit von 0.10.3.

Beim Release-Abgleich wurde eine Metadatenabweichung gefunden: Das Add-on in 0.10.2.5
meldete noch 0.10.2.4. Die Korrektur auf 0.10.3 wird durch zwei neue Versions-Regressionen
sowie den echten Blender-Installations-/Export-Smoke abgesichert. Der Validierungsberichtstest
liest die aktuelle Paketversion statt eine historische Patchnummer festzuschreiben.

Release-Prüfung: **166 Tests grün** (41 Modell-, 12 Qualitäts-/Golden-, 113 übrige Tests),
einschließlich realer Blender-Installation, Reinstallation und FBX-/Palettenexport.
Die ersten beiden Gruppen bestanden in 74 bzw. 73 Sekunden; die übrige Gruppe wurde nach
Korrektur des zusätzlichen Test-Modulpfads vollständig erneut ausgeführt.
Das installierbare ZIP wurde neu gebaut und meldet ebenfalls 0.10.3.

## Arbeitsauftrag und Grundlage

Nutzerauftrag vom 7. Oktober 2026 für die laufende Cube-Escape-Integration und alle folgenden
Phasen: belegte Generatorfehler sofort hier im Generator korrigieren, einen Regressionstest
ergänzen und in diesem Dokument festhalten. Fund, betroffene Varianten/Seeds, Ursache,
Korrektur, Generatorprüfung und erneuten echten Unity-Nachweis dokumentieren. Importprüfungen
nicht lockern und keine Ablehnungsausnahmen als Reparatur verwenden.

Grundlage für Integrationsphase 2: **0.10.2.5**, Commit `0c125f2`, 175 registrierte Typen;
Blender 5.2.2 LTS und ImageMagick lokal geprüft. Die elf neuen experimentellen Typen gehören
nicht automatisch zum geprüften Unity-Gameplay-Vertrag. Die 0.10.1-/0.10.2-Korrekturen bleiben
historisch im veröffentlichten `CHANGELOG.md`.

## Befunde aus Integrationsphase 2

Phase 2 abgeschlossen und vom Nutzer zum Commit und Merge abgenommen. **Kein belegter Generator-Codefehler** in
diesem Prüfumfang; deshalb keine Generator-Codeänderung oder vorgezogene Versionsanhebung.

- Sieben veröffentlichte Cube-Escape-Quellen aus 0.5.0 mit 0.10.2.5/Generation 3 reexportiert.
  Namen, Seeds, bisherige Rezeptparameter, Gesamtmaße, Import-Metas und GUIDs bleiben erhalten.
  Echter Austausch/Reimport erhält Modell-/Gameplay-fileIDs und gespeicherte Platzierungs-,
  PersistentId- und Türgeschwindigkeits-Overrides. Sechs Palettenquellen unverändert.
- Sechs ausdrückliche `params.item_id`-Zuordnungen im externen Prüf-Rezept:
  Energiezelle → `energy_cell`, Batterie → `servo_battery`, vier Karten →
  `keycard_red/blue/green/yellow`. Unity löst alle realen `ItemData` auf.
  Zange, Hinweis, Sicherung, Kabelrolle usw. bleiben ohne konkreten Content-Vertrag ohne Freigabe.
- Je elf intakte/beschädigte echte FBX für historische Pivot-, Luftschleusen-, Geometrie-
  und Collider-Befunde, zusätzlich eine Generation-1-Luftschleuse: alle ohne Importfehler.
  Insgesamt fünf explizite Unity-Batches mit 36 Quellen, keine Ablehnungsausnahmen.
- Generator-Suite: **164 Tests grün**, 120 s (41 Modell-, 12 Qualitäts-, 111 übrige Tests).
  Cube-Escape-Impact-Plan: **210 Tests grün**, 261 s (135 EditMode, 2 Smoke, 24 Targeted,
  49 Related). Zusätzlich 4 Laufzeittests grün und acht Unity-Screenshots geprüft.
- Der erste Projektlauf fand einen veralteten Unity-Test, der jede Root-Box an einer
  Treppe verbot. Generation 3 liefert getrennte Stufenboxen; der Test prüft jetzt reale
  Stufenhöhen und Begehbarkeit. Das war eine Testerwartung, kein Generatorfehler.

Belege im Cube-Escape-Worktree `0b24` unter `QA/Reports/Cubegen01025Phase2`;
Systembericht `Docs/CUBEGEN_IMPORT.md`, Abschnitt Phase 2. Der frühere 0.10.0-Abgleich und
die bereits veröffentlichten Fehlerkorrekturen bleiben als historische Nachweise erhalten.
Neue Fehler aus folgenden Phasen werden mit Ursache, Korrektur und Nachprüfung hier ergänzt.

Dieser Bericht dokumentiert den Release-Stand 0.10.3. Weitere Integrationsbefunde werden
mit Ursache, Regression und Nachprüfung nachvollziehbar ergänzt; spätere Codekorrekturen
erfordern einen eigenen neuen Release-Stand.

Seit Integrationsphase 3 werden neue Befunde im nächsten Arbeitsbericht `VERSION_0.10.4.md`
gesammelt. Dieser veröffentlichte 0.10.3-Bericht bleibt der historische Release-Nachweis.

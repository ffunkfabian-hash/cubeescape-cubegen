# Cubegen 0.11.2 · Erste Asset-Welle aus IDEEN.md, Varianten und Prototyp-Kollision

> **Veröffentlicht mit 0.12.0** (10. Oktober 2026, Release-Zweig `release/0.12.0`, Bericht [VERSION_0.12.0.md](VERSION_0.12.0.md)).
> Die Angaben unten beschreiben den damaligen Arbeitsstand.

Stand: 9. Oktober 2026. Version 0.11.2, Arbeitszweig `release/0.11.2` (uncommittet, kein Release-Commit/Tag).
Paket, CLI, Blender-Quell-Add-on, eigenständiges ZIP (`dist/cubegen_blender_addon_0.11.2.zip`) und das lokal
installierte Blender-Add-on (Blender 5.2) melden einheitlich **0.11.2**.

0.11.1 wurde nie veröffentlicht: Paket, CLI und Add-on standen bis zu dieser Version auf 0.11.0. Der offene
Bericht [VERSION_0.11.1.md](VERSION_0.11.1.md) (Integrationsprüfung des Modell-Browsers ohne Generatorbefund)
bleibt unverändert erhalten; sein Inhalt ist Teil dieses Stands.

## Auftrag

1. Modellkategorien in Cube Escape nach Funktion und Erscheinung ordnen, Cubegen als Herkunft erhalten.
2. Ausrichtung der Vorschaumodelle (Bilder und 3D-Vorschau) prüfen; Fehler der Vorschau in Cube Escape,
   belegte Generatorfehler in Cubegen beheben.
3. Erste priorisierte Asset-Welle aus [IDEEN.md](IDEEN.md) umsetzen: vorhandene Registry-Bausteine prüfen und
   einsortieren; Kandidaten `airlock_chamber`, `pipe_rack`, `ceiling_beam`, `pressure_tank`, `turbine`,
   `compressor`, `relay_box`, `diagnostics_port`, `coolant_loop`, `warning_beacon`, `emergency_case`;
   `iris_door`/`maintenance_hatch` bevorzugt als Varianten, `access_panel` als Panel-Komponente.
4. Version 0.11.2, Dokumentation, Abnahme mit echten FBX in der Cube-Escape-Testkopie.

## Analyse vor dem Bau

**Bestand:** 175 Typen. Für jeden Kandidaten wurde zuerst geprüft, ob Typ, Variante oder Kit den Bedarf abdecken:

| Kandidat | Nächster Bestand | Entscheidung |
|---|---|---|
| `airlock_chamber` | `door` (Stil `airlock`), `bulkhead`, `cargo_container` | neuer Typ: begehbare Kammer mit zwei Türrahmen – eigene Silhouette, kein Türstil |
| `pipe_rack` | `pipe`, `pipe_bend`, Prototyp `test_pipe_rack` | neuer Typ auf Basis des Prototyps (I-Profil-Stützen, Hohlrohrläufe) |
| `ceiling_beam` | `ceiling_module` (Platte mit Kassetten), `ceiling_panel` | neuer Typ: freier Träger ohne Platte; Deckenansicht (`view: below`) |
| `pressure_tank` | `tank` (stehender Lagertank) | neuer Typ: Druckbehälter mit gewölbten Böden, liegend/stehend |
| `turbine` | `fan`, `generator` | neuer Typ: Gehäuse mit Ansaugglocke und Abgasschacht |
| `compressor` | `pump` | neuer Typ: Kolbenkompressor mit Zylinderköpfen und Behälter; Motorrippen wie `pump` |
| `relay_box` | `fuse_box`, Prototyp `test_relay_box` | neuer Typ: Relais-/Verteilerkasten ohne Sicherungsmechanik |
| `diagnostics_port` | `chip_reader`, `cable_plug` | neuer Typ: Serviceanschluss mit Rundsteckbuchse, Klappe, Kabel |
| `coolant_loop` | `pipe`/`pipe_bend`, Prototyp `test_coolant_loop` | neuer Typ: geschlossene Schleife mit Wärmetauscher, innen frei |
| `warning_beacon` | `emergency_light` (Wand-Rundumleuchte), Prototyp `test_warning_beacon` | neuer Typ: stehende Signalsäule mit Leuchtstufen |
| `emergency_case` | `medkit` (Schrank mit Kreuz) | neuer Typ: Wandkasten mit Glastür und Inhalt |
| `iris_door` | `door` | **Variante** `door.variant=iris` |
| `maintenance_hatch` | `hatch` | **Variante** `hatch.variant=maintenance` |
| `access_panel` | `keypad` | **Variante** `keypad.variant=access` (Kartenleser-Modul, Haube, Statusleiste) |

**Golden Rule und Kompatibilität:** Varianten sind stille Optionen (`quiet`) ohne Zufallsverbrauch: Bestehende Seeds
von `door`, `hatch`, `keypad` und allen anderen Typen bleiben bitgleich (Golden-Test). Neue Typen ändern keine
bestehende Ausgabe. Die Prototypen `test_*` bleiben registriert (Namen sind Verträge).

**Modell- und Gameplay-Freigabe getrennt:** Alle elf Typen sind standardmäßig **statische Modelle** (keine
Behaviours) und erhalten in Generation 3 genaue nichtkonvexe Mesh-Collider je Teil. Gameplay-Skripte gibt es nur
auf ausdrücklichen Wunsch: `turbine.machine` (Machine + Rotator, bewegter Rotor konvex), `compressor.machine`
(Machine), `warning_beacon.signal` (SignalLight auf dem einteiligen `Glow`). Die Varianten `hatch.maintenance` und
`keypad.access` behalten Deckel-/Statusskript ihres Basistyps; `door.iris` ist statisch, weil Unitys `Door` nur
lineare Blätter kennt.

## Korrekturen

### Prototypen füllten ihre Zwischenräume mit einer Gesamtbox (Kollision)

- **Fund:** Alle zehn `test_*`-Prototypen exportierten genau einen Box-Collider über die ganze Bounding Box.
  Belegt in Generation 3, Seed 1: `test_pipe_rack` 2,24 × 0,4 × 1,69 m vom Boden bis über die Rohre (der freie
  Raum unter dem untersten Rohrlauf war fest), `test_utility_trench` füllte seinen U-Kanal, `test_coolant_loop`
  das Innere der Schleife, `test_magnetic_lock` den Kanal.
- **Ursache:** `gameplay_tests._mark` setzte `asset.collider(bbox)`; damit übersprang
  `collision.complete_static_collision` die genaue Mesh-Kollision.
- **Korrektur:** Ab Generation 3 setzt `_mark` keine Box mehr; jedes Teil erhält einen genauen Mesh-Collider.
  Generation 1/2 behalten die historische Box bitgleich.
- **Geprüft:** Alle zehn Prototypen in Generation 3 nur nichtkonvexe Meshes; freie Punkte unter dem Rohrlauf
  und im U-Kanal frei (`tests/test_wave_0112.py`). Geometrie unverändert belegt: Mit eingespielter alter
  `_mark`-Logik stimmen alle 270 alten Golden-Digests (27 Fälle × 10) der Prototypen exakt; geändert haben sich nur die
  80 Generation-3-Fälle (Kollision). Generation 1/2: weiterhin genau eine Box.
- **Grenzen:** Die Prototypen bleiben experimentell und sind nicht Unity-geprüft; die kanonischen Typen
  (`pipe_rack`, `relay_box`, `coolant_loop`, `warning_beacon`) ersetzen sie für den Einsatz.

### Keine Generatorfehler in der Modellausrichtung

Cube Escapes Vorschaubilder und 3D-Vorschau zeigten Rückseiten. Abgleich: Cubegen-Vorderseite −Y (Blender)
wird beim FBX-Export (Forward −Z, Up Y) zu Unity **+Z**; Cubegens eigene Icon-Kamera blickt korrekt auf die
Front. Geprüft an allen 49 vorhandenen Cubegen-Modellen in Cube Escape (Kontaktbogen, 3D-Vorschau): Kameralinsen,
Geschützläufe, Ventilräder, Bildschirme, Türblätter und Treppenläufe zeigen auf +Z. Ursache und Korrektur lagen
vollständig in Cube Escape (Vorschaukamera stand auf −Z); siehe dort `Docs/MODEL_BROWSER.md`.

## Neue Typen (Registry, Parameter, Add-on)

Alle Maße in Metern, Front −Y (Unity +Z). „Teile“ sind die exportierten Objekte, Materialrollen wie im Vertrag.

| Typ | Zweck / Silhouette | Maße (Standardwurf) | Pivot | Anschlüsse | Teile / Materialrollen | Kollision |
|---|---|---|---|---|---|---|
| `airlock_chamber` | begehbare Schleuse; Röhre mit zwei überstehenden Doppeltür-Rahmen | Innen 1,8–2,4 × 2,6–3,6 × 2,4–3,0; Durchgang 0,7·Breite × Höhe−0,3 | floor (Boden 0,1 hoch) | – (Türzustand `state`) | `Body`, `Panel_Outer(_B)`, `Panel_Inner(_B)`, `StatusLight_Outer/Inner`, `Glow`; Wall, RobotDark, Metal, Platform, Warning, Glass, Glow | genaue Meshes; offene Türen geben den Durchgang frei, geschlossene Flügel mit 6-mm-Dichtfuge sperren |
| `pipe_rack` | Rohrbrücke; Rahmen alle 2 m, 1–3 Ebenen, 1–3 Hohlrohre je Ebene | Länge 2/4/6, Höhe 1,8–2,8, Tiefe ≥ 0,7 | floor | `pipe` an beiden Enden jedes Laufs (Radius 0,09/0,18 wie `pipe`) | `Frame`, `Pipes`, `Glow`; RobotDark/Metal, Glow | genaue Meshes; Raum unter dem untersten Lauf frei (≥ 1 m Durchgang) |
| `ceiling_beam` | Deckenträger: I-Profil, Fachwerk oder Kasten, optional Trasse/Lampen | Länge 2/4/6, Trägerhöhe 0,3–0,55, Oberkante 3,0 | wall (am Boden, Geometrie auf Höhe), `view: below` | `beam_end` an beiden Enden | `Girder`, `Glow`; RobotDark/Metal/Wall, HazardOrange, Glow | genaue Meshes (Fachwerkfelder bleiben offen) |
| `pressure_tank` | Druckbehälter liegend auf Sätteln oder stehend auf Zarge, Klöpperböden | Radius 0,45–0,9, Mantel 1,6–3,0 | floor | `pipe` (Radius 0,09) am Auslass | `Body`, `Glow` (Statusfenster); Wall/Metal/Platform, Warning, HazardOrange | genaue Meshes; Raum zwischen den Sätteln frei |
| `turbine` | Turbine auf Skid: Ansaugglocke mit Rotor, gerippter Mantel, Abgas oben/hinten | Radius 0,45–0,8, Länge 1,8–2,8 | floor | – | `Body`, `Rotor`, `Glow`; Wall/Metal/HazardOrange, Platform | statisch: genaue Meshes; mit `machine` Rotor konvex und bewegt |
| `compressor` | Kolbenkompressor: Rippenmotor, Riemenschutz, 1–3 Zylinderköpfe, Behälter | Motorradius 0,18–0,3 | floor | `pipe` (0,09) am Behälter | `Body`, `Glow`; HazardOrange/Wall/RobotBody, Metal, Warning | genaue Meshes |
| `relay_box` | Relaiskasten an der Wand (Kasten oder hoch), Kabelrohre nach oben | 0,7–1,0 breit, Mitte 1,2–1,5 | wall (Rückseite y = +0,1, berührt den Boden nie) | – | `Body`, `Glow` (Status), `Lights` (Zusatz-LEDs) | genaue Meshes |
| `diagnostics_port` | Wand-Serviceanschluss: Rundbuchse (`Slot`), Datenport, Klappe, Kabel | 0,34–0,48 × 0,3–0,42, Mitte 0,6–1,1 | wall | `Slot`-Empty für ein Werkzeug | `Body`, `Glow`, `Lights`, `Screen`; Ground, Metal, Platform | genaue Meshes |
| `coolant_loop` | Kühlkreislauf: Steig-/Rücklauf, gerundete Bögen, Wärmetauscher, Pumpe, Ventil | 1,6–2,6 × 1,4–2,2 | floor | `pipe` an beiden Anschlussstutzen | `Pipe`, `Glow` (cold = Cyan, hot = Orange) | genaue Meshes; Schleifeninneres frei |
| `warning_beacon` | Signalsäule auf Mast oder schwerem Fuß, 1–4 Leuchtstufen, Horn | Höhe 1,4–2,2 (Fuß ≤ 0,6) | floor | – | `Body`, `Glow` (oberste Stufe, ein Material), `Lights` | genaue Meshes |
| `emergency_case` | Notfallkasten: Rahmen, Glastür, Feuerlöscher/Axt/Erste Hilfe, Hammer, Schild | 0,45–0,6 × 0,75–1,0 × 0,22–0,3 | wall | – | `Body`, `Glass`, `Content`; HazardOrange/Warning, Glass | genaue Meshes; Innenraum hinter dem Glas hohl |

Klang-/Effektanker (Generation 3): Schleuse `Audio_Door`/`Audio_Hiss`, Rohrbrücke und Kühlkreislauf
`Audio_Flow`, Druckbehälter `Audio_Hiss`, Turbine `Audio_Hum`/`Audio_Fan`, Kompressor `Audio_Pump`,
Relaiskasten `Audio_Hum`, Diagnoseport `Audio_Beep`, Signalsäule `Audio_Alarm`.

Varianten:

- `door.variant=iris`, `door.iris_open` (0–1): Eckplatten um eine runde Öffnung, Zierring, sechs geschichtete
  Lamellen (`Iris`, je eigene Ebene, kein Z-Fighting). 0 = geschlossen (Lamellenspitzen treffen sich in der
  Mitte), 1 = Durchgang mit 0,9 · Radius frei. Rahmen und Wandanschluss (`door`-Konnektor) wie jede Tür.
- `hatch.variant=maintenance`: eckige Luke mit verschraubtem Deckel, zwei Klappgriffen, Warnkante,
  Schraubenkranz und Schließlasche; `Panel` + Rotatable unverändert, Schacht bleibt frei. Ausdrücklich gesetzte
  `shape=round` bleibt rund.
- `keypad.variant=access`: Kartenleser-Modul mit `Slot` neben dem Tastenfeld, Schutzhaube, Statusleiste;
  SignalIndicator wie `keypad`.

## Erste Umsetzungswelle – vorhandene Registry-Bausteine

Alle 61 Typen der Tabelle in IDEEN.md sind registriert (`python3 -m cubegen list`) und wurden den Einsatzgruppen
und den Cube-Escape-Browserkategorien zugeordnet (Zuordnungstabelle `AssetBrowserCategories` in Cube Escape;
jeder Cubegen-Typ der Registry ist dort erfasst). Kein Typ wurde neu angelegt.

Unity-Übernahme als Modell (statisch, ohne Gameplay-Vertrag) über `Blender/Recipes/cubegen_wave1.json`
(Cube Escape, Seed 112, Präfix `Gen_Wave1_`): die elf neuen Typen, die Irisblende und die 20 statischen
Bestandstypen `wall`, `bulkhead`, `platform`, `pillar`, `floor_grate`, `railing`, `vent_shaft`, `tank`,
`server_rack`, `console`, `pallet`, `toolbox`, `workbench`, `locker`, `medkit`, `canister`, `gas_rack`, `shelf`,
`sign`, `tool_cart`. Die übrigen Bestandstypen besitzen Behaviours und brauchen einen eigenen Gameplay-Vertrag
(sie werden nicht still als Dekoration übernommen); Cube Escape hat für die meisten bereits Stationsbausteine.

### Status je Kandidat

| Kandidat | Ergebnis | implementiert | export-geprüft | Unity-geprüft (Modell) | Gameplay-Freigabe |
|---|---|---|---|---|---|
| `airlock_chamber` | neuer Typ | ja | ja | ja (Begehbarkeit) | offen |
| `pipe_rack` | neuer Typ | ja | ja | ja (Freiraum, Läufe fest) | – (Deko) |
| `ceiling_beam` | neuer Typ | ja | ja | ja | – (Deko) |
| `pressure_tank` | neuer Typ | ja | ja | ja | – (Deko) |
| `turbine` | neuer Typ | ja | ja | ja (statisch) | offen (`machine`) |
| `compressor` | neuer Typ | ja | ja | ja (statisch) | offen (`machine`) |
| `relay_box` | neuer Typ | ja | ja | ja (Wandmontage) | offen |
| `diagnostics_port` | neuer Typ | ja | ja | ja (Wandmontage) | offen |
| `coolant_loop` | neuer Typ | ja | ja | ja | – (Deko) |
| `warning_beacon` | neuer Typ | ja | ja | ja (statisch) | offen (`signal`) |
| `emergency_case` | neuer Typ | ja | ja | ja (Wandmontage) | offen |
| `iris_door` | Variante `door.variant=iris` | ja | ja | ja (Mitte frei, Ecken fest) | offen (kein lineares Door) |
| `maintenance_hatch` | Variante `hatch.variant=maintenance` | ja | ja (Blender-FBX, `check --export`) | nein | offen (Hinge-Vertrag) |
| `access_panel` | Variante `keypad.variant=access` | ja | ja (Blender-FBX, `check --export`) | nein | offen (Keypad-Vertrag) |

## Prüfung

- **Python-Suite** (`python3 tools/run_tests.py`): 240 Tests grün (models 41, quality 12, rest 187 inkl. echtem
  Blender-/Add-on-Smoke), 139 s. Neu `tests/test_wave_0112.py` (13 Tests): Registrierung, Kategorie/Pivot,
  Determinismus, statisch mit genauen Meshes in intakt/beschädigt/Abnutzung/niedrigem Detail/Größe L, keine
  ungedeckte Geometrie, kein Z-Fighting, Gameplay-Optionen, Freiräume am echten Importvertrag
  (`families.collision_boxes`), Anschlüsse, Wandflächen, Varianten bitgleich bei `standard`, Prototypkollision.
- **Golden-Daten** gezielt aktualisiert: 186 Typen; geändert nur die 80 Generation-3-Fälle der Prototypen
  (Kollision, Geometrie separat belegt) und die neuen Typen. Qualitätswerte bestehender Typen unverändert;
  README-Parametertabelle neu erzeugt.
- Bewusst angepasste Tests: Typzahl 175 → 186 (`test_extensions`), Deckenansicht schließt `ceiling_beam` ein
  (`test_core`). Keine Tests entfernt oder gelockert.
- **Echter Export:** Rezept `cubegen_wave1.json`, 32 FBX + Sidecars (`generator: cubegen 0.11.2`);
  `cubegen check --export` für alle Library-Ordner: 0 Ablehnungen. Die mitgeschriebenen Stationstexturen waren
  pixelgleich (nur PNG-Kodierung) und wurden unverändert gelassen.
- **Varianten-Export:** je zwei echte FBX (Seed 112) von `door.variant=iris` (geschlossen), `hatch.variant=maintenance`
  und `keypad.variant=access`; `check --export` 0 Ablehnungen, Vorschaubilder geprüft.
- **Unity (Cube-Escape-Testkopie):** siehe Abschnitt Abnahme in Cube Escapes `Docs/CUBEGEN_IMPORT.md`.

## Verbleibende Grenzen

- Gameplay-Freigaben (Schleusenzyklus, Irismechanik, Turbinen-/Kompressor-Maschine, Signalsäule als Lampe,
  Wartungsluke, Zugangspanel) sind nicht Teil dieses Stands.
- `airlock_chamber` exportiert statische Türstellungen; ein Schleusenablauf braucht ein Door-Paar mit Logik.
- Die Prototypen `test_*` bleiben experimentell.

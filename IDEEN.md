# Cube Escape – Ideen, Assets und Puzzle-Plan

> Zweck dieses Dokuments: Ideen sammeln, passende Inhalte priorisieren und späteren
> Modellierungs-, Unity- und Level-Agenten eindeutige Arbeitsregeln geben.
>
> **Gestaltungskern:** Industrial-/Cyberpunk-Puzzle-Plattformer in einer Indoor-Station.
> **Registry-Stand geprüft am 7. Oktober 2026:** 175 Typen einschließlich experimenteller Demos. Die Registry, nicht diese
> Ideensammlung, ist maßgeblich: `python3 -m cubegen list`.
>
> Die langen Kategorien weiter unten sind ein Brainstorming-Backlog, keine verbindliche
> Roadmap. Sie enthalten absichtlich auch thematische Randideen. Neue Einträge sind nicht
> automatisch registriert, exportierbar oder in Unity spielbar.

## Dokument-Navigation

1. [Prioritäten und Umfang](#prioritäten-und-umfang)
2. [Arbeitsregeln und Statusmodell](#arbeitsregeln-und-statusmodell)
3. [Ergänzende Asset-Ideen](#ergänzende-ideen-für-cube-escape-kuratiert)
4. [Puzzle-Bausteine und Patterns](#puzzle-bausteine-für-spätere-ki-agenten)
5. [Weitere Asset-Ideen](#weitere-assetideen-nachtrag)
6. [Kategorisierter Brainstorming-Katalog](#brainstorming-katalog)
7. Varianten- und Ablegerideen
8. [System-Backlog](#systeme-rund-um-die-modelle)
9. [Level-Szenarien](#level-szenarien-und-puzzle-abläufe)
10. [Zurückgestellte Themen](#zurückgestellte-themen)

## Prioritäten und Umfang

Cube Escape priorisiert wiederverwendbare Indoor-Assets für Architektur, Industrie,
Stationsbetrieb, Sicherheit, Labor und Rätsel. Der Nutzen im Level ist wichtiger als die
bloße Menge neuer Typnamen.

### Erste Umsetzungswelle – vorhandene Registry-Bausteine

Diese Liste ist eine Auswahl bereits registrierter Bausteine, keine neue Implementierungsliste:

| Einsatz | Vorhandene Typen |
|---|---|
| Architektur | `door`, `wall`, `bulkhead`, `cargo_container`, `catwalk`, `platform`, `pillar`, `floor_grate`, `railing`, `stairs`, `shutter`, `ceiling_panel`, `vent_shaft` |
| Maschinen | `machine`, `generator`, `reactor_core`, `transformer`, `tank`, `conveyor`, `pump`, `vent`, `pipe`, `fan` |
| Technik | `server_rack`, `terminal`, `monitor_wall`, `console`, `camera`, `antenna`, `light`, `emergency_light`, `floodlight`, `hologram`, `intercom`, `portal_frame` |
| Interaktion | `laser_emitter`, `laser_receiver`, `laser_mirror`, `laser_splitter`, `pressure_plate`, `button`, `fuse_box`, `keypad`, `combination_lock`, `safe`, `switch_panel`, `sequence_panel`, `water_level` |
| Stations-Props | `crate`, `pallet`, `toolbox`, `workbench`, `locker`, `medkit`, `canister`, `gas_rack`, `shelf`, `sign`, `keycard`, `spare_part`, `tool_cart` |

### Kandidaten für neue Assets

Zuerst gegen Registry und Katalog prüfen; dies ist keine Implementierungsfreigabe.
Eigenständige Kandidaten: `airlock_chamber`, `pipe_rack`, `ceiling_beam`,
`pressure_tank`, `turbine`, `compressor`, `relay_box`, `diagnostics_port`,
`coolant_loop`, `warning_beacon` und `emergency_case`.

Vor einer eigenen Typregistrierung erst als Variante oder Puzzle-Komponente prüfen:
`iris_door` und `maintenance_hatch` sind Varianten von `door` beziehungsweise `hatch`;
`access_panel` ist eine interaktive Komponente und könnte in ein vorhandenes Panel/Terminal
integriert werden.

### Zurückstellen statt löschen

Thematische Randideen bleiben als Archiv statt als Roadmap-Einträge erhalten. Die
Entscheidungskriterien stehen am Dokumentende unter „Zurückgestellte Themen“.

## Arbeitsregeln und Statusmodell

### Inhaltstypen strikt unterscheiden

- **Asset-Typ:** eigenständiges, wiederverwendbares Modell mit Registry-Namen.
- **Variante:** Form, Zustand, Material oder Anbauteil eines Assets; bevorzugt als
  Parameter, Stil oder Bestandteil eines Kits statt als weiterer Typ.
- **Puzzle-Komponente:** Objekt mit einer klaren Interaktion, etwa ein Sensor oder Schloss.
- **Puzzle-Pattern:** Lösungsregel / Zustandslogik; nicht automatisch ein Modell.
- **Level-Szenario/System:** mehrere Assets und Regeln als Ablauf oder Generatorfunktion.

Ein Name soll nur dann als neuer Top-Level-Typ vorgeschlagen werden, wenn er eine
eigenständige Silhouette oder Funktion hat und nicht besser als Parameter, Variante,
Komponente oder Kit-Baustein beschrieben wird.

### Status nicht mit Aufwand verwechseln

- `brainstorm` – ungeprüfte Idee.
- `kuratiert` – thematisch geprüft, noch nicht zur Umsetzung freigegeben.
- `freigegeben` – für eine konkrete Umsetzungsphase ausgewählt.
- `implementiert` – in cubegen registriert; mit `python3 -m cubegen list` verifizieren.
- `unity-geprüft` – echter Export wurde mit dem Unity-Importer und dem vorgesehenen
  Verhalten geprüft.
- `zurückgestellt` – nicht verworfen; braucht einen konkreten Anlass zur Neubewertung.

Die in älteren Katalogeinträgen verwendeten Marker sind grobe Aufwandsschätzungen:

- 🟢 **statischer Asset-Kandidat** – keine besondere Interaktion vorausgesetzt.
- 🔵 **bestehendes Verhalten denkbar** – Unity-Verhalten könnte passen, muss aber anhand
  des aktuellen Importers und Scripts verifiziert werden.
- 🟠 **neue Logik wahrscheinlich** – eigenes Unity-Verhalten oder Adapter nötig.

Keiner dieser Marker garantiert Exportierbarkeit oder Spielbarkeit. Modellstatus,
Exportstatus und Unity-Spielbarkeit sind getrennte Prüfpunkte.

### Benennung, Varianten und Duplikate

- Registry-Namen in lowercase `snake_case`; vor dem Anlegen exakt gegen
  `python3 -m cubegen list` prüfen.
- Pro Konzept einen kanonischen Namen verwenden. Synonyme als Notiz/Alias festhalten,
  nicht als parallele Typen (zum Beispiel `beam_splitter` gegenüber vorhandenem
  `laser_splitter`, oder `wall_monitor` gegenüber `monitor_wall`).
- Türen, Lichter, Schränke und ähnliche Familien als Master-Asset mit Varianten führen.
  Zustände wie `open`, `broken`, `powered` und `empty` möglichst nicht als eigene Typen
  vervielfachen.
- Komponenten, die auch eigenständig gebraucht werden, dürfen separat modelliert werden;
  ihr Zusammenhang mit dem Eltern-Asset muss dokumentiert sein.
- Die Zahl in `Vorhanden (n)` zählt registrierte Typen, keine Varianten oder Vorschläge.
  Es gibt bewusst keine Gesamtzahl der Ideen: Katalog, Varianten und Patterns überlappen
  und ändern sich weiter.

### Umsetzungs- und Prüf-Gate

Vor einer Implementierung:
1. Registry, Katalog und Unity-Vertrag auf vorhandene Namen und passende Verhaltensweisen prüfen.
2. Zweck, Silhouette, Maßstab, Pivot, Anschlussstellen und Interaktionsrollen festlegen.
3. Entscheiden, ob Asset, Variante, Puzzle-Komponente, Pattern oder Level-System.
4. Abhängigkeiten und Unity-Script-/Adapterbedarf benennen.

Nach der Implementierung:
1. Typ muss in `python3 -m cubegen list` auftauchen.
2. Generierung, deterministische Seeds, Geometrie-/Colliderqualität und Exportvertrag testen.
3. Falls Gameplay versprochen wird: echten Unity-Import und die konkrete Interaktion testen.
4. Status erst nach dem jeweiligen Nachweis aktualisieren; Fehler samt Regressionstest im Changelog festhalten.

## Ergänzende Ideen für Cube Escape (kuratiert)

> Zusätzliche Asset-Vorschläge, noch nicht in der Registry. Vor Umsetzung gegen die
> kategorisierten Vorschläge und die Registry deduplizieren. Varianten bestehender
> Assets sind hier ausdrücklich keine neuen Top-Level-Typen.

**Architektur & Station**
- airlock_door 🔵 – `door`-Variante mit Druck-/Sicherheitslogik, kein unabhängiger Typ
- maintenance_hatch 🟢 – Wartungszugang als Variante von `hatch`
- service_corridor 🟢 – enger Versorgungsgang
- control_walkway 🟢 – Wartungs-/Steuersteg
- utility_trench 🟢 – Technikrinne / Kabelkanal
- cable_bridge 🟢 – Brücke für Leitungen
- inspection_port 🟢 – Sicht-/Prüföffnung
- observation_window 🟢 – Sicherheitsfenster
- blast_door 🔵 – Druck-/Sicherheits-/Notausgangstür
- pressure_door 🔵 – druckfeste Tür / Sensorabfrage
- service_ladder 🟢 – Wartungsleiter als Variante von `ladder`
- maintenance_tube 🟢 – Wartungsschacht/Technikrohr

**Technik / Maschinen**
- power_cell 🟢 – Energiezelle / Akku-Modul
- relay_box 🟢 – Relais-/Verteilerkasten
- breaker_switch 🔵 – Leistungsschalter
- power_cabinet 🟢 – Energie-/Verteilerschrank
- coolant_pump 🔵 – Kühlmittelpumpe
- waste_tank 🟢 – Abfall-/Schlammbehälter
- ion_charger 🔵 – Ionen-/Ladeeinheit
- battery_charger 🔵 – Akku-Ladegerät
- fuel_cell_stack 🟢 – Brennstoffzellenstapel
- data_cache 🟢 – Datenspeicher-/Archivmodul
- servo_motor 🔵 – Servo-/Aktuator-Motor
- actuator_arm 🔵 – Gelenkarm/linearer Aktuator
- hydraulic_ram 🔵 – Hydraulikzylinder
- inertial_damper 🟢 – Dämpfer/Impulsabsorber

**Puzzle / Interaktion**
- access_panel 🔵 – Zugangssteuerung / Sicherheits-Panel
- code_terminal 🔵 – Programmier-/Code-Terminal
- lockbox 🟢 – verschließbare Box
- cipher_console 🔵 – Chiffre-/Code-Konsole
- override_switch 🔵 – Übersteuerung / Notstromschalter
- maintenance_key 🟢 – Wartungsschlüssel / Spezialwerkzeug
- power_routing 🔵 – Strompfade neu verdrahten
- signal_router 🔵 – Signale umleiten
- lens_array 🔵 – Linsen-/Prisma-Array
- magnetic_lock 🔵 – Magnet-/Sperre mit Metallanker
- rotator_lock 🔵 – rotierende Sperre / drehende Zählscheibe
- pulse_panel 🔵 – Impuls- / Energieschalter
- thermal_switch 🔵 – Temperatur-/Heiz-/Kühl-Schalter
- scanner_pad 🟢 – Scan-/Erkennungsmatte
- energy_bridge 🔵 – Energielink / Brücke aus Licht oder Plasma

**Hazards / Atmosphäre**
- warning_lamp 🟢 – Warnleuchte / Alarmlampe
- arc_trap 🔵 – Strom-/Lichtbogensperre
- pulse_field 🔵 – Pulsfeld / Energiestrahlung
- toxic_vapor 🟢 – giftiger Dampf / Nebelbereich
- steam_puff 🟢 – Dampfstoß / Druckabgabe
- sparks 🟢 – Funken-/Zündquelle
- broken_light_grid 🟢 – beschädigtes Lichtgitter
- radiation_barrier 🟢 – Strahlungs-/Schutzbarriere

### Experimentelle visuelle Prototypen

Die Registry enthält zusätzlich `geometry_test` sowie zehn ausdrücklich als Test gekennzeichnete Typen: `test_utility_trench`, `test_pipe_rack`, `test_relay_box`, `test_coolant_loop`, `test_warning_beacon`, `test_lens_array`, `test_magnetic_lock`, `test_scanner_pad`, `test_power_routing` und `test_thermal_switch`. Sie illustrieren ausgewählte Ideen mit den neuen Geometrie-Primitiven, sind aber weder kanonische Asset-Typen noch Unity-geprüft; Interaktionslogik ist nicht enthalten.

---

## Puzzle-Bausteine für spätere KI-Agenten

> Ein Puzzle selbst ist ein System aus Ziel, Interaktion, Zuständen, Hinweisen und
> Rückmeldung. Ein Modell kann dabei nur ein Baustein sein. Diese Unterscheidung hält
> Asset-Namen und Gameplay-Logik für spätere Agenten getrennt.

### 1) access_panel
- Zweck: Zugang freischalten, Notfallfreigabe oder Sicherheitslogik aktivieren.
- Typische Interaktion: Spieler nutzt `keycard`, `keypad`, `scanner` oder `code_terminal`.
- Zustand: `locked`, `unlocked`, `overridden`, `damaged`.
- Darstellung: Wandmontage, Bedienfeld, Status-LEDs, physische Schalter.
- KI-Notiz: Ein `access_panel` ist ideal als Trigger für Türen, Sicherheitsgates, Lift- oder Generator-Startsequenzen.

### 2) power_routing
- Zweck: Energiepfade umleiten, um einen Bereich oder eine Maschine zu aktivieren.
- Typische Interaktion: Kabel/Leitungen, Relais, Schalter, Power-Cabinet, `beam_combiner`-ähnliche Verknüpfungen.
- Zustand: `off`, `partial`, `online`, `shorted`.
- Darstellung: rote/gelbe Leitungen, verknüpfte Module, aktive Indikatoren.
- KI-Notiz: Dieses Puzzle eignet sich für stationäre Maschinen- oder Wartungsketten, bei denen Energie an mehreren Punkten verteilt werden muss.

### 3) signal_router
- Zweck: Signale entlang einer Reihenfolge korrekt weiterleiten.
- Typische Interaktion: Reihenfolge aus Antennen, Consoles, Monitoren oder Phasenmodulen.
- Zustand: `stable`, `looping`, `jammed`, `redirected`.
- Darstellung: Netzwerkknoten, Datenleitungen, kleine Signalquellen, Indikatorfarben.
- KI-Notiz: Gut für Logik- und Sequenzpuzzle, nicht nur für visuelles Dekor.

### 4) magnetic_lock
- Zweck: Metallobjekte mit einem Magnetfeld aufnehmen, festhalten oder freigeben.
- Typische Interaktion: Spieler nutzt `magnet`, `key`, `metal_plate`, `pod` oder magnetische Kette.
- Zustand: `engaged`, `released`, `stuck`, `overloaded`.
- Darstellung: magnetische Halterung, Stahlanker, Metall- oder Schienenpfad.
- KI-Notiz: Gut für Kettenreaktionen, Bewegungs- oder Entsperrungsmechaniken.

### 5) beam_splitter / lens_array
- Zweck: Strahlen umleiten, fokussieren oder bündeln.
- Typische Interaktion: `laser_emitter`, `laser_mirror`, `prism_stand`, `beam_combiner`, `lens_array`.
- Zustand: `aligned`, `split`, `blocked`, `reflecting`.
- Darstellung: Lichtpfade, Spiegelelemente, Prisma, Strahl-Einfärbungen.
- KI-Notiz: Ein klassisches Cube-Escape-Spielpuzzle; sinnvoll für Station-Umgebungen, Maschinenräume und Sicherheitssektoren.

### 6) thermal_switch
- Zweck: Wärme-/Kältezustand steuert einen Mechanismus oder einen Zustand.
- Typische Interaktion: `temperature_puzzle`, `coolant_leak`, `steam_puff`, Heizer/Kühler.
- Zustand: `cold`, `warm`, `stable`, `overheated`.
- Darstellung: Temperaturindikatoren, Messgeräte, Leitungen, Schalter mit Heiz-/Kühlsymbolen.
- KI-Notiz: Ideal für Labore, Kühlkreisläufe, Robotik-Wartungsbereiche und Alarmstationen.

### 7) scanner_pad
- Zweck: Spieler oder Objekt wird erkannt, validiert oder entschlüsselt.
- Typische Interaktion: Identifikation, Codeprüfung, Synchronschritt, Objekt-Slot.
- Zustand: `idle`, `scanning`, `confirmed`, `denied`.
- Darstellung: helle Plattformen, Scannerlinien, Statusanzeige.
- KI-Notiz: Für Sicherheitscodes, Schlüsselsysteme und Reihenfolgen in der Station relevant.

### 8) pulse_panel
- Zweck: Ein Impuls oder Hoch-/Niederspannungs-Pattern aktiviert Mechanik.
- Typische Interaktion: Timing, Sequenz, Wiederholung, Rhythmus.
- Zustand: `charged`, `triggered`, `stopped`, `charged_overflow`.
- Darstellung: analoge Uhren, Impulsanzeigen, Blinklichtsysteme.
- KI-Notiz: Das Puzzle kann an eine Rhythmus-Mechanik oder eine elektrische Last gekoppelt werden.

### 9) rotator_lock
- Zweck: Dreh-/Ring-/Schlüsselfolge steuert eine Sperre oder einen Mechanismus.
- Typische Interaktion: rotieren, mit richtigen Winkelwerten ausrichten, auf Zeichenmuster prüfen.
- Zustand: `misaligned`, `partial`, `open`, `jammed`.
- Darstellung: Zahnräder, Ringe, mechanische Korrekturmarken, Positionsanzeigen.
- KI-Notiz: Gute Alternative zu einfachen Code-Panels, da sie ein physisches, mechanisches Gefühl erzeugt.

### 10) energy_bridge
- Zweck: Energiequellen verbinden, um Brücke/Struktur zu aktivieren.
- Typische Interaktion: Energiepfad spannungsfrei machen, Strahler aktivieren, Verbindung herstellen.
- Zustand: `inactive`, `stable`, `overloaded`, `collapsed`.
- Darstellung: Licht-/Energiebogen, signalreiche Brücke, passende Leitungen.
- KI-Notiz: Passt zu Portal-, Laser- und Sicherheitsnetz-Mechaniken, etwa als Verbindung zu einer oberen Ebene oder einem entfernten Raum.

### Empfohlene Standardbeschreibung für jeden Puzzle-Typ

Eine neue Puzzle-Idee wird für Agenten mit diesen Feldern beschrieben:
- `name`: eindeutiger kanonischer snake_case-Name; Synonyme als Alias notieren.
- `kind`: Asset, Variante, Puzzle-Komponente, Puzzle-Pattern oder Level-System.
- `theme`: Station, Labor, Sicherheit, Gefahr oder Versorgung.
- `registry_status`: brainstorm, kuratiert, freigegeben, implementiert oder zurückgestellt.
- `unity_status`: ungeprüft, exportgeprüft oder mit echtem Unity-Verhalten geprüft.
- `goal` und `primary_interaction`: Ziel und zentrale Aktion, etwa drehen, ausrichten,
  umleiten, freischalten, scannen oder erkennen.
- `trigger` und `state_machine`: Auslöser sowie alle Zustände und erlaubten Übergänge.
- `asset_roles`: Basis, Bedienelement, Sensor, Anzeige, Ausgang, Gefahrzone usw.
- `feedback`: sichtbare/hörbare/textliche Rückmeldung bei Erfolg, Fortschritt und Fehler.
- `script_need`: vorhandenes Verhalten, Adapter nötig oder neue Mechanik; vorab prüfen.
- `reset_and_recovery`: Rücksetzweg und Schutz vor unwiederbringlichem Fehler/Softlock.
- `variants_and_dependencies`: Varianten, benötigte Items, Assets, Scripts und Räume.
- `acceptance`: konkrete Tests für Lösung, Fehlerfall, Wiederholung, Export und Unity.

## Weitere Assetideen (Nachtrag)

> Neue Vorschläge, keine registrierten Typen. Semantische Nähe bedeutet nicht automatisch
> einen neuen Typ: zum Beispiel ist `wall_monitor` ein Montage-/Varianzfall von `monitor_wall`,
> `beam_splitter` ein Alias-Kandidat für `laser_splitter`, und `coolant_leak` steht bereits
> in der Puzzle-Kategorie. `patch_panel`, `circuit_board`, `capacitor` und `warning_beacon`
> stehen bereits im kategorisierten Katalog.
> Diese Kandidaten vor Umsetzung zusammenführen statt doppelt anzulegen.

**Architektur & Station**
- maintenance_tunnel 🟢 – enger Wartungstunnel zwischen Stationsbereichen
- emergency_shaft 🟢 – vertikaler Notausgangs- oder Evakuierungsschacht
- pressure_chamber 🔵 – Druckkammer als Variante/Innenraum von `airlock_chamber`, nicht automatisch ein eigener Typ
- service_duct 🟢 – begehbarer oder rein technischer Versorgungskanal
- inspection_walkway 🟢 – schmaler Wartungssteg an Wand oder Maschine
- observation_catwalk 🟢 – Steg mit Sichtfenster in einen Maschinen- oder Reaktorraum
- lift_shaft 🟢 – Aufzugsschacht als modularer Raum-/Umgebungsbaustein
- utility_shell 🟢 – abgeschirmte Verkleidung für empfindliche Stationsmodule
- access_ramp 🟢 – kurze Rampe zu Wartungs- oder Bedienbereichen
- shielded_wall 🟢 – abgeschirmtes Wandsegment für Strahlungs- oder Hochenergiezonen
- emergency_exit 🔵 – Notausgang mit Alarm-/Freigabezustand
- dead_end_corridor 🟢 – kurzer Sackgang für Level-Layout und falsche Fährten

**Technik & Infrastruktur**
- relay_matrix 🟢 – gruppierte Relais als Strom-/Signalverteiler
- signal_node 🟢 – einzelner Knoten in einem Signalnetz
- diagnostics_port 🟢 – Wartungsanschluss für Diagnose oder Datenübertragung
- data_bank 🟢 – robuster Datenspeicher / Archivblock
- shield_module 🟢 – separates Energie-/Strahlungsabschirmungsmodul
- power_bus 🟢 – zentrale Sammelschiene zur Stromverteilung
- coolant_loop 🟢 – geschlossener Kühlkreislauf aus Rohren und Ventilen
- battery_stack 🟢 – modularer Stapel aus Stationsakkus
- feed_line 🟢 – Zufuhrleitung für Gas, Kühlmittel oder Prozessmaterial
- junction_box 🟢 – kompakter Abzweigkasten für Leitungen
- fuse_array 🟢 – sichtbare Gruppe austauschbarer Sicherungen
- surge_protector 🟢 – Überspannungsschutz mit Statusanzeige
- membrane_panel 🟢 – austauschbare Filter-/Dichtmembran in einem Rahmen
- scanner_array 🔵 – mehrere synchronisierte Scannerköpfe
- telemetry_beacon 🔵 – Sender für Status- oder Positionsdaten

**Props & Facility-Details**
- maintenance_kit 🟢 – Werkzeug- und Prüfset für Reparaturen; `repair_kit` als mögliche Variante statt eigenem Typ
- spare_parts_bin 🟢 – beschrifteter Behälter für Ersatzteile
- emergency_case 🟢 – Wandkasten mit Notfallausrüstung
- utility_cart 🟢 – mobiler Versorgungskarren
- welding_station 🔵 – stationärer Schweißplatz mit Stromquelle und Halterung
- service_crate 🟢 – robuste, markierte Versorgungskiste
- hazard_marker 🟢 – aufstellbare Gefahrenmarkierung
- floor_marking 🟢 – Richtungspfeile, Sicherheitslinien und Sektorcodes als Bodenelement
- decon_station 🔵 – Dekontaminationsplatz mit Spül-/Statuskomponenten
- medical_cache 🟢 – versiegelter medizinischer Vorratsbehälter
- supply_rack 🟢 – Regal für Stationsverbrauchsmaterial
- tool_chest 🟢 – abschließbare Werkzeugtruhe
- cable_spool 🟢 – Kabeltrommel für Wartungsarbeiten

**Weitere neue, kleine System-Assets**
- pressure_equalizer 🔵 – gleicht den Druck auf beiden Seiten einer Schleuse an
- phase_relay 🔵 – schaltet ein Signal zwischen Phasen oder Frequenzzuständen um
- thermal_fuse 🟢 – sichtbare Einmalsicherung, die bei Überhitzung auslöst
- fault_isolator 🔵 – trennt einen fehlerhaften Stromkreis vom übrigen Netz
- memory_core 🟢 – austauschbarer Speicherbaustein als Schlüssel-/Hinweisobjekt
- acoustic_sensor 🔵 – erkennt Klatschen, Tonfolge oder Frequenzmuster
- air_quality_sensor 🔵 – misst Sauerstoff, Rauch oder toxische Konzentration
- gravity_anchor 🔵 – lokaler Anker für Schwerkraft- oder Bewegungsrätsel
- safety_interlock 🔵 – verhindert Maschinenstart, bis Bedingungen erfüllt sind
- data_cartridge 🟢 – tragbarer Datenträger für Hinweise oder Freischaltungen
- load_cell 🔵 – Gewichtssensor für Waagen- und Lastverteilungsrätsel
- vent_damper 🔵 – verstellbare Klappe zur Luftstromsteuerung

## Puzzle-Patterns für Agenten

> Das sind lösungsseitige Mechaniken, nicht automatisch eigene 3D-Modelltypen. Für die Umsetzung zuerst vorhandene Objekte und Verhaltensweisen kombinieren; ein neues Unity-Script nur dann vorsehen, wenn die Regel nicht mit bestehenden Komponenten ausdrückbar ist.

| Pattern | Ziel und Spieleraktion | Zustände / Rückmeldung | Typische Bausteine |
|---|---|---|---|
| `deadman_switch` | Schalter gedrückt halten, während ein zweiter Weg oder Mechanismus betätigt wird. | `released`, `held`, `interrupted`; sichtbare Halteanzeige und hörbarer Abbruch. | Hebel, Tür, Licht-/Signalindikator |
| `phase_sequence` | Phasenmodule in der aus Hinweisen erschließbaren Reihenfolge aktivieren. | `idle`, `partial`, `solved`, `reset`; jede korrekte Stufe bestätigt sich einzeln. | Phasenschalter, sequence_panel, Signallicht |
| `multi_key_lock` | Mehrere passende Schlüssel, Karten oder Energiezellen in beliebiger oder angezeigter Reihenfolge einsetzen. | `incomplete`, `ready`, `unlocked`; belegte Slots bleiben sichtbar. | Schloss, Item-Slots, keycard, power_cell |
| `timed_shutdown` | Eine Gefahr oder Maschine nach einem Startsignal innerhalb des Zeitfensters abschalten. | `armed`, `counting`, `stopped`, `expired`; Countdown und eindeutiges Erfolgssignal. | countdown, override_switch, Maschine/Hazard |
| `signal_match` | Quelle und Empfänger durch passende Frequenz, Farbe oder Takt synchronisieren. | `searching`, `near_match`, `locked`, `lost`; Feedback zeigt Annäherung ohne die Lösung zu verraten. | freq_dial, antenna, signal_node |
| `dual_power_source` | Zwei unabhängige Energiequellen korrekt verbinden oder zeitgleich aktivieren. | `none`, `one_active`, `both_active`, `overloaded`; jede Quelle wird separat angezeigt. | Generator, battery_stack, relay_matrix |
| `safe_sequence` | Mehrstufige Eingabe an einem Safe aus Hinweisen rekonstruieren. | `idle`, `partial`, `wrong`, `open`; Fehlversuche setzen gemäß Levelregel zurück. | safe, rotator_lock, clue |
| `override_chain` | Eine Reihe von Sicherheitsfreigaben in Abhängigkeit aktivieren. | `blocked`, `partially_overridden`, `released`, `fault`; blockierende Stufe wird erkennbar. | access_panel, fuse_box, safety_interlock |
| `path_lock` | Einen durchgehenden Pfad aus drehbaren oder verschiebbaren Segmenten bilden. | `disconnected`, `partial`, `connected`; Leitungs-/Lichtpfad zeigt Konnektivität. | Rohr-/Leitungssegmente, Rotator, Signalindikator |
| `pulse_reset` | Impulse im richtigen Takt auslösen, um einen Zustand zurückzusetzen oder zu synchronisieren. | `waiting`, `in_sync`, `reset`, `missed`; Taktgeber liefert wiederholbare Hinweise. | pulse_panel, countdown, signal_light |
| `thermal_balance` | Temperatur in einem Zielbereich halten, indem Wärmequelle und Kühlung geregelt werden. | `cold`, `warming`, `stable`, `overheated`; Skala zeigt Bereich statt nur binäres Feedback. | thermal_switch, coolant_loop, pressure_gauge |
| `weight_lock` | Last auf vorgegebenen Sensoren verteilen, nicht bloß Gesamtgewicht erreichen. | `underloaded`, `imbalanced`, `balanced`, `overloaded`; pro Sensor sichtbares Feedback. | load_cell, weight_plate, crate |
| `door_cycle_puzzle` | Schleusen-Türzyklus in sicherer Reihenfolge ausführen; nie beide Türen gleichzeitig öffnen. | `sealed`, `equalizing`, `inner_open`, `outer_open`, `fault`; Druck-/Türanzeigen synchronisieren. | airlock_door, pressure_equalizer, access_panel |
| `route_inversion` | Eine Leitung oder ein Signal absichtlich umkehren, damit das Ziel den richtigen Zustand erhält. | `normal`, `inverted`, `valid`, `shorted`; Richtung/Polarität klar visualisiert. | phase_relay, switch_panel, signal_router |
| `phase_shift_lock` | Bauteile zwischen Phasen schalten, um einen sonst blockierten Pfad zeitweise auszurichten. | `out_of_phase`, `aligned`, `latched`, `unstable`; sichere und instabile Ausrichtung unterscheiden. | phase_platform, phase_relay, Rotator |

Für jedes Pattern muss das Level zusätzlich festlegen: Hinweisquelle, erlaubte Fehlversuche, Reset-Verhalten, Abbruchmöglichkeit, Lösungskriterium und barrierearme Rückmeldung. Ein Puzzle sollte ohne pixelgenaue Platzierung lösbar sein und nach einem Fehler den Zustand eindeutig anzeigen.

---

## Brainstorming-Katalog

> Die folgenden acht Kategorien sind der langfristige Ideenpool. Unter `Vorhanden` stehen
> registrierte Typen; `Vorgeschlagen` ist unbereinigtes Brainstorming, nicht automatisch
> Cube-Escape-relevant. Priorisierte Vorschläge stehen im Index weiter oben.

### environment

### Vorhanden (34)
archway, baseboard, breakable_platform, bulkhead, cable_tray, cage, cargo_container, catwalk, ceiling_module, ceiling_panel, door, escape_pod, floor_grate, floor_tile, hatch, ladder, lift, pad, phase_platform, pillar, planet_window, platform, railing, ramp, retractable_bridge, shutter, spiral_stairs, stairs, vent_shaft, wall, wall_cap, wall_corner, wall_panel, window_wall

### Vorgeschlagen

**Türen & Öffnungen**
- iris_door 🔵 – runde Mehrsegment-Blende, drehend öffnend (Sci-Fi-Signatur)
- saloon_door 🔵 – Schwingtür (Wilder Westen)
- cell_door 🔵 – Zellentür
- security_gate 🔵 – Sicherheitstor

**Fenster & Glas**
- window 🟢 – eigenständiger Fensterrahmen (transparent)
- glass_partition 🟢 – transparente Innenwand
- porthole 🟢 – Bullauge

**Bau-Kit & Architektur**
- corridor_module 🟢 – vorgefertigter Gang
- airlock_chamber 🔵 – komplette Schleuse als Modul
- dome 🟢 – Kuppel
- scaffolding 🟢 – Baugerüst
- greenhouse 🟢 – Gewächshaus (Struktur)
- pergola 🟢 – Pergola
- torii_gate 🟢 – Torii-Tor

**Geländer & Träger**
- railing_corner 🟢 – Eck-/Bogen-Geländer
- ceiling_beam 🟢 – Decken-/Stützträger
- pipe_rack 🟢 – Überkopf-Rohrtrasse
- jeffries_tube 🟢 – vertikaler Wartungsschacht

**Boden & Decke**
- floor_drain 🟢 – Bodengully/Abflussrinne
- crown_molding 🟢 – Deckenleiste
- cornice 🟢 – Gesims
- wainscoting 🟢 – Wandvertäfelung
- ceiling_medallion 🟢 – Deckenrosette

**Infrastruktur & Außen**
- revolving_door 🔵 – Drehtür
- folding_door 🔵 – Falttür (Akkordeon)
- garage_door 🔵 – Kipp-/Rolltor
- skylight 🟢 – Oberlicht
- balcony 🟢 – Balkon
- mezzanine 🟢 – Zwischenebene
- escalator 🔵 – Rolltreppe
- moving_walkway 🔵 – Fahrsteig
- utility_pole 🟢 – Strommast
- pylon 🟢 – Hochspannungsmast
- manhole_cover 🟢 – Kanaldeckel
- storm_drain 🟢 – Straßenablauf
- awning 🟢 – Markise
- storefront 🟢 – Schaufensterfront
- gazebo 🟢 – Pavillon
- colonnade 🟢 – Säulengang
- buttress 🟢 – Strebepfeiler
- coffered_ceiling 🟢 – Kassettendecke
- truss 🟢 – Fachwerkträger

**Architektur-Detail (weitere)**
- atrium 🟢 – Lichthof
- light_well 🟢 – Lichtschacht
- portico 🟢 – Säulenvorbau
- veranda 🟢 – Veranda
- balustrade 🟢 – Balustrade
- cupola 🟢 – Kuppelaufsatz
- dormer 🟢 – Dachgaube
- dumbwaiter 🔵 – Speiseaufzug
- laundry_chute 🟢 – Wäscheschacht
- mail_chute 🟢 – Postschacht
- louver 🟢 – Lüftungslamellen
- clerestory 🟢 – Obergaden
- glass_block_wall 🟢 – Glasbausteinwand

**Stadt & Verkehr (weitere)**
- paternoster 🔵 – Umlaufaufzug
- funicular 🔵 – Standseilbahn
- rotunda 🟢 – Rundbau
- courtyard 🟢 – Innenhof
- cellar 🟢 – Keller
- attic 🟢 – Dachboden
- loading_dock 🟢 – Laderampe
- dock_leveler 🟢 – Überladebrücke
- bell_tower 🟢 – Glockenturm
- platform_screen_door 🟢 – Bahnsteigtür

**Brücken & Verkehrsbauten**
- bridge 🟢 – feste Brücke
- drawbridge 🔵 – Zugbrücke
- gangway 🟢 – Laufsteg/Gangway
- pier 🟢 – Pier/Kai
- boardwalk 🟢 – Holzsteg
- dam 🟢 – Staudamm
- overpass 🟢 – Überführung
- skybridge 🟢 – Skywalk

**Wasserbau & Verkehr (weitere)**
- aqueduct 🟢 – Aquädukt
- viaduct 🟢 – Viadukt
- tunnel 🟢 – Tunnel
- culvert 🟢 – Durchlass
- canal 🟢 – Kanal
- lock 🟢 – Schleuse
- gatehouse 🟢 – Torhaus
- tollbooth 🟢 – Mautstelle
- helipad 🟢 – Hubschrauberlandeplatz

**Bauten & Stätten (weitere)**
- monument 🟢 – Denkmal
- memorial 🟢 – Gedenkstätte
- amphitheater 🟢 – Amphitheater
- hangar 🟢 – Flugzeughalle
- warehouse 🟢 – Lagerhalle
- depot 🟢 – Depot

**Garten- & Gutsbauten**
- aviary 🟢 – Voliere
- orangery 🟢 – Orangerie
- portcullis 🔵 – Fallgatter
- arboretum 🟢 – Arboretum

**Tür- & Fensterzubehör**
- door_handle 🟢 – Türklinke
- doorbell 🔵 – Türklingel
- door_mat 🟢 – Fußmatte
- door_knocker 🟢 – Türklopfer
- window_shutter 🟢 – Fensterladen
- blinds 🟢 – Jalousie
- window_sill 🟢 – Fensterbank

**Stadtmobiliar**
- park_bench 🟢 – Parkbank
- planter_box 🟢 – Pflanzkasten

---

### industrial

### Vorhanden (12)
conveyor, fan, fluid_basin, generator, machine, pipe, pipe_bend, pump, reactor_core, tank, transformer, vent

### Vorgeschlagen

**Feuer & Metall (foundry)**
- furnace 🔵 – Hochofen mit Glut
- foundry_ladle 🔵 – Gießpfanne (flüssiges Metall)
- crucible 🔵 – Schmelztiegel
- rolling_mill 🔵 – Walzwerk
- extrusion_press 🔵 – Strangpresse
- ingot_mold 🟢 – Barrenform
- steel_coil 🟢 – Stahlcoil
- anvil 🟢 – Amboss

**Maschinen & Antrieb**
- turbine 🔵 – Turbine mit Laufrad
- compressor 🔵 – Kompressor
- pneumatic_piston 🔵 – Hydraulik-/Pneumatikzylinder
- flywheel 🔵 – Schwungradspeicher
- motor 🔵 – Elektromotor
- gearbox 🔵 – Getriebe

**Wärme & Chemie**
- cooling_tower 🟢 – Kühlturm
- heat_exchanger 🟢 – Wärmetauscher
- distillation_column 🟢 – Destillationskolonne
- exhaust_stack 🟢 – Abgas-/Schornsteinrohr
- boiler 🟢 – Heizkessel

**Lager & Behälter**
- silo 🟢 – Silo/Trichter
- hopper 🟢 – Trichter
- pressure_tank 🟢 – kugelförmiger Druckbehälter
- valve_manifold 🟢 – Ventilbatterie/Verteiler

**Energie & Strahlung**
- breaker_panel 🟢 – Schaltanlage
- capacitor_bank 🟢 – Kondensatorbank
- wind_turbine 🔵 – Windrad
- inverter 🟢 – USV/Wechselrichter
- fuel_rod 🔵 – Brennstab
- geiger_counter 🔵 – Geigerzähler
- dosimeter 🟢 – Dosimeter
- radiation_sign 🟢 – Strahlen-Warnschild
- lead_container 🟢 – Blei-/Transportbehälter
- tesla_coil 🔵 – Tesla-Spule
- plasma_ball 🔵 – Plasmakugel

**Messgeräte**
- pressure_gauge 🟢 – Manometer
- water_meter 🟢 – Wasserzähler
- gas_meter 🟢 – Gaszähler
- flow_meter 🟢 – Durchflussmesser

**Fördertechnik & Kräne**
- overhead_crane 🔵 – Brücken-/Portalkran
- jib_crane 🔵 – Schwenkkran
- hoist 🔵 – Seilwinde; `winch` als Suchalias, nicht als zweiter Typname
- assembly_line 🔵 – Fließband
- screw_conveyor 🔵 – Schneckenförderer
- bucket_elevator 🔵 – Becherwerk
- chute 🟢 – Rutsche; Trichterform als Variante, nicht als alternativer Typname
- pallet_rack 🟢 – Palettenregal
- parts_bin 🟢 – Kleinteilebehälter

**Prozess & Werkzeugmaschinen**
- reactor_vessel 🟢 – Reaktionsbehälter
- mixing_tank 🔵 – Rührkessel
- filter_press 🟢 – Filterpresse
- vacuum_pump 🔵 – Vakuumpumpe
- gear_pump 🔵 – Zahnradpumpe
- control_panel 🔵 – PLC-Schaltschrank
- lathe_machine 🔵 – Drehbank
- milling_machine 🔵 – Fräsmaschine
- drill_press 🔵 – Ständerbohrmaschine
- press_brake 🔵 – Abkantpresse

**Hütten- & Verfahrenstechnik**
- rotary_kiln 🔵 – Drehrohrofen
- coke_oven 🔵 – Koksofen
- quenching_tank 🟢 – Abschreckbecken
- galvanizing_bath 🟢 – Verzinkungsbad
- electroplating_tank 🟢 – Galvanikbad
- baling_press 🔵 – Ballenpresse
- shredder_machine 🔵 – Schredder (Industrie)
- magnetic_separator 🟢 – Magnetscheider
- cyclone_separator 🟢 – Zyklonabscheider
- dust_collector 🟢 – Staubabsaugung
- scrubber 🟢 – Gaswäscher
- evaporator 🟢 – Verdampfer
- crystallizer 🟢 – Kristallisator
- pallet_wrapper 🔵 – Stretchwickler

**Oberflächen- & Prüftechnik**
- hydraulic_press 🔵 – Hydraulikpresse
- forging_hammer 🔵 – Fallhammer
- shot_blaster 🟢 – Kugelstrahlanlage
- tumbling_barrel 🔵 – Gleitschleiftrommel
- parts_washer 🔵 – Teilereinigungsanlage
- painting_booth 🟢 – Lackierkabine
- powder_coating 🟢 – Pulverbeschichtung
- test_bench 🟢 – Prüfstand

**Hafen- & Logistik-Großgerät**
- stacker_reclaimer 🔵 – Absetzer/Rücklader
- reach_stacker 🟢 – Reach-Stacker
- straddle_carrier 🟢 – Portalhubwagen
- ship_to_shore_crane 🔵 – Containerbrücke
- vibratory_feeder 🔵 – Schwingförderer
- pneumatic_conveyor 🔵 – pneumatische Förderung
- container_spreader 🟢 – Containergeschirr

**Zubehör & Signale**
- stack_light 🔵 – Signalsäule (Andon)
- pipe_clamp 🟢 – Rohrschelle
- flange_cover 🟢 – Flanschdeckel
- machine_light 🔵 – Maschinenleuchte

**Gießerei (weitere)**
- forge_bellows 🔵 – Blasebalg
- sand_mold 🟢 – Sandform (Guss)
- pattern_plate 🟢 – Modellplatte

**Öfen (weitere)**
- cupola_furnace 🔵 – Kupolofen
- electric_arc_furnace 🔵 – Lichtbogenofen
- induction_furnace 🔵 – Induktionsofen
- continuous_caster 🔵 – Stranggussanlage

**Antriebselemente**
- belt_drive 🟢 – Riemenantrieb
- chain_drive 🟢 – Kettenantrieb
- shaft_coupling 🟢 – Wellenkupplung

**Kerntechnik (weitere)**
- fuel_pool 🟢 – Abklingbecken
- containment_vessel 🟢 – Sicherheitsbehälter
- control_rod 🔵 – Steuerstab

**Anzeigen (weitere)**
- gauge_cluster 🟢 – Anzeigenbatterie
- dial_panel 🟢 – Rundinstrument-Panel

---

### nature

### Vorhanden (13)
asteroid, cocoon, floating_island, fungus_carpet, hanging_crystals, hydroponic_bed, mushroom, plant, puddle, rock, stalagmite, vines, wall_roots

### Vorgeschlagen

**Pflanzen**
- alien_tree 🟢 – großer organischer Baum
- bush 🟢 – Busch/Hecke
- tree_stump 🟢 – Baumstumpf
- fallen_log 🟢 – umgestürzter Stamm
- leaf_pile 🟢 – Laubhaufen
- bamboo 🟢 – Bambus
- bonsai 🟢 – Bonsai
- cactus 🟢 – Kaktus
- palm 🟢 – Palme
- lotus 🟢 – Lotus
- orchid 🟢 – Orchidee
- sunflower 🟢 – Sonnenblume
- lichen_patch 🟢 – Flechten/Moos

**Pilze & Alien-Wuchs**
- alien_egg 🟢 – Alien-Ei/Gelege
- spore_pod 🟢 – Sporenkapseln
- bioluminescent_shroom 🔵 – leuchtender Pilz
- web 🟢 – Alien-/Spinnennetz
- honeycomb 🟢 – Wabe

**Geologie & Erde**
- geode 🟢 – Geode
- fossil 🟢 – Fossil
- lava_pool 🔵 – Lavabecken
- magma 🟢 – Glut
- crater 🟢 – Krater
- snow_patch 🟢 – Schnee-/Eisfläche

**Wasser & Wetter**
- fountain 🔵 – Springbrunnen
- well 🟢 – Brunnen
- waterfall 🟠 – Wasserfall (FX)
- geyser 🟠 – Geysir (FX)

**Tiere (Land)**
- rat 🟢, cat 🟢, dog 🟢, horse 🟢, snake 🟢, frog 🟢, turtle 🟢, rabbit 🟢, monkey 🟢, elephant 🟢, giraffe 🟢, llama 🟢

**Vögel**
- bird 🟢, owl 🟢, bat 🟢, crow 🟢, penguin 🟢, peacock 🟢, flamingo 🟢, swan 🟢, eagle 🟢, toucan 🟢, pelican 🟢, hummingbird 🟢, parrot 🟢, carrier_pigeon 🟢

**Meeresbewohner**
- fish 🟢, starfish 🟢, seahorse 🟢, crab 🟢, lobster 🟢, coral 🟢, clam 🟢, octopus 🟢, jellyfish 🔵

**Insekten**
- spider 🟢, beetle 🟢, firefly 🔵, dragonfly 🟢, ladybug 🟢, mantis 🟢, snail 🟢

**Fabelwesen**
- dragon 🟢, unicorn 🟢, phoenix 🔵, gargoyle 🟢, mermaid 🟢, minotaur 🟢, pegasus 🟢

**Pflanzen (weitere)**
- fern 🟢 – Farn
- ivy 🟢 – Efeu
- rose 🟢 – Rose
- tulip 🟢 – Tulpe
- poppy 🟢 – Mohn
- lavender 🟢 – Lavendel
- pine 🟢 – Kiefer
- willow 🟢 – Weide
- cherry_blossom 🟢 – Kirschblüte
- berry_bush 🟢 – Beerenstrauch
- thorn_bush 🟢 – Dornenbusch

**Landschaft & Mineralien**
- stream 🟢 – Bach
- marsh 🟢 – Sumpf/Moor
- hot_spring 🔵 – Thermalquelle
- icicle 🟢 – Eiszapfen
- frost 🟢 – Raureif
- dune 🟢 – Düne
- canyon 🟢 – Schlucht
- cave 🟢 – Höhle
- obsidian 🟢 – Obsidian
- quartz 🟢 – Quarz
- meteorite 🟢 – Meteorit

**Pflanzen & Gewässer (weitere)**
- topiary 🟢 – Formschnitt-Pflanze
- grapevine 🟢 – Weinrebe
- corn_stalk 🟢 – Maisstängel
- wheat 🟢 – Weizen
- reed 🟢 – Schilf
- cattail 🟢 – Rohrkolben
- water_lily 🟢 – Seerose
- kelp 🟢 – Tang
- seaweed 🟢 – Seegras
- barnacle 🟢 – Seepocke
- seashell 🟢 – Muschel
- driftwood 🟢 – Treibholz

**Polargebiete & Himmel**
- glacier 🟢 – Gletscher
- iceberg 🟢 – Eisberg
- snowdrift 🟢 – Schneewehe
- aurora 🟠 – Polarlicht (Himmel-FX)

**Pilze & Baumzustände (weitere)**
- slime_mold 🟢 – Schleimpilz
- puffball 🟢 – Bovist
- bracket_fungus 🟢 – Baumpilz/Konsolenpilz
- pinecone 🟢 – Kiefernzapfen
- acorn 🟢 – Eichel
- seed_pod 🟢 – Samenkapsel
- dead_tree 🟢 – toter Baum
- hollow_tree 🟢 – hohler Baum
- mushroom_ring 🟢 – Hexenring

**Gewässer & Vulkan (weitere)**
- algae 🟢 – Algen
- duckweed 🟢 – Wasserlinse
- stalactite 🟢 – Stalaktit (Deckenzapfen, Pendant zu `stalagmite`)
- fumarole 🟢 – Fumarole
- lava_tube 🟢 – Lavaröhre
- flowstone 🟢 – Sinterfahne
- sea_anemone 🟢 – Seeanemone
- sea_urchin 🟢 – Seeigel

**Pflanzen-Detail (weitere)**
- sapling 🟢 – Setzling
- seedling 🟢 – Keimling
- nest 🟢 – Vogelnest
- feather 🟢 – Feder
- blossom 🟢 – Blüte
- twig 🟢 – Zweig

**Landschaftsformen (weitere)**
- cliff_face 🟢 – Felswand
- mesa 🟢 – Tafelberg
- sinkhole 🟢 – Erdfall
- grotto 🟢 – Grotte
- oasis 🟢 – Oase
- spring 🟢 – Quelle

**Wiesen & Auen**
- grove 🟢 – Hain
- meadow 🟢 – Wiese
- savanna 🟢 – Savanne
- mangrove 🟢 – Mangrove
- fen 🟢 – Niedermoor

**Boden & Spuren**
- gravel 🟢 – Kies
- sand_patch 🟢 – Sandfläche
- animal_tracks 🟢 – Tierspuren

**Küste & Eis (weitere)**
- tide_pool 🟢 – Gezeitentümpel
- sand_dollar 🟢 – Sanddollar
- ice_floe 🟢 – Eisscholle

---

### props

### Vorhanden (33)
barrier, bed, bin, cable_reel, canister, chair, clue, coffee_machine, crate, cryo_pod, debris, extinguisher, flashlight, floor_plan, galley, gas_rack, item, key, keycard, lab_device, locker, medkit, pallet, shelf, sign, spare_part, table, tool, tool_cart, toolbox, vending_machine, washroom, workbench

### Vorgeschlagen

**Möbel & Wohnen**
- armchair 🟢, sofa 🟢, coffee_table 🟢, nightstand 🟢, wardrobe 🟢, dresser 🟢, ottoman 🟢, bookshelf_unit 🟢
- desk 🟢, cabinet 🔵, drawer_unit 🟢, filing_cabinet 🟢, whiteboard 🟢, cork_board 🟢
- bunk_bed 🟢, bench 🟢, rug 🟢, curtain 🟢, coat_rack 🟢, laundry_basket 🟢

**Küche & Essen**
- refrigerator 🟢, stove 🔵, microwave 🔵, dishwasher 🔵, range_hood 🔵, blender 🔵, stand_mixer 🔵, kettle 🟢, toaster 🟢
- pots_pans 🟢, knife_block 🟢, spice_rack 🟢, cutting_board 🟢, rolling_pin 🟢, cookie_jar 🟢, dish_rack 🟢
- bread_loaf 🟢, cheese_wheel 🟢, cake 🟢, pizza 🟢, soup_bowl 🟢, ration 🟢, fruit_crate 🟢, ice_cream 🟢
- sushi 🟢, dumplings 🟢, curry 🟢, waffle 🟢, pancake 🟢

**Getränke**
- soda_can 🟢, juice_box 🟢, water_bottle 🟢, thermos 🟢, wine_bottle 🟢, teapot 🟢, milk 🟢, milkshake 🟢, hot_chocolate 🟢, lemonade 🟢, coffee_mug 🟢

**Werkstatt & Werkzeug**
- vice 🟢, bench_grinder 🔵, power_drill 🟢, welding_torch 🔵, work_light 🔵, saw_horse 🟢
- crowbar 🟢, axe 🟢, pickaxe 🟢, chainsaw 🔵, hammer 🟢, wrench 🟢, shovel 🟢, rake 🟢

**Behälter & Lagerung**
- oil_barrel 🟢, jerry_can 🟢, cardboard_box 🟢, vault 🔵, treasure_chest 🔵, chest 🟢, trunk 🟢
- bucket 🟢, cooler 🟢, picnic_basket 🟢

**Transport & Fahrzeuge**
- forklift 🟢, hand_truck 🟢, pallet_jack 🟢, mine_cart 🟢, roller_track 🟢, shopping_cart 🟢, wheelbarrow 🟢
- motorcycle 🟢, scooter 🟢, skateboard 🟢, bicycle 🟢, wagon 🟢, golf_cart 🟢
- locomotive 🟢, ambulance 🔵, fire_truck 🔵, bulldozer 🟢, excavator 🔵, tractor 🟢, plow 🟢
- hovercraft 🔵, helicopter 🔵, glider 🟢, parachute 🟢, hot_air_balloon 🟢, submarine 🟢, sailboat 🟢, canoe 🟢
- rocket 🟢, satellite 🟢, anchor 🟢, buoy 🟢, cable_car 🟢, monorail 🟢, unicycle 🟢, snowmobile 🟢, jetski 🟢, dirigible 🔵

**Waffen & Militär**
- rifle 🟢, pistol 🟢, shotgun 🟢, machine_gun 🟢, bazooka 🟢, cannon 🟢, flamethrower 🔵, energy_weapon 🔵
- sword 🟢, shield 🟢, spear 🟢, bow_arrow 🟢, quiver 🟢, armor 🟢, crossbow 🟢, cutlass 🟢, knife 🟢
- grenade 🟢, dynamite 🟢, ammo_crate 🟢, shield_generator 🔵, sandbag 🟢, barbed_wire 🟢

**Kleidung & Persönliches**
- hazmat_suit 🟢, lab_coat 🟢, apron 🟢, uniform_on_hanger 🟢, jacket 🟢, gloves 🟢, boots 🟢
- hard_hat 🟢, space_helmet 🟢, top_hat 🟢, goggles 🟢, gas_mask 🟢
- diary 🟢, wallet 🟢, key_ring 🟢, locket 🟢, amulet 🟢, matchbox 🟢, tobacco_pipe 🟢, lighter 🟢, pocket_watch 🔵

**Musik & Unterhaltung**
- guitar 🟢, violin 🟢, cello 🟢, double_bass 🟢, drum_kit 🟢, flute 🟢, microphone 🔵, gramophone 🔵, piano 🟢
- accordion 🟢, harmonica 🟢, trumpet 🟢, saxophone 🟢, trombone 🟢, clarinet 🟢, harp 🟢, banjo 🟢, xylophone 🟢
- didgeridoo 🟢, sitar 🟢, bagpipes 🟢, pan_flute 🟢, kalimba 🟢, steel_drum 🟢, marimba 🟢, bongos 🟢, triangle 🟢, cowbell 🟢, bell 🔵, gong 🔵, wind_chime 🟢
- arcade_cabinet 🔵, jukebox 🔵, slot_machine 🔵, pinball_machine 🔵, claw_machine 🔵, roulette_wheel 🔵
- dart_board 🟢, chess_board 🟢, poker_chips 🟢, dominoes 🟢, mahjong 🟢, books 🟢

**Büro & Papier**
- typewriter 🟢, printer 🔵, shredder 🔵, label_maker 🟢, calculator 🟢, adding_machine 🟢, abacus 🟢, slide_rule 🟢
- paper_stack 🟢, notepad 🟢, sticky_note 🟢, fountain_pen 🟢, quill 🟢, scissors 🟢, paper_clip 🟢, paper_airplane 🟢
- letter 🟢, envelope 🟢, parcel 🟢, mailbox 🟢, passport 🟢, ticket 🟢, wax_seal 🟢
- newspaper 🟢, magazine 🟢, comic_book 🟢, scroll 🟢, manuscript 🟢, blueprint 🟢, poster 🟢, postcard 🟢

**Medizin & Pflege**
- gurney 🟢, operating_table 🟢, iv_drip 🟢, defibrillator 🟢, surgical_light 🔵, medicine_cabinet 🟢
- diagnostic_scanner 🟢, ventilator 🔵, biohazard_bin 🟢, wheelchair 🟢, walker 🟢, crutches 🟢, walking_cane 🟢
- stethoscope 🟢, syringe 🟢, pill_bottle 🟢, scalpel_set 🟢, bandage 🟢, blood_bag 🟢, first_aid_station 🟢
- mri_machine 🟢, ct_scanner 🟢, xray_machine 🔵, ultrasound 🔵, dental_chair 🔵, incubator 🔵, autopsy_table 🟢

**Labor & Wissenschaft**
- fume_hood 🟢, centrifuge 🔵, microscope_station 🟢, test_tube_rack 🟢, cryo_tank 🟢, magnetic_stirrer 🔵, petri_culture 🟢
- bunsen_burner 🔵, spectrometer 🟢, autoclave 🟢, pipette 🟢, graduated_cylinder 🟢, condenser 🟢

**Sport & Spielzeug**
- exercise_bike 🔵, treadmill 🔵, dumbbells 🟢, punching_bag 🟢
- golf_club 🟢, baseball_bat 🟢, tennis_racket 🟢, ping_pong_table 🟢, billiards_table 🟢, bowling_ball 🟢, archery_target 🟢, boxing_gloves 🟢
- teddy_bear 🟢, doll 🟢, toy_robot 🟢, toy_blocks 🟢, rocking_horse 🟢, tin_soldier 🟢, marionette 🔵, puppet 🟢
- ball 🟢, kite 🟢, frisbee 🟢, yo_yo 🟢, jigsaw_puzzle 🟢, rubik_cube 🟢, jack_in_the_box 🔵, spinning_top 🔵, marble 🟢

**Sicherheit & Notfall**
- warning_beacon 🔵, fire_alarm 🟢, exit_sign 🔵, life_ring 🟢, hazard_barricade 🟢, metal_detector 🔵, turnstile 🔵
- prison_bars 🟢, handcuffs 🟢, chain_link_fence 🟢, watchtower 🟢, bunker 🟢
- flare 🔵, whistle 🟢, emergency_blanket 🟢, survival_kit 🟢, emergency_beacon 🔵, signal_mirror 🟢

**Reinigung & Hygiene**
- mop_bucket 🟢, broom 🟢, vacuum_cleaner 🟢, cleaning_cart 🟢, dust_pan 🟢, spray_bottle 🟢
- bathtub 🟢, toilet 🟢, shower 🟢, faucet 🟢, towel_rack 🟢, soap_dispenser 🟢, hair_dryer 🟢

**Deko & Kunst**
- painting 🟢, sculpture 🟢, vase 🟢, aquarium 🔵, terrarium 🔵, picture_frame 🟢, globe 🟢
- candle 🔵, chandelier 🔵, neon_sign 🔵, lantern 🔵, desk_lamp 🔵, floor_lamp 🔵, wall_sconce 🔵

**Haushalt & Elektronik**
- washing_machine 🔵, dryer 🟢, iron 🟢, radiator 🟢, thermostat 🟢, smoke_detector 🟢
- humidifier 🔵, air_purifier 🔵, ceiling_fan 🔵, electric_toothbrush 🔵, curling_iron 🔵
- laptop 🔵, tablet 🔵, smartphone 🟢, headphones 🟢, game_controller 🟢, drone_controller 🟢, music_player 🟢
- telephone 🟢, television 🟢, radio 🟢, webcam 🔵, hard_drive 🟢, usb_drive 🟢, calendar 🟢, rolodex 🟢

**Zeit & Uhren**
- wall_clock 🔵, grandfather_clock 🔵, cuckoo_clock 🔵, astronomical_clock 🔵, digital_clock 🔵, clock_tower 🟢
- sundial 🟢, water_clock 🟢, candle_clock 🔵, metronome 🔵, stopwatch 🟢, alarm_clock 🟢

**Optik & Navigation**
- magnifying_glass 🟢, binoculars 🟢, periscope 🔵, monocular 🟢, telescope 🔵
- star_map 🟢, astrolabe 🟢, sextant 🟢, celestial_globe 🟢, compass 🟢

**Garten & Landwirtschaft**
- flower_pot 🟢, watering_can 🟢, garden_hose 🟢, lawn_mower 🟢, sprinkler 🔵, birdhouse 🟢, bird_bath 🟢, trellis 🟢, compost_bin 🟢
- hay_bale 🟢, scarecrow 🟢, beehive 🟢, honey_jar 🟢, fence 🟢

**Baustoffe**
- brick_pile 🟢, cinder_block 🟢, rebar 🟢, timber_stack 🟢, plywood 🟢, concrete_bag 🟢, metal_sheet 🟢

**Historisch & Fantasie**
- pyramid 🟢, sphinx 🟢, sarcophagus 🟢, mummy 🟢, canopic_jar 🟢, ankh 🟢, scarab 🟢, pharaoh_mask 🟢, hieroglyph 🟢
- amphora 🟢, laurel_wreath 🟢, lyre 🟢, gladiator_helmet 🟢, chariot 🟢
- longship 🟢, drinking_horn 🟢, horned_helmet 🟢, rune_stone 🟢
- horseshoe 🟢, wagon_wheel 🟢, wanted_poster 🟢, tumbleweed 🟢, cow_skull 🟢, lasso 🟢
- eye_patch 🟢, hook_hand 🟢, peg_leg 🟢, rum_barrel 🟢
- monolith 🟢, altar 🟢, obelisk 🟢, totem 🟢, crystal_ball 🔵, tarot_cards 🟢, ouija_board 🟢, pentagram 🔵, cauldron 🔵, wand 🟢, grimoire 🟢, runes 🟢

**Sonstiges / Assistenten**
- crib 🟢, high_chair 🟢, stroller 🟢, baby_bottle 🟢, pacifier 🟢, playpen 🟢
- grab_bar 🟢, stairlift 🔵
- gold_bar 🟢, coins 🟢, gem 🟢, jewelry 🟢, cash 🟢
- christmas_tree 🔵, wreath 🟢, gift_box 🟢, balloons 🟢, pumpkin 🔵, string_lights 🔵, snowman 🟢, gingerbread_house 🟢, stocking 🟢, easter_egg 🟢, fireworks 🟠, pinata 🟢, mask 🟢

**Schreibwaren (weitere)**
- pencil 🟢, eraser 🟢, ruler 🟢, stapler 🟢, hole_punch 🟢

**Rauchen & Genuss**
- ashtray 🟢, cigar 🟢, hookah 🟢

**Haustiere**
- pet_bowl 🟢, pet_bed 🟢, birdcage 🟢, fishbowl 🟢

**Fotografie**
- camera_tripod 🟢, film_roll 🟢

**Geld & Schmuck**
- piggy_bank 🟢, checkbook 🟢
- ring 🟢, bracelet 🟢, earrings 🟢, brooch 🟢

**Nähen & Wäsche**
- pin_cushion 🟢, thread_spool 🟢, button 🟢
- clothesline 🟢, clothespin 🟢, drying_rack 🟢

**Reinigung (weitere)**
- sponge 🟢, scrub_brush 🟢, squeegee 🟢

**Baby (weitere)**
- changing_table 🟢, baby_monitor 🔵, rattle 🟢, mobile 🟢

**Sammlungen & Hobby**
- stamp_collection 🟢, coin_collection 🟢, model_kit 🟢

**Bad & Textil (weitere)**
- towel 🟢, bathrobe 🟢, slippers 🟢
- toothbrush_holder 🟢, soap_dish 🟢

**Büro & Kennzeichnung (weitere)**
- clipboard 🟢, name_tag 🟢

**Garten & Winter (weitere)**
- seed_packet 🟢, garden_trowel 🟢, pruning_shears 🟢, hedge_trimmer 🔵
- snow_shovel 🟢, ice_skates 🟢, snowboard 🟢

**Persönliches (weitere)**
- hip_flask 🟢

**Wäsche & Nähzubehör (weitere)**
- laundry_detergent 🟢, lint_roller 🟢, sewing_basket 🟢, embroidery_hoop 🟢, knitting_needles 🟢

**Haustierzubehör (weitere)**
- pet_carrier 🟢, cat_tree 🟢, scratching_post 🟢, litter_box 🟢

**Körperpflege & Kosmetik**
- razor 🟢, shaving_cream 🟢, aftershave 🟢
- hairbrush 🟢, comb 🟢
- perfume 🟢, cologne 🟢
- makeup 🟢, lipstick 🟢, nail_polish 🟢
- deodorant 🟢, mouthwash 🟢
- nail_clipper 🟢, tweezers 🟢

**Taschen & Verpflegung (weitere)**
- lunchbox 🟢, bento_box 🟢
- grocery_bag 🟢, paper_bag 🟢, tote_bag 🟢
- purse 🟢, messenger_bag 🟢

**Wohn-Accessoires (weitere)**
- shoe_rack 🟢, umbrella_stand 🟢, hat_rack 🟢

**Küchen-Zutaten**
- salt_pepper 🟢, oil_bottle 🟢, vinegar_bottle 🟢

**Werkzeug-Lagerung**
- nail_box 🟢, tool_belt 🟢

**Waffen-Aufbewahrung**
- gun_rack 🟢, weapon_case 🟢

**Büro-Zubehör (weitere)**
- paperweight 🟢, desk_tray 🟢, letter_opener 🟢

**Medizin-Zubehör**
- medicine_bottle 🟢, thermometer_medical 🟢

**Labor-Zubehör**
- funnel 🟢, mortar_pestle 🟢, stir_rod 🟢

**Sport-Zubehör**
- jump_rope 🟢, hula_hoop 🟢

**Sicherheits-Ausrüstung**
- eye_wash_station 🟢, emergency_phone 🔵

**Haushalt (weitere)**
- air_freshener 🟢, rice_cooker 🔵, slow_cooker 🔵

**Zeitmesser (weitere)**
- egg_timer 🟢, timer 🔵

**Optik-Zubehör**
- rangefinder 🟢

**Stations-Ausstattung**
- oxygen_station 🟢 – Sauerstoff-/Atemstation
- decon_shower 🔵 – Dekontaminationsdusche
- fire_hose_cabinet 🟢 – Feuerlöschschrank
- emergency_oxygen 🟢 – Notfall-Sauerstoffmaske
- survival_cache 🟢 – Überlebens-Cache
- airlock_panel 🔵 – Schleusen-Bedienpanel
- radiation_medkit 🟢 – Strahlen-Medkit

---

### puzzle

### Vorhanden (37)
balance_scale, battery_bank, button, cable_plug, chip_reader, combination_lock, countdown, crane, crusher, force_field, freq_dial, fuse_box, gear_puzzle, keypad, laser_emitter, laser_filter, laser_mirror, laser_receiver, laser_splitter, lever, pipe_fitting, pressure_plate, push_block, safe, saw_blade, scanner, sequence_panel, shock_plate, sliding_puzzle, socket, spike_trap, steam_vent, switch_panel, symbol_plate, turntable, valve, water_level

### Vorgeschlagen
- wire_panel 🟠 – Draht-Schneide-Panel („Defusal")
- magnet 🟠 – Elektromagnet (zieht Metall-Items)
- light_sensor 🟠 – Lichtsensor
- motion_sensor 🟠 – Bewegungssensor
- color_mixer 🟠 – Farbmisch-Rätsel
- hourglass 🟢 – Sanduhr als Timer
- pendulum 🔵 – Pendel
- pulley 🔵 – Flaschenzug
- keyhole 🟢 – Schlüsselloch (Interaktion mit `ItemPickup`)

**Weitere Rätsel-Mechaniken (🟠 = neue Scripts)**
- circuit_puzzle 🟠 – Stromkreis verdrahten
- prism_puzzle 🟠 – Licht in Farben zerlegen
- key_matching 🟠 – Schlüssel Schlössern zuordnen
- temperature_puzzle 🟠 – Hitze/Kälte steuern
- sonar_puzzle 🟠 – Echolot-Rätsel
- weight_distribution 🟠 – Gewichtsverteilung
- lever_sequence 🟠 – Hebelreihenfolge
- fluid_flow_puzzle 🟠 – Fluss umleiten
- constellation_puzzle 🟠 – Sterne verbinden

**Noch mehr Rätsel-Mechaniken (🟠)**
- shape_sorter 🟠 – Formen zuordnen
- magnet_maze 🟠 – Magnetlabyrinth
- ball_drop_puzzle 🟠 – Kugelbahn-Rätsel
- rube_goldberg 🟠 – Kettenreaktion
- logic_gate_puzzle 🟠 – Logikgatter (AND/OR/XOR)
- binary_puzzle 🟠 – Binärschalter
- morse_code_puzzle 🟠 – Morsecode
- cipher_puzzle 🟠 – Chiffre knacken
- shadow_puzzle 🟠 – Schatten = Form
- domino_chain 🟠 – Domino-Kette

**Rätsel-Mechaniken (noch weitere, 🟠)**
- pattern_lock 🟠 – Muster-Sperre
- clock_puzzle 🟠 – Uhrzeit einstellen
- compass_puzzle 🟠 – Richtung ausrichten
- telescope_puzzle 🟠 – auf Stern zielen
- pressure_puzzle 🟠 – Druck steuern

**Rätsel-Mechaniken (noch einmal weitere, 🟠)**
- chemical_mix_puzzle 🟠 – Chemikalien mischen
- electrolysis_puzzle 🟠 – Elektrolyse
- magnet_polarity 🟠 – Magnet-Polarität
- rhythm_puzzle 🟠 – Rhythmus nachspielen
- melody_puzzle 🟠 – Melodie nachspielen
- resonance_puzzle 🟠 – Resonanz

**Rätsel-Mechaniken (final, 🟠)**
- light_focus 🟠 – Licht bündeln
- lens_puzzle 🟠 – Linsen anordnen
- balance_beam 🟠 – Balkenwaage
- pulley_weight 🟠 – Umlenkrolle + Gewicht

**Portale & Laser (Gameplay)**
- portal_pedestal 🔵 – Portal auf Sockel
- portal_emitter 🔵 – Portalsender
- laser_booster 🔵 – Laser-Verstärker (Relais)
- laser_tripwire 🟠 – Laser-Schranke (Alarm)
- prism_stand 🔵 – Prisma auf Stativ
- beam_combiner 🔵 – Strahlvereiniger (2 → 1)

**Plattformer-Elemente**
- bounce_pad 🔵 – Sprungplatte
- launch_pad 🔵 – Schleuderplatte
- speed_pad 🔵 – Beschleunigungsplatte
- gravity_well 🔵 – Gravitationsfeld (zieht an)
- anti_gravity_zone 🟠 – Schwerelosigkeitszone
- moving_wall 🔵 – verschiebbare Wand

**Gefahren (Hazards)**
- plasma_gate 🔵 – Plasmator
- energy_wall 🔵 – Energiewand
- flame_jet 🔵 – Flammenstrahl
- piston_smasher 🔵 – Kolbenpresse (Hazard)
- tesla_arc 🔵 – Tesla-Lichtbogen
- magnetic_field 🔵 – Magnetfeld
- coolant_leak 🟢 – Kühlmittelleck
- acid_drip 🟢 – Säuretropfen

---

### robots

### Vorhanden (10)
android, drone, mech, patrol_drone, robot_arm, robot_dog, service_robot, spider_bot, turret, vent_crawler

### Vorgeschlagen
- loader_bot 🔵 – Gabelstapler-Roboter
- cleaner_bot 🔵 – Putzroboter
- welder_bot 🔵 – Schweißroboter (Funken)
- hover_bot 🔵 – schwebender Bot
- probe 🔵 – kleine Sensor-Sonde
- space_rover 🔵 – Mond-/Mars-Rover

**Weitere Roboter**
- assembler_bot 🔵 – Montageroboter
- courier_bot 🔵 – Lieferroboter
- gardening_bot 🔵 – Gartenroboter
- mining_bot 🔵 – Bergbauroboter
- underwater_bot 🔵 – Unterwasserroboter
- rescue_bot 🔵 – Rettungsroboter
- bomb_disposal_bot 🔵 – Entschärfungsroboter
- chef_bot 🔵 – Kochroboter
- guard_bot 🔵 – Wachroboter
- inspection_bot 🔵 – Inspektionsroboter

**Service-Roboter (weitere)**
- surgical_bot 🔵 – OP-Roboter
- pharmacist_bot 🔵 – Apotheker-Roboter
- librarian_bot 🔵 – Bibliotheks-Roboter
- bartender_bot 🔵 – Barkeeper-Roboter
- nanny_bot 🔵 – Kinderbetreuungs-Roboter
- tutor_bot 🔵 – Lehr-Roboter
- scout_bot 🔵 – Aufklärungsroboter
- hover_sentry 🔵 – schwebender Wächter
- drone_swarm 🟢 – Drohnenschwarm
- android_servant 🔵 – Diener-Android

**Industrie-Robotik (weitere)**
- palletizing_robot 🔵 – Palettierroboter
- pick_and_place 🔵 – Greif-/Platzierroboter
- scara_robot 🔵 – SCARA-Roboterarm
- delta_robot 🔵 – Delta-Roboter
- telepresence_robot 🔵 – Telepräsenz-Roboter
- firefighting_bot 🔵 – Feuerwehr-Roboter

**Roboter (noch weitere)**
- pet_bot 🔵 – Roboter-Haustier
- companion_bot 🔵 – Begleitroboter
- micro_bot 🟢 – Mikroroboter
- delivery_drone 🔵 – Lieferdrohne
- construction_bot 🔵 – Bauroboter

**Androiden (weitere)**
- receptionist_android 🔵 – Empfangs-Android
- maintenance_android 🔵 – Wartungs-Android
- worker_android 🔵 – Arbeiter-Android
- combat_android 🔵 – Kampf-Android

---

### ruins

### Vorhanden (10)
broken_wall, burnt_console, cable_mess, collapsed_catwalk, crashed_pod, crate_pile, fallen_pillar, girders, rubble_pile, scrap_heap

### Vorgeschlagen
- broken_door 🟢 – aus den Angeln gehängte Tür
- overgrown_door 🟢 – überwucherte Tür
- shattered_glass 🟢 – Glasscherben
- overgrown_console 🟢 – überwucherte Konsole
- rusty_machine 🟢 – verrostete Maschine
- skeleton 🟢 – Skelett
- skull 🟢 – Schädel/Knochen
- ribcage 🟢 – Brustkorb
- coffin 🟢 – Sarg
- urn 🟢 – Urne
- gravestone 🟢 – Grabstein
- tombstone 🟢 – Grabplatte
- mausoleum 🟢 – Mausoleum
- body_bag 🟢 – Leichensack

**Weitere Ruinen**
- collapsed_ceiling 🟢 – eingestürzte Decke
- buckled_floor 🟢 – aufgewölbter Boden
- scorched_wall 🟢 – brandgeschwärzte Wand
- melted_wall 🟢 – geschmolzene Wand
- rusted_pipe 🟢 – verrostetes Rohr
- broken_stairs 🟢 – zerbrochene Treppe
- wrecked_vehicle 🟢 – Wrack eines Fahrzeugs
- burnt_furniture 🟢 – verkohlte Möbel
- waterlogged 🟢 – durchnässt/überflutet
- ash_pile 🟢 – Aschehaufen

**Noch mehr Ruinen**
- collapsed_tunnel 🟢 – eingestürzter Tunnel
- caved_in 🟢 – Einsturzstelle
- flooded_corridor 🟢 – gefluteter Gang
- overgrown_room 🟢 – überwucherter Raum
- shattered_machine 🟢 – zertrümmerte Maschine
- bent_railing 🟢 – verbogenes Geländer
- crushed_vehicle 🟢 – zerdrücktes Fahrzeug
- melted_metal 🟢 – geschmolzenes Metall
- rusted_beam 🟢 – verrosteter Träger
- weathered_sign 🟢 – verwittertes Schild

**Noch weitere Ruinen**
- sunken_ship 🟢 – gesunkenes Schiff
- buried_ruins 🟢 – verschüttete Ruine
- toppled_statue 🟢 – umgestürzte Statue
- shattered_statue 🟢 – zerschlagene Statue
- overgrown_vehicle 🟢 – überwuchertes Fahrzeug

**Weitere verfallene Orte**
- abandoned_camp 🟢 – verlassenes Lager
- collapsed_roof 🟢 – eingestürztes Dach
- overgrown_building 🟢 – überwuchertes Gebäude
- derelict_ship 🟢 – verlassenes Schiff

**Noch einmal weitere Ruinen**
- overturned_furniture 🟢 – umgestürzte Möbel
- scattered_debris 🟢 – verstreute Trümmer
- burned_out_vehicle 🟢 – ausgebranntes Fahrzeug
- abandoned_lab 🟢 – verlassenes Labor

---

### tech

### Vorhanden (15)
antenna, camera, console, crystal_cluster, emergency_light, floodlight, hologram, intercom, light, light_strip, monitor_wall, portal_frame, server_rack, solar_panel, terminal

### Vorgeschlagen

**Licht & Leuchten**
- siren 🔵 – Alarmsirene mit Leuchtturm
- lighthouse 🔵 – Leuchtturm
- street_lamp 🔵 – Straßenlaterne
- gas_lamp 🔵 – Gaslaterne
- brazier 🔵 – Kohlenbecken
- oil_lamp 🔵 – Öllampe
- spotlight 🔵 – Suchscheinwerfer
- blacklight 🔵 – UV-Lampe
- glow_stick 🔵 – Leuchtstab
- light_bulb 🔵 – Glühbirne
- vacuum_tube 🔵 – Vakuumröhre
- fiber_optic 🔵 – Glasfaser-Bündel

**Wissenschaft & Modelle**
- orrery 🔵 – Planetenmaschine
- armillary_sphere 🟢 – Armillarsphäre
- dna_model 🟢 – DNA-Doppelhelix
- atom_model 🟢 – Atommodell
- newtons_cradle 🔵 – Kugelstoßpendel
- solar_system_model 🔵 – Sonnensystem-Modell
- mobius_strip 🟢 – Möbiusband
- klein_bottle 🟢 – Kleinsche Flasche
- prism 🟢 – optisches Prisma
- lens 🟢 – Linse
- reflector 🟢 – Reflektor

**Mechanische Rechner**
- difference_engine 🔵 – Differenzmaschine
- enigma_machine 🔵 – Chiffriermaschine
- mechanical_calculator 🔵 – mechanischer Rechner

**Wetter-Instrumente**
- weather_vane 🔵 – Wetterfahne
- anemometer 🔵 – Windmesser
- thermometer 🟢 – Thermometer
- barometer 🟢 – Barometer
- hygrometer 🟢 – Hygrometer
- rain_gauge 🟢 – Regenmesser
- weather_station 🟢 – Wetterstation
- seismograph 🟢 – Seismograf

**Weltraum**
- observatory_dome 🔵 – Observatoriumskuppel
- radio_telescope 🔵 – Radioteleskop
- comet 🔵 – Komet
- space_station_ring 🟢 – Ring-Station
- moon_base 🟢 – Mondbasis
- planet_model 🟢 – Planetenmodell
- sun_model 🔵 – Sonnenmodell
- warp_core 🔵 – Warpkern
- jetpack 🔵 – Raketenrucksack
- tractor_beam 🔵 – Traktorstrahl
- replicator 🔵 – Replikator
- clone_tank 🔵 – Klon-Tank
- exo_frame 🔵 – Exoskelett-Rahmen
- teleporter_pad 🔵 – Teleporter-Plattform
- docking_port 🔵 – Andockstutzen
- stasis_tube 🔵 – Stasiskammer

**Kommunikation & Überwachung**
- dome_camera 🔵 – Überwachungskuppel
- speaker_horn 🟢 – Durchsage-Lautsprecher
- alarm_bell 🔵 – Alarmglocke
- projector 🔵 – Beamer
- network_switch 🟢 – Netzwerkgerät
- oscilloscope 🟢 – Oszilloskop
- mainframe 🔵 – Großrechner
- circuit_board 🟢 – Platine
- tape_drive 🟢 – Bandlaufwerk
- switchboard 🔵 – Telefonzentrale
- phone_booth 🔵 – Telefonzelle
- semaphore 🟢 – Flaggensignal
- heliograph 🟢 – Heliograf
- morse_key 🔵 – Morsetaste
- telegraph 🟢 – Telegraf

**Elektrik & Mechanik**
- relay 🟢 – Relais
- coil_spring 🟢 – Spiralfeder
- chain 🟢 – Kette
- bearing 🟢 – Lager

**Vermessung & Kartografie**
- theodolite 🔵 – Theodolit
- survey_rod 🟢 – Messlatte
- drafting_table 🟢 – Zeichentisch
- t_square 🟢 – Reißschiene

**Cyberpunk**
- vr_headset 🔵 – VR-Brille
- cyberdeck 🔵 – Cyberdeck
- cyber_limb 🔵 – kybernetische Prothese

**Rechenzentrum & Fertigung**
- quantum_computer 🔵 – Quantencomputer
- supercomputer 🔵 – Supercomputer
- patch_panel 🟢 – Patchfeld
- modem 🟢 – Modem
- cooling_rack 🟢 – Kühlrack (Rechenzentrum)
- 3d_printer 🔵 – 3D-Drucker
- laser_cutter 🔵 – Laserschneider

**Biometrie & Wearables**
- iris_scanner 🔵 – Iris-Scanner
- fingerprint_scanner 🔵 – Fingerabdruck-Scanner
- smartwatch 🔵 – Smartwatch

**Kiosk & Bezahl-Terminals**
- teleprompter 🔵 – Teleprompter
- kiosk 🔵 – Infoterminal
- atm 🔵 – Geldautomat
- ticket_machine 🔵 – Fahrkartenautomat
- self_checkout 🔵 – Selbstbedienungskasse
- biometric_gate 🔵 – biometrisches Tor

**Smart Home & Zubehör**
- smart_lock 🔵 – Smart-Lock
- ev_charger 🔵 – E-Ladesäule
- power_strip 🟢 – Steckdosenleiste
- nas_device 🟢 – NAS-Gerät
- projector_screen 🟢 – Leinwand
- digital_sign 🔵 – digitales Schild

**Anzeigen & Infrastruktur (weitere)**
- power_distribution_unit 🟢 – Stromverteiler (PDU)
- cable_management 🟢 – Kabelmanagement
- game_console 🔵 – Spielkonsole
- led_matrix 🔵 – LED-Matrix
- scoreboard 🔵 – Anzeigetafel
- traffic_light 🔵 – Ampel
- radar_dish 🔵 – Radarantenne
- touchscreen_panel 🔵 – Touch-Panel

**Elektronik-Werkbank & Messtechnik**
- multimeter 🟢 – Multimeter
- breadboard 🟢 – Steckplatine
- soldering_station 🔵 – Lötstation
- thermal_camera 🔵 – Wärmebildkamera
- barcode_scanner 🔵 – Barcode-Scanner
- rfid_reader 🔵 – RFID-Leser
- logic_analyzer 🟢 – Logikanalysator
- signal_generator 🟢 – Signalgenerator

**Labormesstechnik (weitere)**
- bench_power_supply 🔵 – Labornetzteil
- frequency_counter 🟢 – Frequenzzähler
- spectrum_analyzer 🔵 – Spektrumanalysator
- faraday_cage 🟢 – Faradayscher Käfig
- thermal_chamber 🟢 – Klimakammer

**Elektronik-Bauteile**
- semiconductor 🟢 – Halbleiter
- wafer 🟢 – Wafer
- chip 🟢 – Chip
- transistor 🟢 – Transistor
- resistor 🟢 – Widerstand
- capacitor 🟢 – Kondensator

**Messtechnik (weitere)**
- clamp_meter 🟢 – Zangenamperemeter
- wattmeter 🟢 – Leistungsmesser
- insulation_tester 🟢 – Isolationsprüfer
- logic_probe 🟢 – Logiktastkopf

**Wissenschafts-Modelle (weitere)**
- molecule_model 🟢 – Molekülmodell
- anatomical_model 🟢 – Anatomiemodell
- periodic_table 🟢 – Periodensystem

**Wetter & Weltraum (weitere)**
- weather_balloon 🟢 – Wetterballon
- space_probe 🟢 – Raumsonde
- orbital_module 🟢 – Orbitalmodul

**Kommunikation & Vermessung (weitere)**
- tower_transmitter 🔵 – Sendemast
- gps_unit 🟢 – GPS-Gerät
- laser_distance 🟢 – Laser-Entfernungsmesser

**Cyberpunk (weitere)**
- neural_interface 🟢 – Neuralinterface

**Cyberpunk-Interieur (weitere)**
- neon_hologram 🔵 – Neon-Hologramm
- data_shard 🟢 – Datensplitter (Item)
- memory_chip 🟢 – Speicherchip
- network_node 🔵 – Netzknoten (blinkt)
- cyber_terminal 🔵 – Cyber-Terminal
- holo_advert 🔵 – Hologramm-Werbung
- drone_dock 🔵 – Drohnen-Andockstation

**Kristalle & Energie**
- power_crystal 🔵 – Energiekristall (glüht)
- crystal_reactor 🔵 – Kristallreaktor
- glow_shard 🟢 – leuchtende Scherbe
- energy_vein 🟢 – Energieader (Wand)

**Level-Editor-Marker**
- spawn_marker 🟢 – Spawnpunkt
- checkpoint_marker 🔵 – Checkpoint
- goal_portal 🔵 – Zielportal
- trigger_marker 🟢 – Triggerzone
- waypoint_marker 🟢 – Wegpunkt

---

## Begleiter & Varianten (zu vorhandenen Typen)

Ideen, die direkt an bestehende Typen andocken: Begleitstücke, fehlende Teile,
Varianten und Zustände.

### environment
- door_frame 🟢, double_door 🔵, sliding_glass_door 🔵 *(zu `door`/`shutter`)*
- wall_alcove 🟢, half_wall 🟢, angled_wall 🟢, curved_wall 🟢 *(zu `wall`)*
- stair_landing 🟢 *(zu `stairs`)*, catwalk_corner 🟢 *(zu `catwalk`)*
- corner_pillar 🟢, broken_pillar 🟢 *(zu `pillar`)*
- floor_plate 🟢, access_floor 🟢 *(zu `floor_tile`/`floor_grate`)*
- ceiling_vent 🟢 *(zu `ceiling_panel`)*
- vent_grille 🟢, duct_junction 🟢, duct_corner 🟢 *(zu `vent_shaft`)*
- platform_stair 🟢, platform_edge 🟢 *(zu `platform`)*
- ladder_cage 🟢, fire_escape 🟢 *(zu `ladder`)*
- container_open 🟢, container_door 🔵 *(zu `cargo_container`)*
- bulkhead_door 🔵, bulkhead_window 🟢 *(zu `bulkhead`)*

### industrial
- pipe_t_junction 🟢, pipe_cross 🟢, pipe_cap 🟢, pipe_flange 🟢, pipe_hanger 🟢 *(zu `pipe`/`pipe_bend`)*
- tank_gauge 🟢, tank_ladder 🟢 *(zu `tank`)*
- conveyor_corner 🟢, conveyor_incline 🟢 *(zu `conveyor`)*
- fan_guard 🟢, fan_grille 🟢 *(zu `fan`)*
- machine_cover 🟢, machine_panel 🟢 *(zu `machine`)*
- substation 🟢 *(zu `transformer`)*

### nature
- mushroom_cluster 🟢, giant_mushroom 🟢 *(zu `mushroom`)*
- potted_plant 🟢, hanging_plant 🟢, dead_plant 🟢 *(zu `plant`)*
- rock_cluster 🟢 *(zu `rock`)*
- crystal_shard 🟢, crystal_growth 🟢 *(zu `hanging_crystals`/`crystal_cluster`)*
- toxic_puddle 🔵, blood_puddle 🟢 *(zu `puddle`)*
- vine_curtain 🟢 *(zu `vines`)*
- cocoon_open 🟢, cocoon_cluster 🟢 *(zu `cocoon`)*
- hydroponic_tower 🟢 *(zu `hydroponic_bed`)*

### props
- crate_open 🟢, crate_stack 🟢 *(zu `crate`)*
- locker_open 🟢, locker_row 🟢 *(zu `locker`)*
- office_chair 🟢, stool 🟢 *(zu `chair`)*
- round_table 🟢, lab_table 🟢 *(zu `table`)*
- bin_lid 🟢 *(zu `bin`)*
- traffic_cone 🟢, bollard 🟢 *(zu `barrier`)*
- oxygen_canister 🟢, chemical_canister 🟢 *(zu `canister`)*
- shelf_wall 🟢, shelf_corner 🟢 *(zu `shelf`)*

### puzzle
- emergency_stop 🔵 *(zu `button`)*
- crank 🔵 *(zu `lever`)*
- keypad_card 🔵 *(zu `keypad`/`chip_reader`)*
- valve_handle_large 🔵 *(zu `valve`)*
- item_slot 🔵, socket_multi 🔵 *(zu `socket`)*
- weight_plate 🔵, sensor_plate 🔵 *(zu `pressure_plate`)*
- fuse 🟢, circuit_breaker 🔵 *(zu `fuse_box`)*

### robots
- drone_crashed 🟢 *(zu `drone`)*
- robot_arm_ceiling 🔵 *(zu `robot_arm`)*
- android_chassis 🟢, android_damaged 🟢 *(zu `android`)*
- turret_ceiling 🔵, turret_wall 🔵, turret_damaged 🟢 *(zu `turret`)*

### ruins
- wall_cracked 🟢, wall_bullet 🟢 *(zu `broken_wall`)*
- pod_half 🟢, pod_debris 🟢 *(zu `crashed_pod`)*
- melted_console 🟢, exploded_console 🟢 *(zu `burnt_console`)*

### tech
- server_blade 🟢, server_rack_open 🟢, server_rack_damaged 🟢 *(zu `server_rack`)*
- console_wall 🟢, console_damaged 🟢 *(zu `console`)*
- terminal_kiosk 🟢, terminal_wall 🟢 *(zu `terminal`)*
- camera_pole 🟢, camera_wall 🟢 *(zu `camera`)*
- antenna_array 🟢 *(zu `antenna`)*
- monitor_single 🟢, monitor_bank 🟢 *(zu `monitor_wall`)*
- light_pendant 🔵, light_broken 🟢 *(zu `light`)*
- portal_charged 🔵, portal_inactive 🟢 *(zu `portal_frame`)*
- crystal_single 🟢 *(zu `crystal_cluster`)*

---

## Ableger & Varianten (zu vorgeschlagenen Typen)

> Optionale Ideensammlung, kein Pflichtschema: Ein neuer Typ braucht nicht automatisch
> Komponenten, Begleiter, Zustands- und Gruppenvarianten. Nur Einträge behalten, die
> einen erkennbaren Spiel-, Baukasten- oder Silhouettennutzen haben. Zustände wie
> `open`, `broken`, `charged` und `empty` bevorzugt als Parameter/Varianten modellieren,
> nicht als eigene Typen.

### Industrie-Maschinen
- furnace: furnace_door 🔵, crucible_trolley 🟢, slag_cart 🟢, furnace_chimney 🟢
- turbine: turbine_housing 🟢, turbine_blades 🟢, turbine_intake 🟢
- compressor: compressor_tank 🟢, compressor_line 🟢
- cooling_tower: cooling_tower_fan 🔵, cooling_tower_grille 🟢
- distillation_column: column_platform 🟢, column_ladder 🟢, column_valves 🔵
- silo: silo_discharge 🟢, silo_ladder 🟢, silo_hopper 🟢
- pneumatic_piston: piston_rod 🟢, hydraulic_hose 🟢
- foundry_ladle: ladle_stand 🟢, ladle_hook 🟢, ladle_slag 🟢
- rolling_mill: mill_roller 🟢, mill_stand 🟢, mill_guard 🟢
- valve_manifold: manifold_gauge 🟢, manifold_pipe 🟢
- geiger_counter: geiger_probe 🟢, geiger_holster 🟢

### Fahrzeuge
- forklift: forklift_forks 🟢, forklift_cage 🟢, pallet_load 🟢
- space_rover: rover_wheel 🟢, rover_antenna 🟢, rover_drill 🔵
- locomotive: locomotive_cab 🟢, coal_tender 🟢, rail_section 🟢, rail_buffer 🟢
- submarine: submarine_periscope 🔵, submarine_hatch 🔵, submarine_propeller 🔵
- helicopter: helicopter_rotor 🔵, helicopter_skid 🟢, helicopter_tail 🟢
- rocket: rocket_nozzle 🟢, rocket_stage 🟢, launch_pad 🟢, gantry 🟢
- dirigible: dirigible_gondola 🟢, dirigible_propeller 🔵, mooring_mast 🟢
- ambulance: ambulance_stretcher 🟢, ambulance_light 🔵, ambulance_door 🔵
- fire_truck: fire_truck_ladder 🟢, fire_truck_hose 🟢, fire_truck_pump 🔵
- excavator: excavator_bucket 🟢, excavator_arm 🔵, excavator_cab 🟢
- bulldozer: bulldozer_blade 🟢, bulldozer_ripper 🟢
- tractor: tractor_trailer 🟢, tractor_hitch 🟢
- sailboat: sailboat_mast 🟢, sailboat_rudder 🟢, sailboat_boom 🟢
- canoe: canoe_paddle 🟢, canoe_seat 🟢

### Möbel & Wohnen
- desk: desk_drawer_open 🟢, desk_organizer 🟢
- cabinet: cabinet_door_open 🔵, cabinet_shelf 🟢
- sofa: sofa_cushion 🟢, sofa_arm 🟢
- wardrobe: wardrobe_door 🔵, wardrobe_interior 🟢, wardrobe_mirror 🟢
- bunk_bed: mattress 🟢, pillow 🟢, blanket 🟢, bunk_ladder 🟢
- armchair: armchair_cushion 🟢, armchair_throw 🟢
- bookshelf_unit: book_row 🟢, book_end 🟢
- filing_cabinet: filing_drawer 🟢, filing_folder 🟢

### Küche & Haushalt
- refrigerator: fridge_door_open 🔵, fridge_magnet 🟢, fridge_contents 🟢
- stove: stove_burner 🔵, stove_knob 🟢, stove_pot 🟢
- microwave: microwave_door 🔵, microwave_turntable 🔵
- blender: blender_jar 🟢, blender_base 🟢
- espresso_machine: espresso_portafilter 🟢, espresso_grinder 🟢, espresso_cup 🟢
- cake: cake_slice 🟢, cake_stand 🟢, cake_candle 🔵
- pizza: pizza_slice 🟢, pizza_box 🟢, pizza_cutter 🟢
- sushi: sushi_roll 🟢, sushi_plate 🟢, chopsticks 🟢
- washing_machine: washing_drum 🔵, washing_door 🔵, washing_detergent 🟢
- dishwasher: dishwasher_rack 🟢, dishwasher_door 🔵
- vacuum_cleaner: vacuum_hose 🟢, vacuum_head 🟢, vacuum_bag 🟢
- ceiling_fan: ceiling_fan_blade 🔵, ceiling_fan_light 🔵

### Medizin
- gurney: gurney_mattress 🟢, gurney_rail 🟢, gurney_iv 🟢
- mri_machine: mri_bed 🟢, mri_coil 🟢, mri_control 🔵
- iv_drip: iv_bag 🟢, iv_pole 🟢, iv_tube 🟢
- defibrillator: defib_paddles 🟢, defib_monitor 🔵
- surgical_light: surgical_light_arm 🟢, surgical_light_head 🔵
- wheelchair: wheelchair_wheel 🟢, wheelchair_footrest 🟢
- operating_table: op_table_lamp 🔵, op_table_strap 🟢
- diagnostic_scanner: scanner_bed 🟢, scanner_monitor 🔵
- dental_chair: dental_light 🔵, dental_tool 🟢, dental_tray 🟢

### Labor
- centrifuge: centrifuge_rotor 🔵, centrifuge_tube 🟢, centrifuge_lid 🟢
- fume_hood: fume_hood_sash 🟢, fume_hood_duct 🟢
- microscope_station: microscope_slide 🟢, microscope_lens 🟢
- bunsen_burner: bunsen_flame 🔵, bunsen_tube 🟢
- spectrometer: spectrometer_cuvette 🟢, spectrometer_screen 🔵
- test_tube_rack: test_tube 🟢, test_tube_holder 🟢
- pipette: pipette_stand 🟢
- cryo_tank: cryo_lid 🟢, cryo_vapor 🟠

### Musik
- guitar: guitar_stand 🟢, guitar_case 🟢, guitar_amp 🔵
- drum_kit: drum_stick 🟢, cymbal 🟢, drum_stool 🟢
- piano: piano_bench 🟢, piano_lid 🟢, piano_keys 🟢
- gramophone: gramophone_horn 🟢, gramophone_record 🟢, gramophone_crank 🔵
- violin: violin_bow 🟢, violin_case 🟢, violin_stand 🟢
- cello: cello_bow 🟢, cello_case 🟢
- harp: harp_strings 🟢, harp_pedal 🟢
- jukebox: jukebox_record 🟢, jukebox_light 🔵

### Nautik
- ship_wheel: ship_compass 🟢, ship_bell 🔵, helm_stand 🟢
- porthole: porthole_frame 🟢, porthole_glass 🟢
- anchor: anchor_chain 🟢, anchor_winch 🔵, capstan 🟢
- fishing_rod: fishing_reel 🟢, fishing_hook 🟢, fishing_bait 🟢
- fishing_net: fishing_float 🟢

### Okkult & Historisch
- crystal_ball: crystal_ball_stand 🟢, crystal_ball_glow 🔵
- tarot_cards: tarot_deck 🟢, tarot_spread 🟢
- cauldron: cauldron_ladle 🟢, cauldron_fire 🔵, cauldron_bubbles 🟠
- ouija_board: ouija_planchette 🟢, ouija_board_letters 🟢
- pentagram: pentagram_candle 🔵, pentagram_circle 🟢
- monolith: monolith_base 🟢, monolith_crack 🟢
- obelisk: obelisk_hieroglyph 🟢, obelisk_base 🟢
- mummy: mummy_bandage 🟢, mummy_sarcophagus 🟢
- armor: armor_stand 🟢, armor_helmet 🟢, armor_gauntlet 🟢

### Sci-Fi
- warp_core: warp_core_rings 🔵, warp_core_housing 🟢
- teleporter_pad: teleporter_ring 🔵, teleporter_console 🔵
- clone_tank: clone_tank_tube 🟢, clone_tank_liquid 🔵
- jetpack: jetpack_nozzle 🔵, jetpack_harness 🟢
- stasis_tube: stasis_tube_glass 🟢, stasis_tube_liquid 🔵, stasis_control 🔵
- docking_port: docking_clamp 🟢, docking_seal 🟢, docking_lights 🔵
- replicator: replicator_tray 🟢, replicator_output 🟢
- vr_headset: vr_controller 🟢, vr_base_station 🔵
- cyberdeck: cyberdeck_cable 🟢, cyberdeck_screen 🔵

### Historisch (Set-Stücke)
- pyramid: pyramid_block 🟢, pyramid_entrance 🟢, pyramid_capstone 🟢
- sarcophagus: sarcophagus_lid 🟢, sarcophagus_open 🟢
- longship: longship_oar 🟢, longship_sail 🟢, longship_prow 🟢
- treasure_chest: treasure_chest_open 🔵, treasure_coins 🟢, treasure_gold 🟢

### Spielzeug & Spiele
- teddy_bear: teddy_torn 🟢, teddy_missing_eye 🟢
- doll: doll_head 🟢, doll_broken 🟢
- billiards_table: billiard_balls 🟢, billiard_cue 🟢, billiard_rack 🟢
- ping_pong_table: ping_pong_net 🟢, ping_pong_paddle 🟢
- arcade_cabinet: arcade_screen 🔵, arcade_joystick 🟢, arcade_coin_slot 🟢
- pinball_machine: pinball_flipper 🔵, pinball_ball 🟢, pinball_bumper 🟢
- slot_machine: slot_reel 🔵, slot_handle 🟢, slot_coin_tray 🟢
- roulette_wheel: roulette_ball 🟢, roulette_chips 🟢, roulette_table 🟢
- chess_board: chess_piece 🟢, chess_clock 🔵

### Licht
- lighthouse: lighthouse_lens 🔵, lighthouse_gallery 🟢, lighthouse_door 🔵
- street_lamp: street_lamp_arm 🟢, street_lamp_glass 🟢
- chandelier: chandelier_crystal 🔵, chandelier_arm 🟢

### Garten
- greenhouse: greenhouse_frame 🟢, greenhouse_glass 🟢, greenhouse_vent 🔵
- beehive: beehive_supers 🟢, beehive_frame 🟢, honey_dipper 🟢
- scarecrow: scarecrow_pole 🟢, scarecrow_hat 🟢
- pergola: pergola_beam 🟢, pergola_vine 🟢
- trellis: trellis_frame 🟢, trellis_plant 🟢
- watering_can: watering_can_spout 🟢
- wheelbarrow: wheelbarrow_wheel 🟢, wheelbarrow_handles 🟢

### Waffen
- rifle: rifle_scope 🟢, rifle_magazine 🟢, rifle_bipod 🟢
- cannon: cannon_carriage 🟢, cannon_wheel 🟢, cannon_ball 🟢
- sword: sword_sheath 🟢, sword_stand 🟢, sword_broken 🟢
- crossbow: crossbow_bolt 🟢, crossbow_quiver 🟢
- chainsaw: chainsaw_bar 🟢, chainsaw_chain 🟢, chainsaw_handle 🟢
- flamethrower: flamethrower_tank 🟢, flamethrower_nozzle 🔵
- energy_weapon: energy_cell 🟢, energy_holster 🟢
- axe: axe_handle 🟢, axe_head 🟢, axe_block 🟢

### Natur & Tiere
- alien_tree: alien_fruit 🟢, alien_leaf 🟢, alien_bark 🟢
- alien_egg: alien_egg_open 🟢, alien_embryo 🟢, alien_slime 🟢
- mushroom_cluster: mushroom_cap 🟢, mushroom_stem 🟢
- dragon: dragon_egg 🟢, dragon_wing 🟢, dragon_scale 🟢, dragon_claw 🟢
- spider: spider_egg_sac 🟢

### Sicherheit & Gefängnis
- metal_detector: detector_gate 🔵, detector_panel 🔵
- turnstile: turnstile_arm 🔵, turnstile_card_reader 🔵
- watchtower: watchtower_platform 🟢, watchtower_ladder 🟢, watchtower_spotlight 🔵
- bunker: bunker_door 🔵, bunker_slit 🟢

### Wissenschaft & Wetter
- orrery: orrery_planet 🔵, orrery_arm 🟢, orrery_gear 🟢
- telescope: telescope_tripod 🟢, telescope_eyepiece 🟢, telescope_mount 🔵
- dna_model: dna_base 🟢, dna_strand 🟢
- tesla_coil: tesla_sphere 🔵, tesla_ring 🟢
- weather_vane: vane_arrow 🔵, vane_rooster 🟢
- theodolite: theodolite_tripod 🟢, theodolite_scope 🔵

---

## Systeme (rund um die Modelle)

> Ideen-Backlog ohne zugesagten Umsetzungsstatus. Bereits vorhandene Funktionen zuerst
> in Registry, Code, Vertrag und Changelog prüfen, bevor ein Punkt als offen oder erledigt
> markiert wird. Raum-/Level-Generator bleibt nachrangig; Clutter soll aus weiterhin
> einzeln verfügbaren Assets bestehen.

### Generierung
- **Raum-/Level-Generator** *(nach hinten gestellt)* – aus `families.connectors` + `snapping.py` Räume nach Seed zusammensetzen; Ausgabe Layout-JSON für Unity.
- [x] **Clutter-/Accessoire-Pass (erste Stufe, 0.10.4.1)** – deterministische Props mit Dichte `clean` → `lived-in` → `chaotic` auf freigegebenen Tischflächen; eigene `Clutter_*`-Meshes, Einzeltypen separat exportierbar. Weitere Oberflächen und Unity-Laufzeitprüfung bleiben offen.
- **Composite-/Kitbash-Typen** – Rezept, das zwei vorhandene Teile kombiniert (z. B. `wall` + `vent` + `pipe`).
- **Seed-Morphing** – zwischen zwei Seeds interpolieren, um gezielt zwischen guten Varianten zu suchen.

### Visual & Material
- **Decal-/Beschriftungs-System** – Warnstreifen, Raumnummern, Pfeile, Graffiti, Rost-/Kantenabnutzung (baut auf `lettering.py` auf).
- **Wear als Ebenen** – Staub/Rost/Moos/Ruß/Eis getrennt kombinierbar; Theme wählt die Ebenen.
- **Ambient-Animation** – Idle-Bewegung als Metadaten (Rotorgeschwindigkeit, Blinkmuster, Schwenkbereich) für Unity.
- **Mood-/Atmosphären-Presets** – Paletten-Modus + Lichtfarbe + Nebel + Wear-Dichte als benannte Pakete.

### Gameplay & Logik
- **Zustands-System** – powered/unpowered, open/closed, clean/dirty + Degradationskette im Sidecar.
- **Puzzle-Graph-Generator** – welche Rätsel brauchen welches Item → Abhängigkeits-/Quest-JSON.
- **Item-Ökonomie** – Raritäten/Gewichte für `ItemPickup`, pro Theme gerollt.
- **Audio-Trigger** – über `Audio_*` hinaus: Trigger-Zonen (Türquietschen, Brummen-Radius, Bodenmaterial).

### Unity-Integration
- **Prefab-/Addressables-Generierung** – Bundle-Definitionen zur Batch.
- **Lightmap-UV-Channel** – zweiter UV-Kanal für Baking.
- **Physik-Metadaten** – Masse/Rigidbody-Hinweise für Fragmente und bewegliche Teile.
- **ScriptableObject-Ausgabe** – Sidecar zusätzlich als Unity-ScriptableObject.

### QA & Tooling
- **Geometry-Health-Check** – nicht-manifold, Normalen, degenerierte Faces und offene Kanten; Umfang gegen aktuelle QA prüfen.
- **Visuelle Regression in der CI** – Referenzbilder + Pixel-Diff (Anlass: Blender in die CI).
- **Seed-Gallery (HTML)** – N Varianten browsen, auswählen, `--pick` kopieren.
- **Config-/Schema-Versionierung** – Migration für Rezepte/Familien (wie `--generation` für Modelle).

### Ökosystem
- **Plugin-/Extension-API** – eigene Typen als externe Dateien/JSON.
- **Theme-Packs** – Familie + Palette + Material + Wear + Clutter-Dichte als Paket.
- **Community-Rezepte** – versionierte, teilbare Rezepte (Seed + Rezept).

---

## Level-Szenarien und Puzzle-Abläufe

> Die folgenden Beispiele sind Vorlagen, keine fertig gebauten Level. Agenten dürfen
> konkrete Assets austauschen, müssen Ziel, Hinweise, Zustandsübergänge, Feedback und
> Softlock-Schutz aber erhalten oder begründet neu spezifizieren.

### Szenario: Notstrom für den Sektor

- **Ziel:** Einen gesperrten Stationssektor wieder mit Strom versorgen.
- **Einstieg / Hinweis:** Dunkle Anzeigen und ein Wartungsprotokoll nennen eine ausgelöste
  Sicherung sowie einen überlasteten Nebenstrang.
- **Ablauf:** Spieler findet eine Sicherung oder Energiezelle; isoliert den fehlerhaften
  Zweig; leitet Strom über Schalter/Relais zum Hauptbus; aktiviert den Sektor.
- **Bausteine:** `fuse_box`, `switch_panel`, `generator`, `battery_bank`; optional als
  spätere Assets `fault_isolator`, `power_bus`, `power_cell`.
- **Zustände / Feedback:** `offline` → `isolated` → `partial_power` → `online`.
  Anzeigen schalten sich abschnittsweise ein und benennen den verbleibenden Fehler.
- **Ausgang / Fehlerbehandlung:** Tür oder Lift wird freigegeben. Falsche Schaltung löst
  einen sichtbaren Reset oder eine Sicherungsauslösung aus, aber verbraucht kein
  unverzichtbares Item dauerhaft.

### Szenario: Schleusenstörung

- **Ziel:** Den Außenbereich erreichen, ohne beide Schleusentüren gleichzeitig zu öffnen.
- **Einstieg / Hinweis:** Druckanzeige und Warnmarkierung zeigen, welche Seite noch
  unter Druck steht; ein Schild erklärt die Reihenfolge.
- **Ablauf:** Innenraum versiegeln; Druckausgleich starten; Bestätigung abwarten; Außentür
  freigeben; nach Durchgang den Zyklus schließen.
- **Bausteine:** vorhandene `door`, `hatch`, `pressure_gauge`, `switch_panel`,
  `countdown`; vorgeschlagen `airlock_chamber`, `pressure_equalizer`, `airlock_door`.
- **Zustände / Feedback:** `sealed` → `equalizing` → `safe_to_open` → `crossing` →
  `cycle_complete`. Türleuchten und Druckanzeige müssen konsistent sein.
- **Ausgang / Fehlerbehandlung:** Bei falscher Reihenfolge Türen bleiben verriegelt und
  die Anzeige erklärt den Grund. Kein tödlicher Druckabfall ohne vorherige Warnung;
  Reset bleibt aus dem Raum erreichbar.

### Szenario: Signal zum Sicherheitsknoten umleiten

- **Ziel:** Eine Zugangssperre durch Wiederherstellung des Stationssignals freigeben.
- **Einstieg / Hinweis:** Wartungsdisplay zeigt einen unterbrochenen Pfad; ein räumlicher
  Hinweis identifiziert den defekten Knoten.
- **Ablauf:** Signalquelle lokalisieren; Knoten/Leitung ausrichten; Frequenz oder Phase
  anpassen; am Empfänger die erfolgreiche Verbindung bestätigen.
- **Bausteine:** `antenna`, `freq_dial`, `switch_panel`, `monitor_wall`, `signal_light`;
  vorgeschlagen `signal_node`, `signal_router`, `phase_relay`, `diagnostics_port`.
- **Zustände / Feedback:** `disconnected` → `searching` → `near_match` → `connected`.
  Feedback muss Richtung und Fortschritt vermitteln, ohne die Lösung grundlos zu raten.
- **Ausgang / Fehlerbehandlung:** Sicherheitsfreigabe wird ausgelöst. Fehlstellungen
  lassen sich zurückstellen; eine kurze Diagnose nennt das betroffene Segment.

### Szenario: Kühlkreislauf stabilisieren

- **Ziel:** Überhitzung stoppen und den Reaktorkern auf einen sicheren Betriebsbereich bringen.
- **Einstieg / Hinweis:** Temperatur-/Druckanzeigen und Leckspuren führen zur defekten
  Leitung; die sichere Zielspanne ist im Raum sichtbar dokumentiert.
- **Ablauf:** Gefahr erkennen; Leck isolieren; Ventile so stellen, dass Kühlmittel den
  Kern erreicht; Durchfluss prüfen; Reaktor stabilisieren.
- **Bausteine:** `reactor_core`, `pipe`, `pipe_bend`, `pump`, `valve`, `fluid_basin`,
  `pressure_gauge`, `steam_vent`; vorgeschlagen `coolant_loop`, `vent_damper`.
- **Zustände / Feedback:** `overheated` → `leak_isolated` → `cooling` → `stable`.
  Druck und Temperatur reagieren schrittweise auf Spieleraktionen.
- **Ausgang / Fehlerbehandlung:** Ein falscher Pfad darf eine erkennbare Warnung und
  umkehrbare Fehlstellung auslösen; kein unvermeidlicher Tod oder dauerhaft blockierter
  Durchgang durch einen einzigen Fehlklick.

### Verbindliches Szenario-Schema

Für jedes neue Szenario dokumentieren:

1. **Ziel und Kontext:** Was soll der Spieler erreichen und warum?
2. **Hinweis:** Welche beobachtbare Information macht die Lösung erschließbar?
3. **Voraussetzungen:** Welche Items, Fähigkeiten und Räume sind erforderlich?
4. **Ablauf:** Aktion für Aktion, mit Auslösern und Zustandsübergängen.
5. **Feedback:** Sichtbar, hörbar oder textlich; einschließlich Fehlermeldung.
6. **Erfolgsauswirkung:** Was ändert sich im Raum, Level oder Fortschritt?
7. **Reset / Softlock-Schutz:** Wie kann der Spieler Fehler korrigieren und weiterspielen?
8. **Asset- und Script-Liste:** Vorhandene Assets, Vorschläge, Verhalten, Adapter und
   noch offene Implementierung.
9. **Abnahme:** Wie werden Lösung, Wiederholbarkeit und Unity-Spielbarkeit überprüft?

Ein Puzzle ist fair, wenn relevante Hinweise auffindbar sind, die Rückmeldung Ursache
und Wirkung verbindet, wichtige Items nicht unwiederbringlich verloren gehen und der
Spieler einen fehlgeschlagenen Zustand verlassen kann. Zeitdruck braucht klare Warnung,
einen nachvollziehbaren Timer und ein definiertes Wiederholen.

---

## Langzeit-Systemideen und offene Richtungen

> Backlog, keine aktuelle Zusage. Bereits umgesetzte Funktionen vor einer Wiederaufnahme
> im Changelog und Code prüfen; insbesondere keine erledigten Vorhaben als „offen“ führen.

### Level- und Asset-Workflows

- Clutter-/Accessoire-Pass erste Stufe in 0.10.4.1 umgesetzt; weitere Flächen, Hindernisbeschreibungen und echte Unity-Prüfung offen.
- Composite-/Kit-Rezepte aus vorhandenen Modellen und kompatiblen Anschlüssen.
- Raum-/Level-Generator auf Basis von Connectors und Snapping; ausdrücklich später
  priorisieren, bis die Asset- und Puzzle-Grundlagen stabil sind.
- Seed-Galerie zum Durchsehen und Auswählen reproduzierbarer Modellvarianten.

### Visuals und Zustände

- Vorhandene Palette-, Wear- und Animationsmöglichkeiten zu getesteten Mood-Presets
  kombinieren; nicht als neue Grundfunktionen einplanen, ohne den aktuellen Stand zu prüfen.
- Zustandsvarianten und Ambient-Animationen als Sidecar-Metadaten nur erweitern, wenn der
  Unity-Vertrag sie unterstützt und der Nutzen über vorhandene Verhaltensdaten hinausgeht.
- Das vorhandene Beschriftungsvermögen zu einem konsistenten Leitsystem aus
  Sektorkennungen, Warnstufen und Richtungshinweisen ausbauen.

### Gameplay und Qualität

- Puzzle-Abhängigkeitsgraph nur aus explizit beschriebenen Voraussetzungen erzeugen.
- Physik-, Audio- und Interaktionsmetadaten am Unity-Vertrag ausrichten.
- Offene Geometrie-/Visual-QA-Lücken erst nach Code-/Testprüfung als offen kennzeichnen.

---

## Zurückgestellte Themen

Der Katalog enthält in mehreren Kategorien auch Randideen, die nicht zur engen
Indoor-Station-Ausrichtung passen. Es gilt keine pauschale Sperre nach Kategorie:
`robots`, `ruins` oder `nature` können mit einem konkreten Stations-, Story- oder
Puzzle-Nutzen passend sein. Ideen ohne solchen Anwendungsfall bleiben im Backlog und
werden nicht priorisiert. Auf einen separaten Ausschlusskatalog wird verzichtet, damit
Einträge und Grenzfälle nicht an zwei Stellen gepflegt werden müssen.

# Roadmap

Stand: 6. Oktober 2026, cubegen 0.9.0 plus die Korrekturen unter „Unveröffentlicht“ im [CHANGELOG](../CHANGELOG.md).
Zahlen aus `python -m cubegen check` (Seed 42, 10 Varianten pro Typ). Jede Liste beginnt mit dem Wichtigsten.

## 1. Bekannte Bugs

**Offen**

1. **Unity-Prüfung läuft nicht beim Export.** `cubegen/contract.py` wird nur in den Tests aufgerufen, nicht in
   `generate`. Changelog und `docs/UNITY_INTEGRATION.md` sagen aber, jeder Sidecar werde vor dem Export geprüft.
   Mit eigenen Parametern oder einer Familie kann ein Modell entstehen, das Unity ablehnt, ohne Warnung.
2. **Flackernde Flächen (Z-Fighting) bei 50 Typen**, am stärksten `door` (1,26 m² am `Frame_Top`),
   `vent_shaft` (58 Paare), `window_wall` (44), `hydroponic_bed` (24), `floor_grate` (18).
3. **Zu viele Draw Calls (über 16):** `sliding_puzzle` 48, `spider_bot` 23, `conveyor` 21,
   `breakable_platform` 18, `switch_panel` 17.
4. **`window_wall` und `wall_corner` passen nicht zu `foundry` und `lab`:** feste Maße (3 m hoch, 0,5 m dick,
   Brüstung höchstens 1,5 m).
5. **Wenig Abwechslung:** `camera`, `laser_mirror`, `laser_receiver`, `laser_splitter` und `tool` haben nur 7 von
   10 unterschiedliche Varianten.
6. **Add-on:** „Von jedem Typ (129 × n)“ zählt Typen mit, die nicht zur gewählten Familie passen.
7. **Doku veraltet:** README nennt „getestet mit Blender 4.0“ (im Einsatz: 5.2.2); die Parametertabelle im
   README fehlt für Teile der Typen seit 0.7 (`python -m cubegen params` ist vollständig).

**Behoben (Unveröffentlicht)**

* Add-on: Vorschau, Raster und „Kit bauen“ brachen mit Familie `foundry` oder `lab` ab.
* `door` Stil `airlock`: Die beiden Blätter fuhren in Unity durcheinander hindurch, die Tür blieb zu.

## 2. Verbesserungen am bestehenden System

1. **Unity-Prüfung beim Export** (`check_sidecar` vor dem Schreiben, `check_fbx` danach) und
   `cubegen check --export <Ordner>` für fertige Exporte (`check_export` gibt es schon). Behebt Bug 1.
2. **Versionsschalter** (`--generation 2`, Rezept `"generation": 2`): Korrekturen wie für Bug 2 und 3 ohne
   bestehende Seeds zu verändern; alte Exporte bleiben bitgleich.
3. **`window_wall` und `wall_corner` mit Höhe, Dicke und Brüstung als Parameter**, damit sie allen Familien
   folgen. Danach bekommen alle Kits eine Eckwand.
4. **Mehr Varianten-Parameter** für die Typen aus Bug 5.
5. **Ein gemeinsamer Vertrag:** die Regeln des Unity-Imports als maschinenlesbare Datei, aus der `contract.py`
   und der Unity-Import lesen, statt sie doppelt zu pflegen.
6. **Blender in der CI:** Die 7 Blender-Tests (Add-on, echter FBX-Export) werden heute übersprungen.
7. **Add-on:** Typen, die nicht zur gewählten Familie passen, im Typ-Menü kennzeichnen und nicht mitzählen.
8. **Doku aktualisieren:** Blender-Version, vollständige Parametertabelle.

## 3. Erweiterungen

**Funktionen**

1. **Raum- und Level-Generator:** setzt aus den Anschlusspunkten der Familien (`connectors` im Manifest) einen
   ganzen Raum nach Seed zusammen; Ausgabe als Layout-JSON für Unity.
2. **Einrasten im Blender-Add-on:** Kit-Teile rasten an ihren Anschlusspunkten ein.
3. **Paletten-Modus:** ein Material mit Farbpaletten-Textur pro Modell, also ein Draw Call.
4. **Symmetrisches Schwenken** für `camera` und `turret`: Rotor um den halben Winkel vorgedreht gebaut, dann
   schwenkt das vorhandene `Rotator.arc` um ±60°.
5. **Weitere Familien:** `medbay`, `derelict`, `greenhouse`, `reactor`, jeweils mit Requisiten im Kit.
6. **Zustand `fractured`:** Modell in Bruchstücke zerlegt, die Unity bei Zerstörung herausfallen lässt.
7. **Text auf Modellen:** Raumnummern und Beschriftungen (`sign.text=B-12`).
8. **Anker für Ton und Effekte:** leere Teile wie `Audio_Hum`, `FX_Steam`.

**Neue Modelltypen**

| Bereich | Vorschläge |
|---|---|
| Bau-Kit | Rampe, Decken- und Dachmodul, Durchgang / Torbogen, Wandabschluss, Sockelleiste |
| Rätsel | Gewichtsblock zum Schieben (passt zur Druckplatte), Ton- und Farbfolge-Panel, Wasserstand-Rätsel, Farbfilter für Laser, Symbolplatten, Kran / Magnet, Countdown-Anzeige |
| Requisiten | Labor (Mikroskop, Reagenzglas-Ständer, Zentrifuge), Küche / Messe, Waschraum, Lageplan |
| Licht | Flutlicht, Neon- und LED-Leisten, Notbeleuchtung |
| Roboter | Patrouillen-Drohne, Kriecher für Lüftungsschächte, Roboterhund, Industrie-Mech |
| Natur / Alien | Ranken, Kokons, Wurzeln durch Wände, Pilzteppiche, Pfützen |
| Außen / Weltraum | Rettungskapsel, Solarpanel, Asteroid, Fenster mit Planet |
| Ruinen | abgestürzte Kapsel, ausgebrannte Konsole, eingestürzter Steg |

## 4. ToDo für Unity

Details zu den Mechaniken in [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md).

**Sofort**

1. **Audit-Test aktualisieren:** Er erwartet noch 3 Ablehnungen
   (`CUBEGEN_EXPECT_REJECTED=balance_scale,robot_arm,turret`); diese Pivot-Fehler sind seit 0.8.0 behoben. Mit dem
   aktuellen Stand ohne die Ausnahme neu laufen lassen, erwartet: 0 Ablehnungen.
2. **Luftschleusen neu importieren**, sobald die Korrektur in `main` ist.
3. **8 offene Item-IDs:** `ItemData` für Akku, Datenchip, Sicherung, Keycards, Werkzeuge und Hinweise festlegen,
   dann im Rezept per `item_id` setzen (cubegen erfindet keine IDs).

**Mit vorhandenen Scripts oder kleinen Ergänzungen**

4. **Zwei-Stellungs-Klappen** für `hatch`, `fuse_box`, `cage`, `safe`: `Rotatable` dreht zyklisch weiter, der
   zweite Klick dreht den Deckel durch den Körper.
5. **Lift über `MovingPlatform`** statt `Door`.
6. **Mitfahren** auf `retractable_bridge` (Verschiebung) und `turntable` (Drehung).
7. **Sockel über `ItemSlot`** (`socket`, `chip_reader`, `battery_bank`, `fuse_box`, `Slot` als Einsetzpunkt);
   Mehrfachsockel ergänzen.
8. **`pressure_plate` an `PressurePlate`** anbinden.

**Neue Mechaniken**

9. **Schadenszonen:** `spike_trap`, `crusher`, `saw_blade`, `steam_vent`, `shock_plate`.
10. **Nur vorbereitet:** `portal_frame`, `phase_platform`, `breakable_platform`, `fluid_basin`.
11. **Laser im Raum** mit Spiegeln und Teiler; Controller für das Rohr-Puzzle.
12. **Weitere Interaktionen:** Knopffolgen, Steckfeld, Scanner, Tresor, Werkzeuge als Schlüssel, Schieberätsel,
    Waage, Frequenz-Regler, Taschenlampe, Leiter, Pads, Förderband, Geschütz, Leerlauf-Animation für Drohne und
    Roboterarm.

**Freigabe und Struktur**

13. **Werkbank-Freigabe** neuer Gameplay-Prefabs im `AssetMetadata`-Vertrag.
14. **LOD-Hüllen prüfen:** Collider nur von LOD0.
15. **Import der Anschlusspunkte bzw. des Layout-JSON**, falls der Raum-Generator kommt.

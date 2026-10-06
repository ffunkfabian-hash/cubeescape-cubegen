# Generierte Modelle in Unity verdrahten

`cubegen` schreibt neben jede FBX eine `<Name>.cubegen.json`. Sie enthält, was ein Prefab-Builder sonst als
Rezeptzeile in `ModularBlocks.cs` bräuchte: Teile, Pivots (Unity-Koordinaten), Script und Feldwerte.
Der Prompt unten lässt eine KI im **Unity-Projekt** einen Editor-Import dafür bauen – an die vorhandenen Builder
angeschlossen, ohne Laufzeit-Scripts zu ändern. Ein zweiter, optionaler Prompt
([Neue Interaktionen](#optional-neue-interaktionen)) ergänzt die Spiel-Mechanik, für die es noch kein Script gibt
(Item-Sockel, Laser, Druckplatte, Rohr-Puzzle, Kamera-Schwenk …).

## Prompt

````text
Projekt: Unity-Spiel "Cube Escape". Prefabs werden von Editor-Buildern gebaut
(Assets/Scripts/Editor/PrefabLibrary*.cs, Rezepte in ModularBlocks.cs). Sie suchen Modellteile per Name
(Pflicht: PrefabLibrary.cs ~Zeile 1024, optional: PrefabLibrary.Modular.cs FindPart) und schreiben die
Verweise in [SerializeField]-Felder der Laufzeit-Scripts (Door, Machine, Rotator, Rotatable, SignalLight,
SignalIndicator, ItemPickup …). Animationen laufen prozedural, es gibt keine Clips.

Ein externer Generator (cubegen) legt neue Modelle als Assets/Art/Models/<Name>.fbx ab und daneben
<Name>.cubegen.json. Schema:

{
  "model": "Gen_Door_002", "type": "door", "category": "environment",
  "pivot": "floor|top|center|wall", "seed": 973947131, "masterSeed": 42,
  "static": false,                      // true = reine Deko ohne Script
  "bounds": {"center": [x,y,z], "size": [x,y,z]},          // Unity-Koordinaten
  "parts": [ {"name": "Panel", "parent": null, "localPosition": [x,y,z],
              "empty": false, "materials": ["M_Metal", "M_RobotDark"],
              "bounds": {"center": [x,y,z], "size": [x,y,z]}} ],   // Collider-Hinweis relativ zum Pivot des Teils
  "behaviours": [
    {"script": "Door",
     "parts":  {"panels": ["Panel","Panel_B"], "statusLights": ["StatusLight_Front","StatusLight_Back"],
                "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left","Frame_Right","Frame_Top"]},
     "fields": {"openOffset": [1.25,0,0], "speed": 1.8}}
  ],
  "colliders": [                        // optional, nur bei begehbaren / bewegten Typen
    {"type": "box", "part": null, "center": [x,y,z], "size": [x,y,z], "rotation": [x,y,z,w]},
    {"type": "box", "part": "Panel", ...},           // hängt am Teil, bewegt sich mit ihm
    {"type": "mesh", "part": "Deck", "convex": true}  // MeshCollider auf dem Mesh des Teils
  ]
}

Vorkommende behaviours (Script → parts → fields):
- Door            → panels[], statusLights[], upperFrame[], colliders[] → openOffset (Vector3), speed
- Machine         → body, glow, [rotor], [damage]                      → needsPower
- Rotator         → target                                             → axis ("right"|"up"|"forward"), speed (°/s)
- Rotatable       → target, glow                                       → axis, step, speed, target, interactive
- SignalLight     → glow, [rotor]                                      → mode ("Steady"|"Blink"|"Pulse"|"Rotate"|"Status")
- SignalIndicator → renderers[]                                        → offMaterial, onMaterial (Materialnamen)
- ItemPickup      → model[]                                            → spin (°/s)
Achsnamen meinen Vector3.right/up/forward im lokalen Raum. Materialnamen sind die M_*-Materialien der
MaterialLibrary.
Weitere Regeln:
- Ein Modell kann dasselbe Script mehrfach haben (conveyor: ein Rotator je Roller_<n>, drone: einer je
  Rotor_<n>, bei Drohnen mit negativem speed für gegenläufige Propeller) - jeder Eintrag = eine Komponente.
- Rotatable.step ist nicht immer 90 (laser_mirror 45, fuse_box = Deckelwinkel, lever = Stellungsabstand).
- Door bewegt auch Nicht-Türen: lift hat panels = ["Deck"] und openOffset = (0, Hub, 0).
- Leere Teile ("empty": true) sind Ankerpunkte und müssen als Transforms erhalten bleiben: Slot / Slot_<n>
  (hier sitzt ein eingesetztes Item: socket, chip_reader, fuse_box, battery_bank), Beam (Startpunkt des
  Laserstrahls von laser_emitter). Wenn es im Projekt ein passendes Feld gibt (z. B. ein Item-Sockel-Script),
  schlage die Zuordnung vor, statt eines zu erfinden.
- Gelenkketten haben Parents (robot_arm: Turret > Arm_Lower > Arm_Upper > Gripper; service_robot: Glow unter
  Head). Die Hierarchie aus "parent" übernehmen.
- Rotatable.target = Lösungsstellung in Schritten ab der Ruhelage, interactive = der Spieler darf drehen.
  pipe_fitting: Stellung 0-3, welche Kanten das Stück in Ruhe verbindet, steht im "note" des Eintrags.
- Rotator dreht endlos. Für antenna/radar und Lüfter ist das richtig; camera hat deshalb standardmäßig
  speed 0 (steht), service_robot bekommt für den Kopf nur mit head_speed > 0 einen Rotator. Einen Rotator
  mit speed 0 trotzdem anlegen (deaktiviert), damit ein späteres Schwenk-Script ihn ersetzen kann.
- Collider: statische Modelle bekommen über AssetRegistry eine BoxCollider-Hülle. Hat die JSON "colliders",
  ersetzen diese die Hülle - bei Prefabs mit Script UND bei statischen Modellen (prüfe, wie AssetRegistry die
  Hülle anlegt, und lies dort die JSON neben der FBX mit). Regeln:
  - "part": null = Wurzel, sonst das Teil (Transform per Name). Der Collider bewegt sich mit dem Teil (Luken-Deckel,
    Lift-Deck, Kraftfeld, Pressenkopf, Käfigtür); bewegte Teile brauchen wie bisher einen kinematischen Rigidbody.
  - "box": center / size in Unity-Koordinaten relativ zum Teil. rotation ist ein Quaternion (x, y, z, w). Bei
    (0, 0, 0, 1) den BoxCollider direkt auf das Teil legen (center / size setzen). Sonst ein Kind-Objekt
    "Collider_<n>" mit localPosition = center, localRotation = new Quaternion(x, y, z, w) und einem BoxCollider
    (center 0, size = size) - BoxCollider selbst kann nicht drehen (Rampe, Wendeltreppe, Treppengeländer).
  - "mesh": MeshCollider mit sharedMesh = Mesh des Teils, convex wie angegeben (platform, floating_island).
  - Gibt es kein "colliders", bleibt alles wie bisher. Wand- und Deckenteile (pivot "wall") brauchen nur
    Collider, wenn man sie berühren kann.
  Typen mit "colliders": stairs, spiral_stairs, catwalk, platform, floor_tile, floating_island, hatch,
  floor_grate, vent_shaft (innen begehbar), lift, force_field, crusher, cage, railing, shock_plate, saw_blade.
- Weitere Typen mit den vorhandenen Scripts:
  - Door bewegt auch force_field (panels = ["Field"], openOffset nach unten: das Feld verschwindet im Boden;
    sein Collider steht in "colliders" mit part "Field") und shutter (Rolltor, nach oben).
  - Door bewegt auch crusher: panels = ["Panel"] (Pressenkopf), openOffset = (0, -Hub, 0) - "offen" heißt hier
    zugeschlagen, der Kopf landet auf der Bodenplatte. Der Takt kommt aus der Spiel-Logik.
  - Rotatable.step darf negativ sein: hatch klappt den Deckel "Panel" mit negativem step um Unity right nach
    oben. Kinder eines bewegten Teils übernehmen ("parent"): hatch "Wheel" unter "Panel"; safe "Wheel",
    "Glow" und "Screen" unter "Panel" (Tür). safe hat zwei Rotatables: Rad (interactive, target = Code-Ziffer)
    und Tür (interactive false - geht auf, wenn das Schloss gelöst ist).
  - gear_puzzle: ein Rotator je "Gear_<n>", Tempo nach Übersetzung und gegenläufig. Diese Rotatoren
    deaktiviert anlegen; sie laufen erst, wenn das Werk vollständig ist. Fehlt ein Rad, gibt es "Slot".
  - laser_splitter: leere Teile "Beam_A" / "Beam_B" sind Kinder von "Prism" (Strahlausgänge).
  - Machine mit needsPower false (transformer, reactor_core) ist eine Energiequelle.
  - Leere oder Teile ohne Script, die erhalten bleiben müssen: "Button" / "Button_<n>" (button, intercom:
    werden beim Drücken ~1,5 cm Richtung Wand geschoben), "Plug" (cable_plug), "Grille" (vent_shaft),
    "Gun" (turret, Kind von "Turret"), "Leg_<n>" (spider_bot, Pivot an der Hüfte), "Head" (android).
  - Weitere Rotatables: combination_lock (je Ring "Dial_<n>" einer, axis right, step 36, target = Ziffer),
    freq_dial ("Dial_<n>", axis forward), switch_panel ("Switch_<n>", zwei Stellungen), cage (Tür "Panel",
    axis up, negativer step, interactive false - der Käfig geht per Signal auf; "Glow" ist Kind von "Panel"),
    balance_scale ("Beam", interactive false; "Pan_A" / "Pan_B" sind Kinder von "Beam", darauf die leeren
    "Slot_A" / "Slot_B"). Mehrere Rotatables teilen sich ein "Glow".
  - saw_blade: Rotator am Blatt "Rotor" (axis forward) + SignalLight. steam_vent: leeres "Steam" ist der
    Ansatzpunkt für ein Partikelsystem (nach Unity-oben); optional Rotatable am Absperrventil "Wheel".
  - sliding_puzzle: "Tile_<n>" ohne Script (Mechanik im zweiten Prompt), Anordnung in meta.layout, Raster
    meta.pitch_m; SignalIndicator am "Glow".
  - Items mit ItemPickup: auch flashlight, key, cable_reel.

Optional erzeugt cubegen Texturen (sonst bleiben alle Materialien die bekannten M_*-Materialien):
- "tiled": Materialien MT_<Name> (z. B. MT_Metal), beschrieben in <Texturordner>/CubeEscape_Textures.json:
  {"materials": [{"name": "MT_Metal", "base": "M_Metal", "maps": {"Albedo": "MT_Metal_Albedo.png",
  "Normal": "MT_Metal_Normal.png", "MetallicSmoothness": "MT_Metal_MetallicSmoothness.png", ...},
  "metallic": 0.6, "smoothness": 0.55, "tile_m": 1.0}]}  (UV0 = Box-Projektion in Metern, Tiling 1/1)
- "baked": pro Asset ein Material MTA_<Model>; die Dateien stehen in der <Name>.cubegen.json unter
  "textures": {"mode": "baked", "baked": {"Albedo": ..., "Normal": ..., "MetallicSmoothness": ...}}
Glow-/Status-Materialien (M_Glow*, M_Crystal, M_Glass) sind nie texturiert und bleiben M_*.
Modelle mit "static": true (auch zerstörte Varianten und die Ruinen-Typen) haben keine Scripts.

LODs (nur mit --lods exportiert, nur statische Modelle): In der FBX heißt jedes Teil <Teil>_LOD0 und
<Teil>_LOD1, deshalb legt Unitys Model-Importer die LODGroup selbst an. "parts" nennt beide Stufen genau so
wie die FBX, "colliders" zeigen auf LOD0. Nichts an der LODGroup ändern.

Die FBX passt immer exakt zur JSON (cubegen liest jede FBX nach dem Export zurück und vergleicht Eltern,
localPosition, Rotation 0 und Vertices). Weicht ein importiertes Modell trotzdem ab: nicht die Toleranz
lockern, sondern das Modell ablehnen und melden.

Aufgabe:
1. Prüfe zuerst, ob die Feldnamen oben zu den echten Feldern der Scripts passen. Liste jede Abweichung
   (z. B. heißt das Feld in Door anders, oder Machine kennt keine Rotor-Achse) und schlage die Abbildung vor,
   bevor du Code schreibst.
2. Baue einen Editor-Import (Menüpunkt z. B. "Cube Escape/Import cubegen models"), der alle
   Assets/Art/Models/*.cubegen.json liest und für jedes Modell mit "static": false ein Prefab baut.
   Nutze dafür die VORHANDENEN Builder-Funktionen und Hilfsmethoden (AddModel, FindPart, AddBoxFromMesh,
   kinematischer Rigidbody für bewegte Teile, MaterialLibrary …). Die Werte kommen aus der JSON statt
   aus einer festen Rezeptzeile – genauso wie die bestehenden Rezepte für Door_Sliding, Machine_Small,
   Valve, EmergencyLight usw.
3. Modelle mit "static": true bekommen kein Prefab mit Scripts (sie gehören nach Art/Models/Library/<Kategorie>
   und werden von AssetRegistry registriert) - ihre MT_/MTA_-Materialien aus Schritt 5 aber trotzdem, und ihre
   "colliders" (siehe oben) statt der BoxCollider-Hülle.
4. Keine Änderungen an Laufzeit-Scripts. Fehlende Teile: Warnung ins Log, Modell überspringen.
5. Materialien: MT_*/MTA_* NICHT auf M_* remappen, sondern aus den JSON-Angaben als URP/Lit-Materialien
   anlegen (Albedo -> Base Map, Normal -> Normal Map, MetallicSmoothness -> Metallic Map mit Smoothness aus
   Alpha) und auf die Slots gleichen Namens legen. M_* weiterhin wie bisher remappen.
6. Wiederholbar: erneuter Import überschreibt die generierten Prefabs (gleicher Name), nichts anderes.
7. Am Ende eine Zusammenfassung im Log: gebaut / übersprungen / Warnungen.
Zeige mir vor der Umsetzung den Plan und die Feld-Abbildung aus Schritt 1.
````

## Optional: neue Interaktionen

Die meisten neuen Typen bringen Teile und Ankerpunkte für Mechanik mit, die das Spiel noch nicht hat. Dieser
Prompt lässt eine KI dafür **neue** Laufzeit-Scripts anlegen. Erst ausführen, wenn der Import oben läuft.

````text
Projekt: Unity-Spiel "Cube Escape". Generierte Modelle (cubegen) werden schon per Editor-Import zu Prefabs
mit den vorhandenen Scripts (Door, Rotatable, Rotator, SignalLight, SignalIndicator, ItemPickup …).
Jedes Modell hat eine <Name>.cubegen.json mit "type", "params", "parts" (Name, Parent, localPosition,
bounds) und "behaviours". Einige Typen brauchen Mechanik, die es noch nicht gibt.

Regeln:
- Zuerst prüfen, wie das Spiel Signale/Schalter verbindet (z. B. wie ein Rotatable oder Terminal eine Tür
  öffnet) und welche Systeme es schon gibt (Inventar, Interaktion, Spieler-Controller). Neue Scripts hängen
  sich daran an und senden/empfangen Signale auf demselben Weg. Bestehende Laufzeit-Scripts nicht ändern.
- Ein kleines Script pro Mechanik, Felder per [SerializeField], vom cubegen-Import gesetzt (Import um diese
  Typen erweitern). Keine Animation-Clips, alles prozedural wie im restlichen Spiel.
- Vor dem Schreiben: Plan + Liste, was sich mit vorhandenen Scripts schon lösen lässt.

Mechaniken:
1. Item-Sockel (socket, chip_reader, fuse_box, battery_bank; terminal mit params.extra = "slot"):
   nimmt ein passendes Item aus dem Inventar an, setzt es auf das leere Teil "Slot" bzw. "Slot_<n>"
   (Position + Rotation übernehmen), schaltet den SignalIndicator ein und sendet ein Signal, wenn alle Slots
   belegt sind. Passend: socket params.kind (energy_cell | battery) -> item.kind gleichen Namens,
   chip_reader -> item.kind data_chip, fuse_box -> item.kind fuse, battery_bank -> battery,
   terminal (slot) -> keycard. fuse_box: Deckel (Rotatable an "Panel") muss offen sein.
2. Laser (laser_emitter, laser_mirror, laser_receiver): Strahl vom leeren Teil "Beam" in dessen
   Vorwärtsrichtung, Raycast, an Spiegeln reflektieren (Treffer auf das Glas des "Mirror"-Teils:
   Vector3.Reflect mit hit.normal), max. ~10 Reflexionen, LineRenderer mit dem Glow-Material des Emitters.
   Trifft der Strahl das Teil "Lens" eines Empfängers -> dessen SignalIndicator an + Signal; sonst aus.
   Spiegel drehen weiter über ihr Rotatable.
3. Druckplatte (pressure_plate): Trigger-Volumen über "Plate" (aus dessen bounds); Spieler oder
   Rigidbody darauf -> "Plate" sinkt 0,04 m (Unity -Y), SignalIndicator an, Signal; runter -> zurück.
4. Rohr-Puzzle (pipe_fitting): Controller für eine Gruppe von Fittings: gelöst, wenn jedes Rotatable auf
   seinem target steht. Dann Glow aller Fittings an (SignalIndicator-Logik oder Materialtausch auf
   M_GlowCyan) und Signal. Optional "Fluss": nur Fittings leuchten, die von einer Quelle aus verbunden
   sind (Anschlüsse aus "note", gedreht um die aktuelle Stellung).
5. Schwenken (camera "Rotor", service_robot "Head"): Hin- und Herschwenken um Unity up statt Dauer-Drehung,
   ±60° (Kamera) bzw. ±40° (Kopf), Tempo als eigenes Feld (Standard 20 °/s); den Rotator der Kamera
   (speed 0) dafür ersetzen. Kamera optional mit Sichtkegel:
   sieht sie den Spieler -> Glow-LED auf Dauerlicht, Signal (Alarm).
6. Leiter (ladder): Trigger-Volumen vor der Leiter (Front = Unity +Z), Spieler klettert hoch/runter;
   Höhe aus bounds. Nur wenn der Spieler-Controller sich dafür erweitern lässt - sonst vorschlagen.
7. Pads (pad): params.kind "jump" -> Spieler nach oben schleudern (Kraft als Feld, Standard so, dass er
   ~3 m hoch kommt); "teleport" -> Ziel-Pad als Feld (im Level verknüpft), Ring dreht schneller beim Auslösen.
8. Förderband (conveyor): Rigidbodies und Spieler auf dem Band bewegen sich entlang der lokalen X-Achse
   (Unity right), Richtung aus dem Vorzeichen des Rotator-speed, Tempo = Rollen-Umfang * Drehzahl.
   Nur aktiv, solange die Rotatoren laufen (z. B. Machine/Signal schaltet sie).
9. Lift: Door bewegt "Deck" schon - ergänzen: Ruf-Knopf oben/unten (keypad oder lever im Level) und den
   Spieler mitnehmen (Deck als bewegte Plattform, Spieler parenten oder Geschwindigkeit übertragen).
10. Leerlauf-Animation (drone, robot_arm): Drohne schwebt sanft auf und ab (±5 cm, ~0,5 Hz) und neigt sich
    leicht; Roboterarm bewegt Arm_Lower / Arm_Upper (Unity right) und Turret (Unity up) mit langsamen
    Sinuswellen um die Ruhepose, Gripper öffnet/schließt. Rein visuell, abschaltbar.

11. Knöpfe (button, intercom): Interaktion drückt "Button" bzw. "Button_<n>" kurz 0,015 m Richtung Wand
    (Unity -Z) und sendet ein Signal. Knopfreihe: Reihenfolge als Feld (Code-Rätsel), richtige Folge ->
    SignalIndicator an.
12. Zahnradwerk (gear_puzzle): Item-Sockel (Mechanik 1) für "Slot" mit spare_part kind "gear"
    (meta.missing_gear.radius ≈ spare_part params.size). Eingesetzt -> Rotatoren aller Gear_<n> an,
    SignalIndicator an, Signal. Ohne fehlendes Rad: startet per Signal (z. B. Kurbel / lever).
13. Laser-Teiler (laser_splitter): in Mechanik 2 einbauen - trifft der Strahl "Prism", gehen zwei neue
    Strahlen von "Beam_A" und "Beam_B" in deren Vorwärtsrichtung aus (Beam_B: Unity right des Prismas).
14. Steckfeld (cable_plug): Spieler nimmt "Plug" (ausblenden, gilt als gehaltenes Kabelende) und steckt es
    in eine Buchse "Slot_<n>": Stecker dort zeigen. Richtig = meta.target_slot (gleiche Farbe) ->
    SignalIndicator an, Signal; falsch -> kurz rot blinken.
15. Scanner (scanner): params.kind "card" -> braucht ein keycard-Item im Inventar, "hand"/"retina" ->
    Spieler steht davor und hält die Interaktion ~1,5 s (Scan-Glow pulsiert dabei schneller), danach
    SignalIndicator an + Signal.
16. Tresor (safe): Rad (Rotatable an "Wheel") auf der Code-Ziffer bzw. Keypad-Code richtig -> Tür-Rotatable
    auslösen; im "Slot" liegt ein Item (Feld: welches Prefab).
17. Werkzeuge (tool) als Schlüssel: kind "crowbar" hebelt "Grille" von vent_shaft und den Rost "Panel" von
    floor_grate auf (Teil fällt als Rigidbody heraus), "wrench" dreht Ventile ohne Rad, spare_part
    "valve_wheel" setzt ein fehlendes Ventilrad ein. clue-Items zeigen beim Aufheben einen Text (Feld).
18. Wachgeschütz (turret): wie Mechanik 5 schwenken (Turret ±60°), "Gun" zielt auf den Spieler, wenn er im
    Sichtkegel ist (Glow -> Blink, Signal / Schaden nach Spiel-Logik). spider_bot: Beine "Leg_<n>" im
    Wechsel leicht anheben (prozedurale Laufanimation), nur visuell.
19. Fallen (crusher, saw_blade, steam_vent, shock_plate): Schadenszone als Trigger (crusher: unter "Panel",
    nur während der Kopf fällt; saw_blade: um das Blatt; steam_vent: Kegel über "Steam"; shock_plate: über
    "Body"). Ein-/Ausschalten per Signal (z. B. Sicherung, Hebel), dabei SignalLight bzw. Rotator mit
    an/aus. crusher: Takt-Script, das die Door abwechselnd öffnet/schließt (Pause als Feld). steam_vent: das
    Absperrventil (Rotatable an "Wheel" auf target) stoppt Dampf und Schaden.
20. Schieberätsel (sliding_puzzle): Klick auf ein "Tile_<n>" neben der Lücke schiebt es um meta.pitch_m in
    die Lücke (Unity X / Y der Wandfläche, ~0,15 s). Startanordnung aus meta.layout (0 = Lücke). Gelöst =
    Tile_1..Tile_<n*n-1> zeilenweise von oben links, Lücke unten rechts -> SignalIndicator an, Signal.
21. Waage (balance_scale): Items auf "Slot_A" / "Slot_B" ablegen (wie Item-Sockel, Mechanik 1); Gewicht pro
    item.kind als Feld. Stellung = Vorzeichen der Differenz (-1 / 0 / +1) auf das Rotatable an "Beam";
    "Pan_A" / "Pan_B" gegen die Balkenneigung zurückdrehen, damit die Schalen waagrecht hängen. Gleich
    schwer -> Signal.
22. Frequenz-Regler (freq_dial): je weiter die Knöpfe vom target entfernt sind, desto unruhiger flackert der
    "Screen" (Material-Emission oder UV-Scroll); alle auf target -> ruhig, SignalIndicator an, Signal.
23. Taschenlampe (flashlight): aufgehoben -> Taste schaltet ein Spot-Light an der Kamera; "Glow" der
    Lampe wechselt dabei M_GlowCyan/M_GlowOrange <-> M_RobotDark. key: wie keycard als Schlüssel-Item
    (item.kind "key"), öffnet z. B. cage oder safe.
Am Ende: Liste der neuen Scripts, welche Typen sie nutzen, und welche Felder der Import jetzt setzt.
````

## cubegen 0.9: Vertrag, neue Typen und Integrationsbedarf

Abgeglichen mit `Docs/CUBEGEN_IMPORT.md` des Spiels (Stand 6. Oktober 2026). cubegen prüft jeden Sidecar
vor dem Export mit denselben Regeln (`cubegen/contract.py`): erlaubte Wurzel-, Teil- und Behaviour-Schlüssel,
Rollen und Felder je Script, Wertetypen, ein Bewegungs-Script pro Transform, normierte Quaternionen, konvexe
Mesh-Collider an bewegten Teilen, und gegen die FBX: Eltern, Mesh/Empty, lokale Position (1 cm),
Modell-Bounds (2,5 cm + 1 %), Teil-Bounds gegen das eigene Mesh.

**Schema:** unverändert, keine neuen Wurzelfelder. Familie, Anschlusspunkte, Herkunft der Parameter und die
Passungsprüfung stehen nur im `manifest.json`. Neue Varianten (Wandöffnung, Stegform, Treppenlauf …) stehen
wie alle Parameter in `params`, und nur, wenn sie gesetzt sind; ohne sie sind Modelle und Sidecars bitgleich
zu 0.8.0.

**Behoben** (bisher vom Import zu Recht abgelehnt): Pivots ab der dritten Ebene (`balance_scale`,
`robot_arm`, `turret`); `pipe` mit Ventil, dessen `Rotatable.glow` auf ein fehlendes `Glow` zeigte (26 von
300 Seeds); zerstörte `balance_scale`/`robot_arm`/`service_robot`/`turret` mit verwaisten Kindteilen.
Der reale Seed-42-Export aller 121 Bestandstypen ergibt jetzt 66 Gameplay-, 55 statische Modelle, 0
Ablehnungen und genau die 8 offenen Item-Zuordnungen.

**Item-IDs:** `--param keycard.item_id=<ItemData-ID>` (auch `item`, `key`, `tool`, `clue`, `spare_part`,
`flashlight`, `cable_reel`, im Rezept unter `params`, im Add-on als Textfeld) schreibt `fields.itemId`.
cubegen erfindet keine IDs; ohne Angabe bleibt die Zuordnung offen. Für mehrere Items desselben Typs mit
verschiedenen IDs: je Variante ein Kit-Eintrag mit eigenen `params`.

### Neue Typen: was der Import heute schon kann

| Typ | Teile | Behaviour (vorhanden) | Collider | Status |
|---|---|---|---|---|
| `turntable` | `Base` (statisch), `Deck` (Pivot Mitte), `Glow` | `Rotatable` target `Deck`, axis up, step 45/90 | Rahmen-Boxen, `Deck` Box bzw. konvexes Mesh | spielbar als Richtungsrätsel |
| `retractable_bridge` | `Housing`, `Deck`, `StatusLight_Front/Back`, `Rail` | `Door` panels `Deck`, `openOffset` (-Spannweite, 0,3, 0) | Podest, Taschenwände, Pfosten; `Deck` Box | ausfahrbar per Signal |
| `spike_trap` | `Base`, `Spikes` (Pivot unten), `StatusLight_*` | `Door` panels `Spikes`, `openOffset` (0, Höhe, 0) | Platte; `Spikes` Box | fährt aus, **ohne Schaden** |
| `cargo_container` | `Body`, `Door_Left/Right` (Pivot Scharnier), `Glow` | je Flügel ein `Rotatable` (axis up, step +90 / -90, target 1) | Boden, Wände, Dach, Rahmen; Flügel-Boxen | begehbar, Türen per Klick |
| `portal_frame` | `Frame`, `Surface` (kein Collider), `Glow` | `SignalLight` am Glow | Pfosten und Sturz einzeln | **nur vorbereitet** |
| `phase_platform` | `Base`, `Deck`, `Glow` | `SignalLight` am Glow | Anker; `Deck` Box | **nur vorbereitet** |
| `breakable_platform` | `Frame`, `Tile_<n>` (Pivot Plattenmitte) | – (statisch) | Rahmen; je Platte eine Box | **nur vorbereitet** |
| `fluid_basin` | `Basin`, `Fluid` (kein Collider) | – (statisch) | Wände und Boden einzeln, innen offen | **nur vorbereitet** |

Neue Varianten bestehender Typen (`wall` mit Tür-/Fenster-/Rohröffnung, `catwalk` L/T/Kreuz/Podest/Ende,
`stairs` mit Podest/Vierteldrehung/Wendepodest) sind statisch und bringen ihre `colliders` mit: Öffnungen
und Anschlüsse bleiben frei, Geländer sind eigene schmale Boxen.

### Benötigte Unity-Erweiterungen

1. **Portal** (`portal_frame`): Trigger-Volumen aus den Bounds von `Surface`, Verknüpfung zweier Portale
   (Paar-ID als Datenvertrag in `AssetMetadata`), Teleport mit Ausrichtung; Status über das vorhandene
   `SignalLight` am `Glow`.
2. **Phase** (`phase_platform`): Script, das `Deck` (Renderer und Collider) im Takt oder per Signal ein- und
   ausschaltet; `Glow` als Vorwarnung (z. B. Blink kurz vor dem Ausblenden).
3. **Bruch** (`breakable_platform`): Belastungs- oder Zeitlogik je `Tile_<n>`; die Platte wird zum
   Rigidbody bzw. deaktiviert, der Rahmen bleibt.
4. **Gefahr** (`spike_trap`, wie die bestehenden Fallen): Schadenszone als Trigger auf `Spikes`, nur
   ausgefahren aktiv; Takt- oder Signalsteuerung des vorhandenen `Door`.
5. **Flüssigkeit** (`fluid_basin`): Trigger-Volumen unter der `Fluid`-Fläche (Wasser: bremsen/schwimmen,
   Schlamm: bremsen, toxisch: Schaden); optional eigenes Wassermaterial statt `M_Glass`.
6. **Mitfahren**: Spieler und Kisten auf `Deck` von `retractable_bridge` (Translation) und `turntable`
   (Rotation) müssen der Bewegung folgen. `MovingPlatform` deckt Translation ab, sollte dann aber statt `Door`
   den Deck-Transform steuern; die Rotation der Drehscheibe ist zu prüfen.
7. **Werkbank-Freigabe**: Ports, Grundfläche und Platzierung der neuen Gameplay-Prefabs im bestehenden
   `AssetMetadata`-Vertrag authorieren; das Sidecar ersetzt diesen Vertrag nicht.
8. **Familien-Anschlüsse** (optional): Die Anschlusspunkte im Manifest (`models[].connectors`: Art,
   Position, Richtung, Breite/Höhe/Radius in Unity-Koordinaten) könnten später ein Einrasten im Editor
   steuern. Heute liest der Import das Manifest nicht; dafür ist keine Sidecar-Änderung nötig.
9. **LOD-Hüllen**: Statische Modelle mit `--lods` bekommen in Unity automatisch eine LODGroup. Zu prüfen
   ist, dass die Registry-Hülle mit einer LODGroup umgeht (Collider nur von LOD0, `colliders` zeigen auf
   `<Teil>_LOD0`).
10. **Klappen mit zwei Stellungen**: Die Deckel und Türen von `hatch`, `fuse_box`, `cage` und `safe` nutzen
    `Rotatable` mit `step` 100°/110° und `target` 1 (zu → offen). Das vorhandene Script dreht zyklisch weiter:
    Der zweite Klick dreht den Deckel durch den Körper. Nötig ist ein Zwei-Stellungs-Modus (offen ↔ zu) oder ein
    eigenes Klappen-Script; der Sidecar bleibt dafür unverändert.
11. **Luftschleuse** (`door` Stil `airlock`): Bis 0.9.0 stand das untere Blatt zuerst in `panels`. Mit dem
    Standard `secondOffset = -openOffset` fuhren beide Blätter durcheinander hindurch, die Öffnung blieb zu.
    Jetzt steht das obere Blatt (`Panel_B`) zuerst; mit 0.9.0 exportierte Luftschleusen neu erzeugen.

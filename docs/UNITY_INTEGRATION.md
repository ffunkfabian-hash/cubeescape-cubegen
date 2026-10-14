# Generierte Modelle in Unity verdrahten

`cubegen` schreibt neben jede FBX eine `<Name>.cubegen.json`. Sie enthält, was ein Prefab-Builder sonst als
Rezeptzeile in `ModularBlocks.cs` bräuchte: Teile, Pivots (Unity-Koordinaten), Script und Feldwerte.
Der Prompt unten lässt eine KI im **Unity-Projekt** einen Editor-Import dafür bauen – an die vorhandenen Builder
angeschlossen, ohne Laufzeit-Scripts zu ändern. Ein zweiter, optionaler Prompt
([Neue Interaktionen](#optional-neue-interaktionen)) ergänzt die Spiel-Mechanik, für die es noch kein Script gibt
(Item-Sockel, Laser, Druckplatte, Rohr-Puzzle, Kamera-Schwenk …).

## Aktueller Integrationsstand (8. Oktober 2026)

Cube Escape hat bereits einen validierten Editor-Importer und eine GUID-basierte Registry.
Die folgenden ursprünglichen Aufbau-Prompts sind historische Referenz; keinen zweiten
Importer, keine zweite Bausteinliste und keine neuen Laufzeitsysteme daraus bauen.
Der aktuelle Vertrag steht in `cubegen/contract.json`; die tatsächliche Unity-Freigabe
und Prüfbelege stehen im Spielprojekt in `Docs/CUBEGEN_IMPORT.md` und `Docs/ROADMAP.md`.

Phase 3 authoriert konkrete Modelle über `Assets/Editor/Cubegen/interactions.json`:
Klappen nutzen optionale Zwei-Stellungs-Drehung, der Lift den vorhandenen
`MovingPlatform`-Empfänger mit separatem Deck, Druckplatten einen ausdrücklich
zugewiesenen Sensor, Inventar-Sockel `ItemSlot`/`ItemSlotSignal`/`LogicGate`.
Inventar und physisch abgelegte Lasten bleiben verschiedene Verträge.
Ein Sidecar oder Modellprofil ist keine automatische Spielerlevel-Freigabe.

Kamera/Geschütz unterstützen positive und negative Schwenkgeschwindigkeit.
Bei ausdrücklich gesetztem Speed 0 bleiben aktuelle Generationen stehen; ohne
Speed-Vorgabe bleibt der historische implizite Sweep mit 30°/s erhalten. Generation 1
bewahrt die frühere Stillstand-/Sweep-Semantik. Der damalige Korrekturbericht
steht in `VERSION_0.10.4.md`; aktueller Arbeitsstand: [0.11.0](../VERSION_0.11.0.md).

## Historischer Aufbau-Prompt

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
- Collider: statische Modelle können eine Hülle erhalten; begehbare Modelle verwenden die geprüften Flächen der AssetRegistry. Gameplay-Modelle bekommen **keine** allgemeine Gesamthülle. Hat die JSON "colliders",
  ersetzen diese die Hülle - bei Prefabs mit Script UND bei statischen Modellen (prüfe, wie AssetRegistry die
  Hülle anlegt, und lies dort die JSON neben der FBX mit). Regeln:
  - "part": null = Wurzel, sonst das Teil (Transform per Name). Der Collider bewegt sich mit dem Teil (Luken-Deckel,
    Lift-Deck, Kraftfeld, Pressenkopf, Käfigtür); bewegte Teile brauchen wie bisher einen kinematischen Rigidbody.
  - "box": center / size in Unity-Koordinaten relativ zum Teil. rotation ist ein Quaternion (x, y, z, w). Bei
    (0, 0, 0, 1) den BoxCollider direkt auf das Teil legen (center / size setzen). Sonst ein Kind-Objekt
    "Collider_<n>" mit localPosition = center, localRotation = new Quaternion(x, y, z, w) und einem BoxCollider
    (center 0, size = size) - BoxCollider selbst kann nicht drehen (Rampe, Wendeltreppe, Treppengeländer).
  - "mesh": MeshCollider mit sharedMesh = Mesh des Teils, convex wie angegeben (platform, floating_island).
  - Ohne "colliders" bauen Gameplay-Adapter nur die ausdrücklich benannten Kollisionsrollen bzw. interaktiven Ziel-Bounds. Generation 3 ergänzt deshalb bei Gameplay-Modellen ohne eigene Shapes Collider pro Teil: feste Meshes nichtkonvex, bewegte Ziele und Kinder konvex. Pickups behalten ihren Interaktionstrigger. Ältere Generationen bleiben historisch; ein erfolgreicher Import beweist keine Begehbarkeit.
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
   (speed 0) dafür ersetzen. Mit cubegen-Parameter camera.sweep / turret.sweep kommt der Rotor schon um den
   halben Winkel vorgedreht und mit Rotator.arc = Winkel: dann reicht das vorhandene Rotator.arc.
   Kamera optional mit Sichtkegel:
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

## Gemeinsamer Vertrag (`cubegen_contract.json`)

Die Regeln des Imports stehen maschinenlesbar in `cubegen/contract.json`: erlaubte Wurzel- und Teil-Schlüssel,
Pflichtfelder, Pivots, Kategorien, Rollen und Feldtypen je Script, welche Rollen ein Teil bewegen, Regeln wie
„ein bis zwei Türblätter“ oder „Schritt 1–360°“, Collider-Schlüssel, Toleranzen (1 cm, 2,5 cm + 1 %) und
Dateigrenzen (4 MiB, 64 Ebenen, keine doppelten Schlüssel). `cubegen/contract.py` prüft jeden Export damit.

```bash
python3 -m cubegen contract --out ../CubeEscape/Assets/Editor/Cubegen/cubegen_contract.json
```

Liest der `CubegenImporter` diese Datei statt eigener Listen, laufen Generator und Import nicht mehr auseinander:
Eine neue Rolle oder ein neues Feld wird an einer Stelle eingetragen (`version` erhöhen), beide Seiten prüfen
danach gleich. Bis dahin ist die Datei die Referenz zum Abgleich mit `Docs/CUBEGEN_IMPORT.md`.

### Versionen des Vertrags (seit 0.22.0)

| Version | seit | Inhalt |
|---|---|---|
| 1 | 0.9 | Regeln oben; gebackene Karten standen nur in der Liste des Importers (`CubegenMaterials`) |
| 2 | 0.22.0 | neuer Abschnitt `baked_maps` mit `Emission`, dazu `history` |
| 3 | 0.24.0 | neutrale Karten (`textures.neutral`, `textures.weight_layout`, Abschnitt `neutral_maps`), Thema als Daten (Wurzelschlüssel `paint`, Abschnitt `paint_scheme`), eigene Materialnamen statt `M_Crystal` für Nicht-Kristalle (Abschnitt `materials`), Abschnitt `textures` mit `since`, `root.since` |

`baked_maps` (Version 2) beschreibt `textures.baked` im Sidecar:

| Schlüssel | Wert | Bedeutung |
|---|---|---|
| `keys` | `Albedo`, `Normal`, `MetallicSmoothness`, `Roughness`, `AO`, `Height`, `Emission` | erlaubte Karten |
| `required` | `Albedo`, `Normal`, `MetallicSmoothness` | Pflicht im Modus `baked` |
| `srgb` | `Albedo`, `Emission` | Farbkarten (sRGB), alle anderen linear |
| `since` | `{"Emission": 2}` | ab welcher Vertragsversion eine Karte im Sidecar stehen darf |
| `material_prefix` | `MTA_` | Material `MTA_<Modell>` |
| `emission_intensity` | `3.0` | `_EmissionColor` = Weiß × 3 (wie die Emission Strength in Blender) |
| `distinct_files` | `true` | jede Karte eine eigene Datei |

Beide Seiten brechen nichts, solange sie dieselbe Version sprechen. Für einen Import, der eine ältere Version liest
(Cube Escape liest seit 0.57 Version 2, Version 3 folgt in dessen Phase 3), gibt es:

```bash
python3 -m cubegen contract --version 2 --out <Datei>      # die Datei von 0.22/0.23, inhaltsgleich (1: von 0.21)
python3 -m cubegen generate … --paint crystal --contract 2  # Sidecars für einen Import von Version 2 (oder 1)
python3 -m cubegen check --export <Ordner> --contract 2     # Export gegen Version 2 prüfen
```

`--contract 2` lässt neutrale Karten und Thema im Sidecar weg (sie bleiben im Manifest: `models[].neutral_maps`,
`weight_layout`, `config.paint_scheme`) und schreibt für die neuen Materialnamen wieder `M_Crystal`
(`Asset.legacy_materials`: bitgleich zum Modell von 0.23, belegt mit den Golden-Daten). `contract_for(2)` ist die
Datei von 0.22/0.23 (Fixture `tests/fixtures/contract_v2.json`).

Mit `--contract 1` bleibt die Leuchtkarte nur im Manifest (`models[].baked.Emission`); ein Sidecar ohne Emission ist
auch für Version 2 gültig. `tools/unity_check.py` liest die Version aus Cube Escapes
`Assets/Resources/Cubegen/cubegen_contract.json` und schreibt die Prüfsätze passend. **Umstellung in Cube Escape**
(ROADMAP ToDo 26): `CubegenContract` liest Version 2 (Schlüssel `history`, `baked_maps`), `CubegenMaterials` nimmt
die Kartenliste aus `baked_maps` statt der festen Liste, setzt bei `Emission` `_EmissionMap`, `_EMISSION` und
`_EmissionColor` = Weiß × `emission_intensity`; danach `python3 -m cubegen contract --out
Assets/Resources/Cubegen/cubegen_contract.json`.

**Leuchtkarte** (`--paint`, ToDo 26): nur Themen mit Leuchtkanten (`edge_glow` > 0: Crystal, Dark, Space, Ice, Toxic,
Void, eigene Themen mit `edge_glow`) schreiben `MTP_<Modell>_<Thema>_Emission.png`; Industrial, Clean, Ruin, Organic
und Sand schreiben keine (bis 0.21 eine schwarze Karte – eine Textur weniger im Werkbank-Budget). Die Karte ist sRGB,
die Leuchtfarbe ist `edge_glow_color` des Themas (Manifest `paint.edge_glow_color`) mal Kantenmaske; im GLB steckt
sie als `emissiveTexture`.

### Neutrale Karten für den Umfärbe-Shader (Vertrag 3, seit 0.24.0)

Mit `--paint` schreibt jeder Lauf neben den fertigen Karten (`MTP_<Modell>_<Thema>_*.png`, Material `MTA_<Modell>`)
je Modell die gepackten neutralen Karten `MTN_<Modell>_<Karte>.png` in den Texturordner. Aus ihnen und dem Thema
rechnet `paint.compose` die fertigen Karten – der Shader (Cube Escape: Rezept PAINT) rechnet dasselbe nach. Alle
Karten sind **linear** (sRGB aus), 8 Bit, gleiche Auflösung wie der Atlas (`--texture-size`), UV0 des Modells.

| Karte | R | G | B | A |
|---|---|---|---|---|
| `W0` | Gewicht `weight_layout[0][0]` | Gewicht `[0][1]` | Gewicht `[0][2]` | **Rauschen** 0–1 |
| `W1` | Gewicht `weight_layout[1][0]` | `[1][1]` | `[1][2]` (ohne zweite Gruppe schwarz) | **Detail**: `0,35 + A × 1,45` |
| `W2` | Gewicht `weight_layout[2][0]` | `[2][1]` | `[2][2]` | reserviert (1) – nur bei drei Gruppen |
| `Fields` | Umgebungsverdeckung (AO) | Kante | oben (Weltnormale Z) | Höhe (0 am Fuß, 1 oben) |
| `Normal` | Tangentennormale (OpenGL, +Y) | | | |

- `weight_layout`: die Spielmaterialien des Modells (aus `paint_scheme.painted`, in dieser Reihenfolge) in Dreiergruppen;
  ein fehlendes `W<k>` oder ein freier Kanal wiegt 0. `W0`, `W1`, `Fields`, `Normal` sind Pflicht, `W2` genau bei
  drei Gruppen – fünf Texturen statt acht (bisher W0–W2, AO, Kante, oben, Höhe, Normal einzeln).
- **Rauschen und Detail sind Kanäle:** Bis 0.23 erzeugte `compose` das Rauschen zur Laufzeit aus einem numpy-Seed.
  Seit 0.24.0 setzt Cubegen die fertigen Karten **aus den gepackten 8-Bit-Werten** zusammen (`neutral.compose_packed`)
  – ein Shader, der die Karten liest, rechnet exakt das Referenzbild nach. Die fertigen Karten ändern sich dadurch
  gegenüber 0.23 um höchstens 5/255 (im Mittel 0,14/255, gemessen an Kiste, Säule, Modulwand in allen elf Themen).
- `paint.compose` bleibt die Referenzformel (Cube Escape `MATERIALS.md`, Entscheidung 2). Ein Gewicht wird mit
  `w / max(Σw, 1e-4)` normiert (8-Bit-Rundung), Detail multipliziert die Albedo, danach Schmutz, aufsteigender
  Schmutz, Staub, Moos, Kantenlicht, Abnutzung und Leuchtkanten in dieser Reihenfolge.
- Die Rohdaten des Backens (`Textures/Neutral/<Modell>_W<n>/AO/Edge/Up/Height/Diffuse/Normal.png`, Manifest
  `models[].neutral`) bleiben unverändert erhalten – für den Stiltest, nicht für Unity.

**Sidecar (Version 3):** `textures.neutral` und `textures.weight_layout` neben `baked`, dazu der Wurzelschlüssel
`paint`: der Name eines eingebauten Themas – oder ein eigenes Thema vollständig als Daten (`name` und alle
`paint_scheme.keys`, Farben sRGB `#rrggbb`, Mengen 0–1). Die eingebauten Themen liefert
`python3 -m cubegen catalog --paints` (`paint_schemes`, `paint_keys`) – Cube Escape spiegelt die Datei wie
`cubegen_contract.json`. Beispiel (`generate --seed 19 --pick crate:0 --paint dark`):

```json
{
  "model": "Crate_000",
  "textures": {
    "mode": "baked",
    "manifest": "Textures/CubeEscape_Textures.json",
    "baked": {
      "Albedo": "Textures/MTP_Crate_000_dark_Albedo.png",
      "Roughness": "Textures/MTP_Crate_000_dark_Roughness.png",
      "MetallicSmoothness": "Textures/MTP_Crate_000_dark_MetallicSmoothness.png",
      "Normal": "Textures/MTP_Crate_000_dark_Normal.png",
      "Emission": "Textures/MTP_Crate_000_dark_Emission.png"
    },
    "neutral": {
      "W0": "Textures/MTN_Crate_000_W0.png",
      "W1": "Textures/MTN_Crate_000_W1.png",
      "Fields": "Textures/MTN_Crate_000_Fields.png",
      "Normal": "Textures/MTN_Crate_000_Normal.png"
    },
    "weight_layout": [["M_RobotDark", "M_Metal", "M_Warning"]]
  },
  "paint": "dark"
}
```

Ein eigenes Thema (`--paint-file paints/custom_example.json`) steht als Objekt da:
`"paint": {"name": "rust_bucket", "label": "Rust Bucket", "colors": {…alle neun…}, "glow": "red", …}`.

Regeln (`check_sidecar`, Version 3): `neutral` nur im Modus `baked`, nur zusammen mit `weight_layout` und `paint`;
bekannte Karten, Pflichtkarten, `W2` genau bei drei Gruppen, jede Karte eine eigene Datei; `check --export` findet
fehlende Dateien. Ein Import von Version 2 lehnt `paint`, `textures.neutral` und `textures.weight_layout` ab.

**Vergleichsbilder** (Cube Escape `SurfaceRenderTests`): `python3 tools/paint_reference.py <Lauf>` setzt aus den
`MTN_`-Karten eines Laufs jedes eingebaute Thema (und das eigene des Laufs) ohne Blender zusammen –
`<Lauf>/paint_reference/<Thema>/MTP_<Modell>_<Thema>_Albedo/Roughness/MetallicSmoothness[/Emission].png` und
`reference.json` (Modelle, `weight_layout`, neutrale Karten, Themendaten, vorgeschlagene Toleranz: je Kanal höchstens
3/255, im Mittel 0,5/255). `--check` vergleicht das Thema des Laufs mit den von Blender gespeicherten Karten: sie sind
bitgleich. `tools/unity_check.py` legt die Referenz für jeden Prüfsatz mit Anstrich an und reicht sie als
`$CUBEGEN_PAINT_REFERENCE` an den Unity-Lauf.

### Eigene Materialnamen statt `M_Crystal` (Vertrag 3, seit 0.24.0)

`M_Crystal` ist nur noch echter Kristall (Fels, Kristallgruppe, Hängekristalle, Asteroid, Stalagmit, Schwebeinsel- und
Plattform-Unterseite, Reaktorkern, Kryo-Reif, Ersatzteil „crystal“, Modulwand – `materials.CRYSTAL_TYPES`, ein Test
hält es fest). Was bisher `M_Crystal` trug, ohne Kristall zu sein, hat einen eigenen Namen. Alle haben vorerst die
Werte von `M_Crystal` (gleiches Aussehen), bis Cube Escape sie gestaltet:

| Material | sRGB | Glätte | Metall | Emission | wofür (Typen) |
|---|---|---|---|---|---|
| `M_Liquid` | `#4ce6ff` | 0,9 | 0 | 2,5 | Flüssigkeit, Wasser, Schlamm (`water_level`, `puddle` slime, `lab_device`, `galley`) |
| `M_Hologram` | `#4ce6ff` | 0,9 | 0 | 2,5 | Hologramme und Energiefelder (`hologram`, `force_field`) |
| `M_Lamp` | `#4ce6ff` | 0,9 | 0 | 2,5 | Lampenflächen, Sterne (`floodlight` ohne `--glow`, `planet_window`) |
| `M_Leaf` | `#4ce6ff` | 0,9 | 0 | 2,5 | Alien-Blätter, Pilzflächen, Pilzhüte (`plant`, `hydroponic_bed`, `vines`, `fungus_carpet`, `mushroom`) |
| `M_Biolume` | `#4ce6ff` | 0,9 | 0 | 2,5 | leuchtende Organik: Knospen, Wurzeladern, Sporenpunkte (`vines`, `wall_roots`, `fungus_carpet`) |
| `M_Signal` | `#4ce6ff` | 0,9 | 0 | 2,5 | Sequenzfarbe der Tonfolge (`sequence_panel`, auch `onMaterial`) |
| `M_Accent` | `#4ce6ff` | 0,9 | 0 | 2,5 | Leuchtakzente von Bau-Kit-Teilen (`pad` Teleporterring, Planet in `planet_window`) |
| `M_Optic` | `#4ce6ff` | 0,9 | 0 | 2,5 | Linsen und Prismen (`laser_receiver`, `laser_splitter`, `spare_part` Linse, `test_lens_array`) |

Emission ist die Stärke wie bei den anderen `M_`-Materialien (`materials.MATERIALS`: Farbe × 2,5). Die Liste steht im
Vertrag (Abschnitt `materials`: `split` mit Verwendung, `like`, `legacy`) und je Lauf im Manifest (`materials`: je Name
`srgb`, `smoothness`, `metallic`, `emission`, `use`, `legacy`; `written: false`, wenn der Lauf für Version 2/1 wieder
`M_Crystal` schrieb). Wie die anderen Leucht-, Kristall- und Glasmaterialien behalten sie ihr eigenes Material beim
Backen, Anstreichen und in Paletten (Palettenmodus: die Zelle von `M_Crystal`, das Palettenbild bleibt gleich). Die
Kristallfarbe eines Themas (`paint.crystal_color`) gilt nur noch für `M_Crystal`. **Für Cube Escape:** die acht
Materialien in der `MaterialLibrary` anlegen (vorerst Kopien von `M_Crystal`), danach Vertrag 3 lesen. Alte Ausgabe
bleibt historisch: Exporte bis 0.23 und Läufe mit `--contract 2`/`1` tragen `M_Crystal`.

## Manifest für Cube Escape (`manifest.json`, Format 2 seit 0.22.0)

Der Import liest heute nur Sidecar, FBX/GLB und die Textur-Manifeste. Für den Modell-Browser der Werkbank
(ROADMAP ToDo 16, 25, 30, 31) steht im `manifest.json` jedes Laufs alles Weitere. `format` fehlt bis 0.21 (= 1);
Format 2 ergänzt nur Schlüssel, ein Leser von Format 1 läuft weiter. Koordinaten wie im Sidecar: Unity, Meter,
Pivot des Modells.

**Wurzel**

| Schlüssel | Inhalt |
|---|---|
| `format` | `2` |
| `config.contract` | Vertragsversion, für die die Sidecars geschrieben sind |
| `sets` | Variantensets (unten) |
| `joins` | welche Anschlussarten zusammenpassen (unten) |
| `dressings` | Anbauten je Typ und Thema (unten) |
| `paint` | `name`, `glow`, `crystal_color`, `edge_glow_color` des Anstrichs, sonst `null` |
| `materials` | (0.24.0) die von `M_Crystal` abgespaltenen Materialnamen mit Werten, `written` (siehe oben) |
| `models` | ein Eintrag je Modell (unten) |

**`sets[]`** (`--set`, ToDo 25/31) – ein Set sind Varianten eines Typs mit gleichem Umriss:

```json
{"name": "floor_tile_set", "type": "floor_tile", "members": ["FloorTile_000", "FloorTile_001", "FloorTile_002"],
 "pinned": {"depth": 0.1271, "size": 4.0}, "faces": ["x-", "x+", "y-", "y+", "z-"],
 "faces_unity": [{"face": "x-", "direction": [1.0, 0.0, 0.0], "distance_m": 2.0},
                 {"face": "y-", "direction": [0.0, 0.0, 1.0], "distance_m": 2.0},
                 {"face": "z-", "direction": [0.0, -1.0, 0.0], "distance_m": 0.1271}],
 "bounds": {"center": [0.0, 0.1878, 0.0], "size": [4.0, 0.6298, 4.0]},
 "outline_ok": true, "deviation_m": 0.0, "preview": "set_floor_tile.png"}
```

- `members`: Modellnamen in Variantenreihenfolge (Einträge in `models`, dort mit `set` = Setname).
- `pinned`: festgehaltene Parameter (Umriss und Formwahlen, `set_pins`).
- `faces`: geprüfte Anschlussseiten in Generator-Achsen (`x-` links, `y-` vorne, `z-` unten; Blender);
  `faces_unity`: dieselben Seiten in Unity – `direction` zeigt nach außen, `distance_m` ist der Abstand der Seite
  vom Pivot entlang `direction`. Zwei Mitglieder schließen an, wenn eine Seite mit `direction` d und eine mit −d
  aneinanderliegen; nur an diesen Seiten einrasten (ToDo 31). Seiten, die nicht genannt sind (bei Böden oben,
  bei Wänden vorne), dürfen Details tragen und schließen nicht an.
- `bounds`: Hüllquader des Umrisses (Variante 0, wie `bounds` im Sidecar).
- `outline_ok = false`: die Mitglieder weichen um mehr als 1 cm ab (`deviation_m`) – der Typ ist nicht set-fähig,
  im Browser kennzeichnen.
- `preview`: Reihenbild aller Mitglieder (nur mit Vorschauen, sonst `null`).

**`joins[]`** (ToDo 16) – alle Paare aus `families.JOINS`:

```json
{"a": "walk", "b": "walk_edge", "mode": "face", "fit_check": true}
```

`a`/`b` sind Anschlussarten (`models[].connectors[].kind`, in beliebiger Reihenfolge), `mode` `face` = Richtungen
entgegengesetzt (Steg an Steg), `align` = gleiche Richtung (Tür in Wandöffnung, Abschluss auf der Wand),
`fit_check` = `cubegen check --family` prüft die Maße dieser Fuge. Arten ohne Partner: `floor_walk` (Fuß einer
Treppe oder Rampe auf dem Boden), `window`, `pipe_up` (senkrechter Rohrarm).

**`models[].connectors[]`** – Anschlusspunkte jedes Modells:

```json
{"name": "deck_out", "kind": "walk", "width": 1.0, "position": [-2.0, 0.0, 0.0], "direction": [-1.0, 0.0, 0.0],
 "moves": {"part": "Deck", "offset": [-2.0, 0.3, 0.0]}}
```

`position`/`direction` am Pivot, Maße je Art (`width`, `height`, `thickness`, `radius`, `clear` = lichte Öffnung).
`moves` (neu in Format 2): der Anschluss sitzt auf einem bewegten Teil und gilt erst, wenn `part` um `offset`
verschoben ist (ausgefahrene Brücke).

**`dressings`** (ToDo 30) – Anbauten sind Geometrie, die ein Anstrich nicht liefern kann (nie gewürfelt):

```json
{"dressing": {"values": ["none", "ruin", "organic"], "default": "none",
              "types": ["catwalk", "floor_tile", "pillar", "test_wall_modules"],
              "paints": {"ruin": ["ruin"], "organic": ["organic"]}},
 "crystals": {"values": ["none", "some", "many"], "default": "none", "types": ["test_wall_modules"]}}
```

`paints` nennt das Thema, für das ein Anbau gemacht ist (Vorschlag für den Browser, keine Pflicht). Je Modell
`models[].dressing` mit den wirksamen Werten, z. B. `{"dressing": "ruin"}` oder
`{"crystals": "some", "dressing": "none"}`; Typen ohne Anbauten haben den Schlüssel nicht.

**Weitere Felder je Modell** (unverändert): `files`, `preview`, `icon`, `pivots`, `behaviours`, `stats`,
`renderers`, `asset_hash`, `meta` (mit `params`), `family`, `param_sources`, `build_key`; mit Anstrich `baked`
(Karten, mit `Emission` nur bei leuchtendem Thema), `baked_material`, `paint`, `weight_layout`, `neutral` (Rohdaten
des Backens) und seit 0.24.0 `neutral_maps` (die gepackten `MTN_`-Karten, `{"W0": "models/Textures/MTN_Crate_000_W0.png",
…}`, bei jeder Vertragsversion).

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

## Phase 3: Erweiterungen und Integrationsbedarf

**Schema:** unverändert. Alles Neue sind Teile, Behaviours und Felder, die der Vertrag schon kennt
(`cubegen/contract.json` ist gleich geblieben). Der Seed-Export aller 164 Typen ergibt 0 Ablehnungen.

**Generation 3 (Standard): Anker für Ton und Effekte.** Neue leere Teile `Audio_<Klang>` und `FX_<Effekt>`
(`Audio_Hum`, `Audio_Door`, `Audio_Servo`, `Audio_Beep`, `Audio_Alarm`, `Audio_Motor`, `Audio_Zap` …,
`FX_Steam`, `FX_Sparks`, `FX_Smoke`, `FX_Dust`, `FX_Muzzle`, `FX_Spores`, `FX_Portal` …; Tabelle:
`cubegen/models/anchors.py`). Sie sind Kinder des Teils, auf dem sie sitzen, und bewegen sich mit ihm. Import:
nach Namen eine `AudioSource` (Schleife, 3D) bzw. ein Partikelsystem anhängen; Effekte zeigen nach Unity-oben,
Front-Anker (`FX_Muzzle`) nach Unity-forward. `--generation 2` exportiert ohne Anker, bitgleich wie bisher.

**Bruchstücke** (`style.damage` = `fractured`): Generation 3 im 0.11.0
verwendet leere `Fragment_01` … als Compound-Parents. Die Meshes heißen
`Shard_<Fragment>_<Teil>` und tragen ihre eigenen Collider. Ein Rigidbody gehört an
den Fragment-Parent, nicht an jeden Shard. Konvexe Körper bleiben konvex; seltene
nichtkonvexe Shards behalten genaue feste Mesh-Kollision. Solche Quellen erhalten
keine dynamische Freigabe, bevor eine echte Zerlegung vorliegt. Generation 1/2
behalten historische zusammengesetzte Einzelhüllen, die Zwischenräume schließen
können. Neue/geänderte Quellen neu exportieren, keine alte Ausgabe als repariert melden.

Der erste gezielte Zerlegungsschritt gewinnt bereits getrennte geschlossene konvexe
Komponenten zusammengesetzter Kastenprofile zurück. U-/L-/T-/I-Profile und Gitter
behalten ihre Flächen und Materialrollen; alle Shapes eines bisherigen Fragments
teilen weiter denselben Rigidbody. Offene Schalen oder echt konkave zusammenhängende
Komponenten werden nicht mit einer Hülle ersetzt. `python3 -m tools.audit_fragment_profiles`
misst den aktuellen Umfang ohne Blender-/Renderläufe; weitere Familien benötigen
eigene Geometrie- und echte Unity-Physiknachweise.

Hohlrohre (`pipe_section`), einfache Bandringe (`ring`) und Torusformen (`torus`)
liefern zusätzlich genaue Wandsegment-Rezepte. In Generation-3-Fragmenten werden
deren geschlossene, konvexe Segmente am bisherigen Fragment-Parent ausgegeben.
Zentrale Öffnungen bleiben frei; Abschlussflächen werden ergänzt. Nach allen
Transformationen Konvexität, Kantenabschluss und Volumen prüfen; verformte/ungültige
Rezepte bleiben fest. `--baseline structural` am Auditwerkzeug vergleicht nur diesen
zweiten Schritt. Mehr Shapes erfordern weiterhin Objekt- und globale Physikbudgets;
ein erfolgreicher Export erteilt keine automatische Gameplay-Freigabe.

Einfache konkave Extrusionsquerschnitte (`prism`, höchstens 128 Originalpunkte)
werden deterministisch trianguliert; benachbarte Stücke werden nur bei konvexer
Vereinigung zusammengeführt. Aussparungen, Umfang, Fläche/Volumen und Materialrollen
bleiben erhalten. Selbstschneidende/-berührende, degenerierte oder zu große Profile
erhalten kein Rezept. Anschließende 3D-Prüfungen sichern verformte Modelle ab.
`python3 -m tools.audit_fragment_profiles --baseline round` vergleicht gezielt
diesen dritten Schritt. Echter Blender-Batch: `tests/blender/round_export.py
--family extrusion`; gleicher Export- und Physikvertrag wie bei Rohr-/Ringproben.
Im Master-Seed-42-Prüfsatz sinkt die verbleibende Zahl von 20 auf 15 Quellen;
fünf weitere Quellen sind vollständig konvex, ohne zusätzliche Rigidbodies.

Profilierte volle Drehkörper (`lathe`) liefern zusätzlich geschlossene Kegelstümpfe;
radiale Querschnitte mit Achsen-Enden erhalten konvexe Winkelstücke aus denselben
Originalpunkten. Flache Endpole bleiben Abschlussflächen ohne eigenes Nullvolumen-
Shape. Originalflächen/Materialrollen und Vertiefungen erhalten; bereits konvexe
Körper bleiben einzelne Shapes. Profil-/Seitenzahl begrenzt, ungültige/offene oder
verformte Rezepte behalten genaue feste Kollision. Nach allen Transformationen
prüft der Fragmentvertrag außerdem plane Rezeptflächen.
`--baseline extrusion` am Auditwerkzeug vergleicht den Drehprofil-Schritt;
`tests/blender/round_export.py --family lathe` exportiert echte gezielte Proben.
Im Master-Seed-42-Prüfsatz bleiben zwölf statt 15 Quellen; die drei zusätzlichen
konvexen Quellen sind Antenne, Kristallsockel und Transformator. Körperzahl gleich,
mehr Shapes erfordern weiterhin die bestehenden Budgets. Eine Schüsselvertiefung
ist kein Durchgang: ihre freie Kavität und der feste Boden werden getrennt geprüft.

Verformte achtpunktige Kästen erhalten eine begrenzte Partition über zwölf
Außendreiecke und einen nachgewiesenen inneren Punkt. Nur konvexe Nachbar-
vereinigungen werden zusammengeführt. Render- und Kollisionsflächen verwenden
dieselben expliziten Dreiecke; eine gemittelte Vierecknormale reicht bei nicht
planen Flächen nicht aus. Invalides, invertiertes oder nicht geschlossenes Netz
bleibt ohne dynamische Freigabe. Bereits konvex triangulierte Kästen bleiben ein
Shape; plane konvexe Kästen bleiben unverändert. Historische Generationen erhalten.
`--baseline lathe` vergleicht diese Nacharbeit; `--family box` am bestehenden
Blender-Prüfexport exportiert Standardquellen, isolierte Proben und den korrigierten
breiten kurzen Säulenstumpf. Im Master-Seed-42-Prüfsatz bleiben neun statt zwölf
Quellen. Die separate Stumpfhöhen-Korrektur in `fallen_pillar` gilt für aktuelle
Modelle in allen Zuständen; alte fehlerhafte Exporte müssen neu erzeugt werden.

`"static": true` beschreibt nur fehlende Generator-Behaviours. Fragment-Prefabs
niemals automatisch für Static Batching freigeben. Unity verwendet seinen vorhandenen
Bruch-/Schaden-/Signal-/Reset-Lebenszyklus, baut Körper einmalig und begrenzt aktive
Körper, Shapes und Lebensdauer. Der Draw-Call-Bericht zählt Fragment-Meshes auch im
Paletten-Modus einzeln. Unity-Abnahme und geprüfte Modellprofile stehen im aktuellen
`Docs/CUBEGEN_IMPORT.md` von Cube Escape. Alle unmittelbaren Generatorbefunde für
Phase 5 und kommende Aufträge: [VERSION_0.11.0.md](../VERSION_0.11.0.md).

Audio-/FX-Anker werden bei verfügbaren Unity-Mechaniken an deren echten Zustand
gebunden. Dampf, Strom und bewegte Teile dürfen ohne Aktivität weder Loop noch
Partikelausstoß behalten; Reset/Disable entfernt Restpartikel. Unbekannte Anker
bleiben vorbereitet, bis die betreffende Mechanik freigegeben wird.

**Paletten-Modus** (`--textures palette`): Die Teile nennen `MP_Palette` als Material (Glas, Status- und
Glow-Teile behalten `M_…`). Einmal ein Material `MP_Palette` anlegen: Albedo `MP_Palette_Albedo.png` (sRGB),
Metallic `MP_Palette_MetallicSmoothness.png` (R = Metallic, A = Smoothness, linear), Emission
`MP_Palette_Emission.png` × `emission` aus `CubeEscape_Palette.json`; alle drei mit Filter Mode **Point** und ohne
Mipmaps (sonst laufen die Farbzellen ineinander). Seit 0.10.2 enthält der Sidecar
`textures: {"mode": "palette", "manifest": "Textures/CubeEscape_Palette.json"}`; Farbpaletten
verweisen entsprechend auf `CubeEscape_Palette_<Name>.json`. Der Unity-Importer validiert
das Manifest und erzeugt das URP-Material selbst, getrennt nach Manifest-GUID.
Farbpaletten (`--palette rust` …) heißen `MP_Palette_<Name>` mit eigenen Bildern `MP_Palette_<Name>_Albedo.png` …
und `CubeEscape_Palette_<Name>.json`; die Zellen und UVs sind dieselben. Pro Palette ein Material wie oben anlegen.
Ein Raum wechselt die Stimmung, indem man das Material tauscht (oder mit einer anderen Palette exportiert).

**Schwenken** (`camera.sweep`, `turret.sweep`): `Rotator` mit `arc` = Winkel. cubegen baut den Kopf bzw. das
Geschütz um −arc/2 (Unity-Gier) vorgedreht, damit ein Schwenk von 0 bis `arc` in Richtung `speed` symmetrisch
±arc/2 um die Blickrichtung pendelt. Bitte prüfen, dass `Rotator.arc` so arbeitet (sonst: Vorzeichen in
`cubegen/models/common.py`, `sweep_rotator`). Die Kamera-LED (`Glow`) ist dann Kind von `Rotor`.

**Text:** `sign.text`, `door.label` (eigenes statisches Teil `Label` über der Tür), `countdown.text`,
`floor_plan.title` sind Geometrie; nichts zu tun. Der Countdown zeigt seine Startzeit (`meta.time`,
`meta.seconds_total`); für eine laufende Uhr die Ziffern (`Glow`) durch eine TextMesh-Anzeige ersetzen.

### Neue Typen: was der Import heute schon kann

| Typ | Teile | Behaviour (vorhanden) | Status |
|---|---|---|---|
| `sequence_panel` | `Button_<n>`, `Light_<n>` (Kind der Taste), `Glow` | `SignalLight` Blink; unabhängige `SignalIndicator`-Rezepte in `meta.deferred_behaviours` im Manifest | Statusleuchte importierbar; Tasten-Anzeiger und Folge brauchen einen eigenen Adapter (`meta.sequence`) |
| `water_level` | `Fluid_<n>` (Pivot unten), `Wheel_<n>`, `Glow` | je Rad `Rotatable` (forward, 90°, Ziel = Zielstand × 4), `SignalLight` | Räder drehbar; `Fluid_<n>` je Schritt um ¼ der Säule (`meta.column_m`) anheben fehlt |
| `laser_filter` | `Filter` (Pivot auf der Achse), `Glow` | `Rotatable` (up, 90°, Ziel 1) | drehbar; Laserfarbe (`meta.colour`) übernehmen fehlt |
| `symbol_plate` | `Plate_<n>` (Pivot Mitte), `Glow` | je Platte `Rotatable` (forward, 90°, Ziel = aufrecht) | spielbar, wenn alle Ziele erreicht = gelöst |
| `crane` | Drehkran: `Jib` mit Kind `Glow` (Magnet); Portalkran: `Trolley` mit `Glow` | `Rotatable` (up, 45°) bzw. `SignalLight` | Drehen spielbar; Magnet (Aufnehmen) und Laufkatze fehlen |
| `countdown` | `Body`, `Glow` (Ziffern) | `SignalLight` Blink | statische Startzeit |
| `push_block` | `Body`, optional `Glow` | – (statisch), eine Box als Collider | Schieben (Rigidbody, nur horizontal) und `PressurePlate` fehlen |
| `escape_pod` | `Panel` (Luke, Pivot am Scharnier), `Glow` | `Rotatable` (up, ±100°, Ziel 1) | Luke wie die Klappen (Zwei-Stellungs-Modus, ToDo 4) |
| `floodlight` | `Glow` | `SignalLight` mit `lightPosition`, `range`, `intensity` | spielbar |
| `light_strip`, `emergency_light`, `floor_plan`, `solar_panel`, `cocoon` | `Glow` (+ `Rotor` bei der Rundumleuchte) | `SignalLight` | spielbar |
| `lab_device` (Zentrifuge) | `Rotor` | `Rotator` (up) | spielbar |
| `patrol_drone` | `Rotor_1/2`, `Head` mit Kind `Glow` | `Rotator` je Propeller (gegenläufig) und Scanner, `SignalLight` | Flug-/Patrouillenlogik fehlt |
| `vent_crawler`, `robot_dog`, `mech` | `Leg_<n>` (Pivot Hüfte), `Head`, `Torso`, `Arm_L/R` | `SignalLight` (+ `Rotator` Torso) | Gangarten fehlen |

Statisch mit eigenen Collidern: `ramp` (Schräge + ebenes Ende), `archway` (Pfosten und Sturz, Durchgang frei),
`ceiling_module` (Platte), `wall_cap` mit Geländer, `collapsed_catwalk` (schräges Deck), `push_block`. Alle anderen
neuen Typen sind statische Deko mit Hülle.


## Kollisionskorrektur · 0.10.5

Qualität und Anschlusschecks verwenden jetzt standardmäßig den tatsächlichen Gameplay-Import.
Eine fehlende Kollisionsfläche ist ein Fehler. Eine explizite historische Layoutschätzung
(`collision_boxes(..., gameplay_import=False)`) ist kein Unity-Nachweis. Feste
nichtkonvexe Meshes werden als Vereinigung ihrer geschlossenen Teile geprüft;
eine Gesamtbox darf keine freie Öffnung als belegt melden. Konvexe Meshes werden
in Python konservativ begrenzt; echte FBX-/Unity-Physikprüfungen bleiben erforderlich.

Cube Escape Integrationsphase 4 authoriert 13 konkrete Modellprofile an den vorhandenen
Gefahren-/Plattform-/Fluid-/Portal-Systemen. Diese Freigabe gilt nur in Cube Escape,
nicht automatisch für jeden Export desselben Modelltyps. Korrekturen, Regressionen
und aktueller Prüfstatus stehen in `../VERSION_0.10.5.md`.


Statische und zerstörte Modelle der Generation 3 erhalten ohne eigenes Shape-Rezept
nun genaue nichtkonvexe Mesh-Collider pro Teil. Der frühere Gesamthüllen-Rückfall ist
für neue Exporte damit nicht erforderlich. Vorhandene Exporte werden nicht rückwirkend
repariert; Generation 1/2 bleiben historisch. Kollisionspflicht und Abnahmekriterien
für künftige Agenten stehen in `../AGENTS.md`, Befunde in `../VERSION_0.10.5.md`.


### Kameraneigung und zerstörte Exportflächen · 0.10.5

Generation-3-Kastenkameras schauen nach der Vorzeichenkorrektur 15–30° nach unten
(Blender-Vorderseite −Y, positive X-Neigung). Dome-Kameras und historische Generationen
bleiben erhalten. Bestehende Vorschauen/Exporte erneut erzeugen und reimportieren.
Zerstörte Generation-3-Meshes werden beim Blender-Export ausdrücklich trianguliert,
damit Unity nichtplanare Bruchflächen samt Materialrolle nicht verwirft. Regressionen
prüfen Blickrichtung, echten FBX und Frakturmaterial im GLB. Prüfbericht: `VERSION_0.10.5.md`.


## Compound-Bruch und radiale Partition · 0.11.0

Generation 3 zerlegt Strukturprofile, Hohlrohr-/Ringwände, konkave Extrusionen,
profilierte Drehkörper, verformte Kästen und nachweisbar sternförmige radiale Netze
in passende konvexe Shards. Ein Fragment-Parent erhält mehrere Collider und einen
Rigidbody; Öffnungen werden nicht durch eine gemeinsame Hülle verschlossen.
Die radiale Partition übernimmt die Außen-Dreiecke exakt und prüft einen strikten
inneren Punkt, geschlossene orientierte Topologie, Windung und Volumenerhalt.
Sie ist auf 64 Punkte/128 Dreiecke und eine begrenzte Punktsuche beschränkt.
Nicht plane Flächen verwenden gemeinsame explizite Render-/Collider-Dreiecke.
Offene, invertierte oder nicht beweisbar partitionierbare Geometrie bleibt fest.

175 Typen, Master-Seed 42, Index 0: kumulativ 34 → 0 Quellen mit nichtkonvexen
Shapes; letzte radiale Nacharbeit 9 → 0 bei 166 unveränderten Digests. Weitere
36 Seed-Fälle konvex, 227 Generator-Tests und 14 echte FBX grün. Zusätzliche Shapes
sind kostenpflichtig; keine Laufzeitzerlegung, keine weiteren Rigidbodies und keine
automatische Gameplay-/Spielerlevel-Freigabe. Import-/Physikbudgets bleiben erhalten.
Generation 1/2 und bestehende Exporte bleiben historisch; für Korrekturen neu
exportieren. Das vorhandene Blender-Add-on ist lokal auf 0.11.0 aktualisiert.
Vollständige Nachweise, Modellkorrekturen und Grenzen: [Versionsbericht](../VERSION_0.11.0.md).


### Sichtbare Abnahme in Cube Escape

Die Daten-Testanlage Z-1 kombiniert zwölf konkrete Bruchprofile: Kiste/Käfig/Rohr
und die neun radialen Quellen, Master-Seed 42/Index 0. Links BRUCH, rechts RESET
über die vorhandenen benannten Signalports; E/F bedient, V wechselt die Sicht.
Alle zwölf Stationen sind in beiden Ansichten je zweimal gespielt, einschließlich
Reset nach zeitgesteuertem Cleanup. Zwölf Bruch- und 13 Phase-4-Profile sind mit
0.11.0 neu exportiert und als echte FBX geprüft/importiert. Die konkrete Anlage
ersetzt keine allgemeine Freigabe anderer Parameterformen. Zugang im Spiel:
OPTIONEN > ENTWICKLUNG > DEV-MENÜ, dann ENTWICKLERWERKZEUGE > Bruch-Testanlage Z-1.

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
- Rotator dreht endlos. Für antenna/radar und Lüfter ist das richtig; bei camera und service_robot.Head
  (Kopf) würde ein Dauer-Dreh durch die Wand schwenken - solange es kein Schwenk-Script gibt, dort den
  Rotator deaktiviert lassen (speed 0) und im Log darauf hinweisen.
- Collider: statische Modelle bekommen über AssetRegistry eine BoxCollider-Hülle. Für begehbare Typen
  (stairs, catwalk, floor_tile, platform, floating_island) ist das falsch (Treppe als Block, Steg mit
  Geländer-Hülle): prüfe, wie AssetRegistry das macht, und schlage MeshCollider bzw. Box-Collider aus den
  "bounds" der einzelnen Teile vor (Deck ohne Rail). Wand- und Deckenteile (pivot "wall") brauchen nur
  Collider, wenn man sie berühren kann.

Optional erzeugt cubegen Texturen (sonst bleiben alle Materialien die bekannten M_*-Materialien):
- "tiled": Materialien MT_<Name> (z. B. MT_Metal), beschrieben in <Texturordner>/CubeEscape_Textures.json:
  {"materials": [{"name": "MT_Metal", "base": "M_Metal", "maps": {"Albedo": "MT_Metal_Albedo.png",
  "Normal": "MT_Metal_Normal.png", "MetallicSmoothness": "MT_Metal_MetallicSmoothness.png", ...},
  "metallic": 0.6, "smoothness": 0.55, "tile_m": 1.0}]}  (UV0 = Box-Projektion in Metern, Tiling 1/1)
- "baked": pro Asset ein Material MTA_<Model>; die Dateien stehen in der <Name>.cubegen.json unter
  "textures": {"mode": "baked", "baked": {"Albedo": ..., "Normal": ..., "MetallicSmoothness": ...}}
Glow-/Status-Materialien (M_Glow*, M_Crystal, M_Glass) sind nie texturiert und bleiben M_*.
Modelle mit "static": true (auch zerstörte Varianten und die Ruinen-Typen) haben keine Scripts.

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
   und werden von AssetRegistry registriert) - ihre MT_/MTA_-Materialien aus Schritt 5 aber trotzdem.
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
   ±60° (Kamera) bzw. ±40° (Kopf), Tempo aus dem Rotator-Feld speed. Kamera optional mit Sichtkegel:
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

Am Ende: Liste der neuen Scripts, welche Typen sie nutzen, und welche Felder der Import jetzt setzt.
````

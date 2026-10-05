# Generierte Modelle in Unity verdrahten

`cubegen` schreibt neben jede FBX eine `<Name>.cubegen.json`. Sie enthält, was ein Prefab-Builder sonst als
Rezeptzeile in `ModularBlocks.cs` bräuchte: Teile, Pivots (Unity-Koordinaten), Script und Feldwerte.
Der Prompt unten lässt eine KI im **Unity-Projekt** einen Editor-Import dafür bauen – an die vorhandenen Builder
angeschlossen, ohne Laufzeit-Scripts zu ändern.

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
              "empty": false, "materials": ["M_Metal", "M_RobotDark"]} ],
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
- SignalLight     → glow, [rotor]                                      → mode ("Steady"|"Pulse"|"Rotate")
- SignalIndicator → renderers[]                                        → offMaterial, onMaterial (Materialnamen)
- ItemPickup      → model[]                                            → spin (°/s)
Achsnamen meinen Vector3.right/up/forward im lokalen Raum. Materialnamen sind die M_*-Materialien der
MaterialLibrary.

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
3. Modelle mit "static": true nicht anfassen (die gehören nach Art/Models/Library/<Kategorie> und werden
   von AssetRegistry registriert).
4. Keine Änderungen an Laufzeit-Scripts. Fehlende Teile: Warnung ins Log, Modell überspringen.
5. Wiederholbar: erneuter Import überschreibt die generierten Prefabs (gleicher Name), nichts anderes.
6. Am Ende eine Zusammenfassung im Log: gebaut / übersprungen / Warnungen.
Zeige mir vor der Umsetzung den Plan und die Feld-Abbildung aus Schritt 1.
````

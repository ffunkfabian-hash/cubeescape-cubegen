# Changelog

## 0.9.0 – 2026-10-06

### Modellfamilien und Bau-Kits

* Eine Familie ist ein Rezept mit `"family"` und verbindlichen Maßen `"dims"`: Wandhöhe und -stärke,
  Modullänge, Tür-Stil und -Öffnung, Fenster, Laufstegbreite, Geländer- und Ebenenhöhe, Plattformgröße,
  Rohrradius und -achshöhe. `cubegen/families.py` bildet jedes Maß zentral auf die Parameter aller Typen ab,
  die ihm folgen. Typen mit fest eingebautem Maß werden abgelehnt, statt still nicht zu passen.
* Mitgeliefert: `station`, `foundry`, `lab` (`cubegen/family_data/`), jeweils mit Kit aus 28–29 Teilen.
* `--family NAME|DATEI` erzeugt das Kit oder mit `--types`/`--count` Varianten in der Familie. Rezepte mit
  `"family": "<Name>"` bauen darauf auf, ihre Werte sind dokumentierte Abweichungen. `--match
  <Name>.cubegen.json` erzeugt passende Ergänzungen zu einem vorhandenen Modell, das selbst mitgeprüft wird.
* Kit-Einträge dürfen eigene `params` haben (`{"type": "wall", "pick": [1], "params": {"opening": "door"}}`).
  Namen und Seeds bleiben `<Typ>_<Index>`, neue Teile ändern keine bestehenden.
* Passungsprüfung (`check --family`, Manifest `family.fit`): Breiten, Höhen, Ausrichtung, obere Ebene,
  begehbarer Boden über jeder Fuge (auch an Rampen), freier Durchgang, Tür/Portal in der Wandöffnung, Rohre
  durch Durchführungen, gemeinsamer Look. 0 von über 15 000 geprüften Fugen fehlerhaft (3 Familien, 3 Seeds,
  je 4 Varianten); absichtliche Abweichungen werden erkannt.
* Manifest: `family` (Name, Datei, Maße, Abweichungen, Passung), pro Modell `param_sources` und
  `connectors` (Unity-Koordinaten). Der Sidecar bekommt keine neuen Felder.
* `families` listet Familien und Maße. Add-on: Panel „Familie & Kit“ mit Kit bauen und Kit exportieren.

### Neue Typen (jetzt 129)

* `portal_frame`, `phase_platform`, `retractable_bridge`, `turntable`, `breakable_platform`, `spike_trap`,
  `fluid_basin`, `cargo_container`: bewegte und schaltbare Teile getrennt mit Pivot, explizite Collider,
  Öffnungen und Innenräume frei. Vorhandene Scripts nur, wo sie die Funktion abbilden (`Rotatable` für Drehscheibe
  und Containertüren, `Door` für Brücke und Stacheln, `SignalLight` für Portal- und Phasen-Glow); was in
  Unity noch fehlt, steht in `docs/UNITY_INTEGRATION.md`.

### Neue Varianten vorhandener Typen

* `wall`: `opening` `door`/`window`/`pipe` (Ausschnitt mit Rahmen, eigene Collider, Durchgang frei),
  `height`, `thickness`. `catwalk.shape`: L, T, Kreuz, Podest, Endstück; `rail_height`. `stairs.layout`:
  Zwischenpodest, Vierteldrehung, gegenläufig mit Wendepodest.
* Ohne diese Parameter sind alle Modelle bitgleich zu 0.8.0 (Fingerabdrücke). Der reale FBX-Export aller 121
  Bestandstypen × 2 Varianten wurde mit 0.8.0 verglichen: keine Änderung an FBX oder Sidecar.

### Unity-Vertrag

* `cubegen/contract.py` prüft jeden Sidecar mit den Regeln des Spiel-Imports (`Docs/CUBEGEN_IMPORT.md`) und
  gegen die FBX: Pivots auf 1 cm, Bounds, Rollen, Felder, Collider. Der Audit aus dem Spiel (Seed 42, alle
  Typen) ergibt 0 Ablehnungen und genau 8 offene Item-Zuordnungen.
* Neu: `item_id` für die 8 `ItemPickup`-Typen schreibt `fields.itemId`, nur wenn angegeben.
* Behoben: `--lods` schrieb das unbekannte Wurzelfeld `lods` und Teilenamen ohne `_LOD`-Endung (der Import hätte
  abgelehnt); jetzt stehen die Teile so im Sidecar wie in der FBX.
* Behoben: `pipe` mit Ventil konnte auf ein fehlendes `Glow` verweisen (26 von 300 Seeds); zerstörte
  `balance_scale`/`robot_arm`/`service_robot`/`turret` hatten verwaiste Kindteile (Blender-Export schlug fehl).

## 0.8.0 – 2026-10-06

### Behoben: Pivots von Teilen ab der dritten Ebene in der FBX

* Teile, deren Eltern-Teil selbst ein Eltern-Teil hat, hatten in der FBX eine falsche lokale Position und eine
  Drehung von 90° um X. Ursache ist Blenders FBX-Export mit `bake_space_transform`: Er rechnet die
  Achsen-Umrechnung ab der zweiten Ebene doppelt. Betroffen waren genau die drei Typen mit solchen Teilen:
  `balance_scale` (`Slot_A`, `Slot_B`), `robot_arm` (`Arm_Upper`, `Gripper`) und `turret` (`Glow`). Unity hat diese
  Modelle zu Recht abgelehnt. Die `.cubegen.json` war richtig, die FBX falsch.
* Der Export berechnet diese Matrizen jetzt selbst. Alle anderen Objekte behalten den Wert des Exporters, deren
  FBX ändern sich nicht.
* Neu: Nach jedem FBX-Export liest cubegen die Datei zurück (`cubegen/fbxread.py`, reines Python) und vergleicht
  Eltern, lokale Pivots, Rotation, Skalierung und Vertices mit dem Modell. Bei einer Abweichung bricht der Export
  ab, statt eine Datei zu schreiben, die nicht zur `.cubegen.json` passt.
* **Neu exportieren**: Wer `balance_scale`, `robot_arm` oder `turret` mit 0.7.0 exportiert hat, sollte sie neu
  erzeugen (gleiche Seeds, gleiche Namen).

### Gleicher Seed = gleiches Modell, garantiert

* `tests/golden.json`: Fingerabdrücke aller 121 Typen (9 Seed-/Stil-Fälle). Der Test schlägt fehl, sobald sich ein
  Modell ändert. Absichtlich geändert: `python3 tests/golden_cases.py --update`.
* Python 3.12 rechnet `sum()` von Kommazahlen genauer als 3.11. Dadurch hatten manche Flächen mit Python 3.12+
  eine andere Startecke als in Blender (3.11): gleiche Form, aber andere Dateien. Jetzt bauen Python 3.9 bis 3.13
  bitgenau die Modelle von Blender bzw. 0.7.0.
* `StableRandom`: Pythons Zufallsfunktionen außer `random()` dürfen sich zwischen Versionen ändern. cubegen nutzt
  jetzt eingefrorene Kopien, gleiche Ergebnisse wie bisher.
* `a.sub("name")`: eigener Zufallsstrom für neue Details in einem Builder, damit sie bestehende Seeds nicht
  verschieben.
* CI testet mit Python 3.9, 3.11 und 3.13.

### Neu

* `--unique` (Rezept `"unique"`, Add-on „Nur unterschiedliche“): überspringt Varianten, die wie eine frühere
  aussehen. Bei Seed 42 waren z. B. nur 7 der ersten 12 `laser_mirror` verschieden.
* `--theme TEXT` (Rezept `style.theme`, Add-on „Thema“): Raum-Thema, würfelt Glow-Farbe, Material, Abnutzung und
  Warnfarbe einmal für alle Modelle. Einzeln festgelegte Werte gehen vor.
* `--lods` (Rezept `"lods"`, Add-on): statische Modelle bekommen eine Sparstufe in derselben FBX
  (`<Teil>_LOD0` / `<Teil>_LOD1`, Unity baut die LODGroup beim Import); im Median 30 % weniger Dreiecke.
* Inkrementell: Ein erneuter Lauf in denselben Ausgabeordner baut nur geänderte Modelle neu; Blender startet gar
  nicht, wenn sich nichts geändert hat. `--force` baut alles neu.
* `--jobs N` (Add-on „Parallel“): N Blender-Prozesse gleichzeitig.
* `python -m cubegen check`: Qualitätsbericht mit Dreiecken gegen Budget, Draw Calls, flackernden Flächen
  (Z-Fighting) und Anzahl unterschiedlicher Varianten. Alle Typen liegen im Budget. 50 Typen haben flackernde
  Flächen, z. B. bündig aufliegende Warnstreifen und Leuchtringe. Sie zu beheben würde bestehende Seeds ändern; sie
  stehen in `tests/quality_baseline.json`, und der Test verhindert, dass es schlimmer wird.
* Rezepte werden geprüft: Tippfehler geben einen Fehler mit Vorschlag (`unknown key 'stlye' (did you mean
  'style'?)`) statt still ignoriert zu werden. `models` nimmt auch Varianten-Listen (`"door": [0, 7]`), Schlüssel
  mit `_` sind Kommentare.

### Kompatibilität

* Gleiche Seeds liefern dieselben Modelle wie 0.7.0. Ausnahme sind die FBX der drei oben genannten Typen, die
  jetzt korrekt sind.
* `<Name>.cubegen.json`: `style` enthält jetzt den aufgelösten Stil (mit Thema und `wear`), neu ist optional
  `lods`. `manifest.json`: neu `build_key` pro Modell.
* Mit `--lods` heißen die Objekte statischer Modelle in der FBX `<Teil>_LOD0` / `_LOD1`. Ohne `--lods` ändert
  sich nichts.
* `ItemPickup` schreibt weiterhin nur `spin`. Eine Spiel-ID (`itemId`) für die 8 Item-Typen kennt nur das
  Unity-Projekt; die Zuordnung bleibt dort.

## 0.7.0 – 2026-10-06

### Neu: Collider

* `<Name>.cubegen.json` enthält bei begehbaren und bewegten Typen `"colliders"`: Boxen (Unity-Koordinaten,
  Quaternion-Rotation) oder konvexe Mesh-Collider, optional an einem Teil, mit dem sie sich bewegen.
* Mit Collidern: `stairs` (Stufen bzw. Rampe + Geländer), `catwalk` (nur Deck, Geländer, Stützen), `platform`,
  `floating_island` (konvex), `floor_tile`, `hatch`, `floor_grate` (Schacht bleibt offen, Deckel / Rost auf
  `Panel`), `vent_shaft` (innen begehbar), `lift` (Deck fährt mit), `force_field` (`Field`).
* Ohne `colliders` bleibt alles wie bisher (Hülle). Zerstörte Varianten haben keine.
* `docs/UNITY_INTEGRATION.md`: der Import-Prompt nutzt `colliders` – auch für statische Modelle über `AssetRegistry`.

### Neu: 17 Typen (jetzt 121)

* Fallen: `crusher`, `saw_blade`, `steam_vent`, `shock_plate`
* Rätsel: `combination_lock`, `sliding_puzzle`, `balance_scale`, `freq_dial`, `switch_panel`
* Bau-Kit: `spiral_stairs`, `railing`, `cage`
* Items: `flashlight`, `key`, `cable_reel`
* Geräte: `coffee_machine`, `vending_machine`
* Rezept `recipes/traps_riddles.json`; Interaktions-Prompt um Mechaniken 19–23 erweitert.

### Kompatibilität

* Gleiche Seeds liefern dieselben Modelle wie 0.5.0; neue Typen ändern keine bestehenden Assets.

## Frühere Versionen

Siehe Git-Historie (0.5.0: 104 Typen, Parameter & Stil, Texturen, Zerstörung, Blender-Add-on).

# Changelog

## Unveröffentlicht

### Modell-Generationen

* `--generation 1|2` (Rezept/Familie `"style": {"generation": 1}`, Add-on „Generation“, Standard 2): Korrekturen,
  die bestehende Seeds verändern, gelten erst ab ihrer Generation. Generation 1 baut die Modelle von cubegen 0.9.0
  bitgleich nach (geprüft gegen die Fingerabdrücke von 0.9.0, alle Typen; nur die korrigierte Verdrahtung der
  Luftschleuse bleibt). Generation 2 enthält die Korrekturen für flackernde Flächen und Draw Calls (unten).
* Der Sidecar nennt die Generation unter `style.generation`. `--match` baut ein vorhandenes Modell in seiner
  Generation nach; Sidecars ohne diesen Eintrag stammen aus Generation 1.

### Gemeinsamer Vertrag mit dem Unity-Import

* `cubegen/contract.json` enthält die Regeln des Unity-Imports (Schlüssel, Rollen, Feldtypen, Regeln, Collider,
  Toleranzen, Dateigrenzen); `contract.py` liest sie von dort. Neu geprüft: höchstens 4 MiB, 64 Ebenen, keine
  doppelten Schlüssel.
* `python -m cubegen contract --out <Datei>` gibt dieselbe Datei an den Unity-Import weiter.

### Add-on: Typ-Menü

* Typen, die nicht zur gewählten Familie passen, stehen im Typ-Menü mit Warnsymbol und Grund; das Panel nennt
  den Grund, wenn so ein Typ gewählt ist.

### Unity-Prüfung bei jedem Export

* `cubegen/contract.py` lief bisher nur in den Tests. Jetzt prüft `generate` alle Sidecars mit den Regeln des
  Unity-Imports, bevor Blender startet: Ein Verstoß bricht den Export mit allen Fundstellen ab, offene Item-IDs
  stehen als Hinweis im Log. Nach dem Export wird jede FBX gegen ihren Sidecar geprüft (Pivots, Bounds).
* Neu: `python -m cubegen check --export <Ordner>` prüft einen fertigen Export-Ordner (Fehlercode 1 bei Fehlern).

### Keine flackernden Flächen mehr

* Liegt ein Detail (Warnstreifen, Glow-Leiste, Paneel, Rahmen) bündig auf einer anderen Fläche mit anderem
  Material oder an einem anderen Teil, hebt `generate_asset` die kleinere Fläche um 2 mm entlang ihrer Normale an
  (`quality.fix_z_fighting`). Danach: 0 flackernde Flächen in allen 129 Typen, intakt, beschädigt, zerstört, mit
  Abnutzung und in allen Detailstufen. Abnutzung verändert das Modell weiterhin nicht.
* **Geänderte Modelle** (Aussehen gleich, Vertices um 2 mm verschoben, die Dateien ändern sich): die 50 Typen, die
  0.9.0 mit flackernden Flächen gemeldet hat - `balance_scale`, `battery_bank`, `bed`, `bin`, `broken_wall`,
  `bulkhead`, `button`, `cable_plug`, `cable_tray`, `cage`, `camera`, `console`, `crate`, `crate_pile`,
  `cryo_pod`, `door`, `drone`, `extinguisher`, `fallen_pillar`, `floor_grate`, `force_field`, `gear_puzzle`,
  `hatch`, `hydroponic_bed`, `keycard`, `ladder`, `laser_mirror`, `laser_splitter`, `lift`, `locker`, `medkit`,
  `pad`, `pipe_fitting`, `plant`, `pump`, `scanner`, `service_robot`, `shutter`, `socket`, `spiral_stairs`,
  `steam_vent`, `table`, `tool_cart`, `valve`, `vending_machine`, `vent_shaft`, `wall`, `wall_panel`,
  `window_wall`, `workbench` - und einzelne beschädigte, zerstörte oder abgenutzte Varianten weiterer Typen.

### Draw Calls

* Bewegliche Teile mit drei Materialien haben jetzt zwei: Die Punkte der Schiebeplatten (`sliding_puzzle`) tragen
  die Zeilenfarbe, die Hüften von `spider_bot` das dunkle Material der Beine, Risse auf einer markierten
  Bruchplatte (`breakable_platform`) die Warnfarbe. Diese drei Typen sehen dadurch leicht anders aus.
* Das Budget berücksichtigt, dass einzeln bewegliche Teile in Unity nicht zusammengefasst werden können:
  16 pro Modell oder 2 pro Teil + 2, Abnutzung kommt hinzu; statische Modelle zählen ein Material einmal (Static
  Batching). Kein Typ überschreitet es, in keinem Zustand.

### `window_wall` und `wall_corner` folgen den Familien

* Neue Parameter `height` und `thickness` (wie bei `wall`; ohne Angabe bitgleich wie bisher), `window_wall.sill`
  bis 2 m, die Fensteroberkante folgt der Wandhöhe. `wall_height`, `wall_thickness` und `window_sill` der Familie
  gelten jetzt auch für sie, `foundry` (4 m) und `lab` (0,3 m) können sie verwenden.
* Jedes Kit hat eine Eckwand (`wall_corner`, Anschlüsse an den Wandseiten; Passungsprüfung ohne Befund).

### Add-on und Doku

* Add-on: „Von jedem Typ“ und „Alle Typen exportieren“ zählen nur Typen, die zur gewählten Familie passen.
* README: Parametertabelle aller Typen, erzeugt aus der Registry (`tools/param_table.py --write`; ein Test meldet,
  wenn sie veraltet); Blender „getestet mit 4.0 und 5.2 LTS“.

### Behoben: Luftschleuse öffnet sich in Unity nicht

* Bei `door` Stil `airlock` (oben/unten geteilt) stand das untere Blatt zuerst in `panels`. Unity bewegt das
  zweite Blatt um `-openOffset`: Das untere fuhr nach oben, das obere nach unten, beide durcheinander hindurch,
  die Öffnung blieb zu. Jetzt steht das obere Blatt (`Panel_B`) zuerst. Geometrie und Teilenamen sind
  unverändert, nur der Sidecar ändert sich. Mit 0.9.0 exportierte Luftschleusen bitte neu erzeugen.
* `cubegen/contract.py` prüft jetzt, dass zwei Türblätter auseinanderfahren (mit `secondOffset` oder dessen
  Standard).
* Dokumentiert (`docs/UNITY_INTEGRATION.md`): Klappen von `hatch`, `fuse_box`, `cage` und `safe` brauchen in
  Unity einen Zwei-Stellungs-Modus, das vorhandene `Rotatable` dreht zyklisch weiter.

### Behoben: Add-on mit Familie `foundry` oder `lab`

* Mit gewählter Familie `foundry` oder `lab` brachen Vorschau, Raster, „Von jedem Typ“ und „Kit bauen“ im Add-on
  ab (`window_wall can't follow window_sill = 1.6` bzw. `fixed wall_thickness`). Das Add-on hat die Maße der
  Familie auf alle 129 Typen angewandt statt nur auf die Typen, die gebaut werden; `window_wall` und
  `wall_corner` haben feste Maße und können diesen beiden Familien nicht folgen. Die Kommandozeile war nicht
  betroffen.
* Jetzt folgen nur die gebauten Typen den Maßen. „Von jedem Typ“ lässt Typen aus, die nicht zur Familie passen,
  und nennt sie; ein einzelner solcher Typ in der Vorschau meldet den Grund, statt einen Traceback zu zeigen.
* Neu: `families.misfits(dims, types)` liefert die Typen, die bestimmten Maßen nicht folgen können, mit Grund.

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

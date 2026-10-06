# Changelog

## Unveröffentlicht

Roadmap Phase 3 (Erweiterungen) ohne den Raum- und Level-Generator: Einrasten im Add-on, Paletten-Modus,
symmetrisches Schwenken, vier neue Familien mit Requisiten, Zustand `fractured`, Text auf Modellen, Anker für Ton und
Effekte, 35 neue Typen (jetzt 164).

### Einrasten im Blender-Add-on

* Neues Panel „Einrasten“: **Einrasten** setzt das Teil des aktiven Objekts an den nächsten passenden freien
  Anschluss eines anderen Teils (ausgewählte Teile, sonst alle gebauten): Stegende an Stegende, Rampe an Steg oder
  Plattform, Tür bzw. Portal in die Wandöffnung, Rohr an Rohr bzw. durch die Durchführung, Wandende an Wandende,
  Wandabschluss auf die Wand, Sockelleiste an die Wandfläche, Deckenmodul an Deckenmodul. Das Teil dreht nur um die
  Hochachse; belegte Anschlüsse werden übersprungen, wiederholtes Einrasten baut Ketten. **Anschlüsse zeigen** setzt
  Pfeile an alle Anschlusspunkte, **Reichweite** begrenzt die Suche.
* Kern in reinem Python (`cubegen/snapping.py`, getestet ohne Blender); welche Anschlussarten wie zusammengehören
  (gegenüber oder gleich ausgerichtet), steht in `families.JOINS` neben den Passungsregeln `families.RULES`.
* Neue Anschlüsse: Wände, Fensterwände und Torbögen haben `wall_top` (oben) und `face` (beide Wandflächen),
  `ramp` (`floor_walk` unten, `ramp_top` oben), `ceiling_module` (`ceiling`, vier Kanten), `wall_cap` (`cap`,
  `cap_end`), `baseboard` (`trim`, `trim_end`). Neue Passungsregeln: Wandabschluss auf der Wand (Stärke, Höhe, die
  Wand ist ein ganzes Vielfaches des Abschlusses), Sockelleiste an der Wandfläche, Rampe an Steg/Plattform, Decke an
  Decke, Abschluss an Abschluss, Leiste an Leiste.

### Paletten-Modus (`--textures palette`)

* Ein Material `MP_Palette` pro Modell, also ein Draw Call: Alle Farben des Spiels liegen als 16-px-Zellen in einer
  64 × 64-Palettentextur, jede Fläche zeigt mit ihren UVs auf die Mitte ihrer Zelle (Punktfilterung). Dazu
  Metallic/Smoothness- und Emissionsbild und `CubeEscape_Palette.json`. Reines Python (eigener PNG-Schreiber), auch mit
  `--no-blender` (OBJ/MTL).
* Glas und Teile, deren Material die Scripts umschalten (`SignalIndicator.renderers`, `Machine.glow`,
  `SignalLight.glow`, `Rotatable.glow`, `Door.statusLights`), behalten ihr Material. Statische Modelle: 1 Draw Call
  (2 mit Glas). `check --palette` zählt die Draw Calls so. Add-on: Texturen „Palette“, auch in der Vorschau.
* Der Sidecar nennt `MP_Palette` als Material der Teile; sein Schema bleibt unverändert (kein `textures`-Eintrag,
  den der Unity-Vertrag nicht kennt). Das Manifest beschreibt die Palette unter `textures`.

### Symmetrisches Schwenken für `camera` und `turret`

* Neuer Parameter `sweep` (Grad, 0 = aus): Der Kamerakopf (`Rotor`) bzw. das Geschütz (`Turret` mit `Gun` und
  `Glow`) wird um den halben Winkel vorgedreht gebaut, `Rotator.arc` = `sweep` schwenkt es dann gleichmäßig nach
  beiden Seiten (120 = ±60°); ohne `speed` mit 30 °/s. Die Kamera-LED wird dabei Kind des Kopfes und schwenkt mit.
  Ohne `sweep` bleiben beide Typen unverändert.

### Vier neue Familien mit Requisiten

* `medbay` (Krankenstation), `derelict` (verlassenes Wrack, Stil `damage` damaged, starke Abnutzung),
  `greenhouse` (Gewächshaus), `reactor` (Reaktor) - jeweils mit Bau-Kit und Requisiten im Kit (Liegen,
  Laborgeräte, Waschraum, Schilder mit Text; Wracks, Bewuchs; Pflanzen, Wasser, Solarpanel; Reaktorkern, Trafo,
  Kran, Countdown …). Passungsprüfung über drei Seeds ohne Befund.
* Die Kits von `station`, `lab` und `foundry` enthalten zusätzlich Torbogen, Wandabschluss, Sockelleiste,
  Decken-/Dachmodul und Rampe (neue Teile, bestehende unverändert).
* Neues Maß `ceiling_thickness` (Deckenstärke); `wall_height`, `wall_thickness`, `module`, `door_width`,
  `door_height`, `walk_width` gelten auch für die neuen Bau-Kit-Typen.

### Zustand `fractured`

* `--damage fractured` (Add-on: Zustand „Bruchstücke“): Das Modell sieht intakt aus, besteht aber aus 4-12
  Bruchstücken `Fragment_<nn>`. Voronoi-Zellen um einige Seed-Punkte zerschneiden jede konvexe Grundform (Boxen,
  gefaste Boxen, Zylinder), die Schnittflächen tragen das Bruchmaterial; andere Formen gehen ganz an die Zelle ihrer
  Mitte. Jedes Bruchstück hat seinen Pivot in der Mitte und einen konvexen Mesh-Collider; das Volumen bleibt
  erhalten, keine flackernden Flächen. Statisch (keine Scripts) bis Unity es zerstört.

### Text auf Modellen

* Low-Poly-Blockschrift (`cubegen/models/lettering.py`: A-Z, Ä Ö Ü, 0-9, `- + . : / _ ' ! #`).
* `sign.text` (Schild mit Text statt Symbol, so breit wie der Text), `door.label` (Raumnummer über der Tür, eigenes
  statisches Teil `Label`), `countdown.text`, `floor_plan.title`. Ohne Angabe bleiben alle Modelle unverändert.

### Anker für Ton und Effekte (Generation 3)

* Neue Modell-Generation 3 (Standard): Maschinen, Türen, Lifte, Fallen, Roboter, Geräte und viele neue Typen
  bekommen leere Teile für Unity - `Audio_Hum`, `Audio_Door`, `Audio_Servo`, `Audio_Beep`, `Audio_Alarm` … und
  `FX_Steam`, `FX_Sparks`, `FX_Smoke`, `FX_Dust`, `FX_Muzzle`, `FX_Spores` … (`cubegen/models/anchors.py`). Ein Anker
  ist Kind des Teils, auf dem er sitzt, und bewegt sich mit ihm. Zerstörte Modelle haben `FX_Smoke`, Bruchstücke keine.
* Die Geometrie bleibt exakt wie in Generation 2; `--generation 2` baut die bisherigen Modelle bitgleich nach
  (geprüft: alle Fingerabdrücke der Generationen 1 und 2 unverändert).
* **Geänderte Modelle in Generation 3** (neue leere Teile, Geometrie gleich): `breakable_platform`, `cable_mess`,
  `camera`, `coffee_machine`, `console`, `conveyor`, `crusher`, `cryo_pod`, `crystal_cluster`, `door`, `drone`,
  `fan`, `fluid_basin`, `force_field`, `gear_puzzle`, `generator`, `hanging_crystals`, `hologram`, `intercom`,
  `keypad`, `lift`, `machine`, `monitor_wall`, `mushroom`, `pad`, `phase_platform`, `pipe`, `portal_frame`, `pump`,
  `reactor_core`, `retractable_bridge`, `robot_arm`, `saw_blade`, `scanner`, `server_rack`, `service_robot`,
  `shock_plate`, `shutter`, `spider_bot`, `spike_trap`, `steam_vent`, `terminal`, `transformer`, `turntable`,
  `turret`, `vending_machine`, `vent`; alle Typen ab Zustand `destroyed` (`FX_Smoke`).
* **Behoben in Generation 3**: Beschädigte Modelle (`--damage damaged`) schlagen von Teilen, aus denen Unity
  Collider baut (`Door.colliders`, `Machine.body` …), nichts mehr ab. Bisher konnte ein Stück von `Frame_Top` auf
  dem Boden liegen; die Hülle des Rahmens reichte dann quer durch die Türöffnung. Beschädigte Varianten dieser Typen
  sehen dadurch etwas anders aus: `cargo_container`, `crusher`, `door`, `force_field`, `generator`, `lift`,
  `machine`, `pump`, `reactor_core`, `shutter`, `transformer`.

### Neue Typen (jetzt 164)

* Bau-Kit: `ramp`, `ceiling_module`, `archway`, `wall_cap`, `baseboard`.
* Rätsel: `push_block`, `sequence_panel`, `water_level`, `laser_filter`, `symbol_plate`, `crane`, `countdown`.
* Requisiten: `lab_device` (Mikroskop, Reagenzglas-Ständer, Zentrifuge), `galley` (Küche, Messe, Kühlschrank),
  `washroom` (Waschbecken, WC, Dusche), `floor_plan` (Lageplan).
* Licht: `floodlight` (mit echter Lichtquelle über `SignalLight.lightPosition`/`range`/`intensity`),
  `light_strip`, `emergency_light`.
* Roboter: `patrol_drone`, `vent_crawler`, `robot_dog`, `mech`.
* Natur / Alien: `vines`, `cocoon`, `wall_roots`, `fungus_carpet`, `puddle`; Weltraum: `escape_pod`,
  `solar_panel`, `asteroid`, `planet_window`; Ruinen: `crashed_pod`, `burnt_console`, `collapsed_catwalk`.
* Alle mit Unity-Vertrag geprüft (Sidecar und echte FBX), ohne flackernde Flächen, im Dreiecks- und Draw-Call-Budget,
  in allen Zuständen. Rezept: `recipes/phase3_rooms.json`.

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

### Behoben: `archway` – Wand über dem Durchgang nach hinten versetzt

* Das Wandstück über dem Bogen saß eine halbe Wandstärke hinter den Pfosten (y 0 … t statt −t/2 … t/2): vorn
  eine Stufe, hinten stand es über, Rahmenleisten und Schlussstein hingen vorn frei vor der Wand, und der
  Collider über dem Durchgang passte nicht zur Geometrie. Jetzt ist die Wand vorn und hinten bündig, bei allen
  Bogenformen. Mit diesem Stand exportierte `Archway`-Modelle bitte neu erzeugen; Generation 1 ist nicht
  betroffen (den Typ gab es in 0.9.0 noch nicht).
* Der Schlussstein (`round`, `pointed`) hing 5,5 cm unter den Scheitel in den Durchgang, jetzt sitzt er auf dem
  Scheitel. Die Rahmenleisten lagen mittig auf der Kante und standen 6 cm in die Öffnung, jetzt liegen sie ganz
  auf der Wandfläche. Ein Test hält den Bogen bündig mit den Pfosten und den Durchgang frei.

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

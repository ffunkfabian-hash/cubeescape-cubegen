# Changelog

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

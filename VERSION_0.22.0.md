# Cubegen 0.22.0 – Beacon

*abgenommen (Stufe 2, lokal am 14. Oktober 2026)* – Prüfung siehe „Abnahme (Stufe 2)“.

Arbeitsstand vom 14. Oktober 2026, unveröffentlicht; vorherige Version [0.21.3](VERSION_0.21.3.md).
Zuarbeit für Cube Escape 0.57 (gemeinsamer Shader-Unterbau) und 0.58 (Cubegen in der Werkbank: Variantensets,
Anstriche, Anbauten, Anschlussseiten im Modell-Browser) – hier nur die Generatorseite.

## 1. Leuchtkarte der Anstriche im Vertrag (ROADMAP ToDo 26)

**Fund.** `--paint` schrieb seit 0.17.0 je Modell `MTP_<Modell>_<Thema>_Emission.png` und hängte sie im Blender-Material
an, der Sidecar ließ sie aber weg (`pipeline.BAKED_MAP_KEYS`), weil Cube Escapes `CubegenMaterials` nur Albedo, Normal,
MetallicSmoothness, Roughness, AO und Height annimmt – eine unbekannte Karte lehnt das Modell ab. Auch der Vertrag
(`contract.json`) kannte gebackene Karten gar nicht; `check_sidecar` prüfte nur `mode` und `manifest`.
Geprüft am Code von Cube Escape (Stand `aa861d2`): `CubegenContract` verlangt `version == 1` und lehnt jeden
unbekannten Wurzelschlüssel ab; `CubegenMaterials` lehnt unbekannte Karten und unbekannte `textures`-Schlüssel ab.

**Korrektur.**

- `contract.json` **Version 2** mit Abschnitt `baked_maps`: `keys` (sieben Karten), `required` (Albedo, Normal,
  MetallicSmoothness), `srgb` (Albedo, Emission), `since` (`Emission`: 2), `material_prefix` `MTA_`,
  `emission_intensity` 3,0 (Blenders Emission Strength, in Unity `_EmissionColor` = Weiß × 3), `distinct_files`.
  Dazu `history` mit den Versionen.
- `contract.py`: `contract_for(version)` (Version 1 = der Inhalt von 0.21, ohne `history`/`baked_maps`),
  `baked_map_keys(version)`, `check_sidecar(…, version)` prüft `textures` wie der Import (nur `mode`/`manifest`/
  `baked`, Karten nur im Modus `baked`, Pflichtkarten, eine Datei je Karte, unbekannte Karte mit Hinweis auf die
  Version); `check_export(…, version)` findet fehlende Kartendateien.
- Der Sidecar nennt `textures.baked.Emission`, wenn das Thema leuchtet.
- **Nur leuchtende Themen schreiben die Karte** (`paint.scheme_glows`: `edge_glow` > 0 – Crystal, Dark, Space, Ice,
  Toxic, Void). Industrial, Clean, Ruin, Organic und Sand schrieben eine schwarze Karte, die im GLB als
  `emissiveTexture` eine der 16 Texturen des Werkbank-Budgets belegte (gemessen: Kiste Industrial 4 → 3 Texturen).
- **Rückweg für den heutigen Import:** `generate --contract 1` (Rezeptfeld `contract`) schreibt Sidecars ohne
  Emission (die Karte bleibt im Manifest), `contract --version 1` den Vertrag von 0.21 (inhaltsgleich, gleiche
  Wurzelschlüssel wie `CubegenContract` sie annimmt), `check --export … --contract 1`. Ein Sidecar von Version 1
  ist auch für Version 2 gültig. `tools/unity_check.py` liest die Version aus Cube Escapes
  `Assets/Resources/Cubegen/cubegen_contract.json` und schreibt die Prüfsätze dafür.

**Nebenfund.** `puddle` (z. B. Seed 0, `Puddle_000`) besteht manchmal nur aus `M_Crystal`, `M_Glass` oder
`M_GlowOrange`. Mit `--textures baked` (und `--paint`) gibt es dann nichts zu backen, der Sidecar sagte trotzdem
`{"mode": "baked", "manifest": …}` ohne `baked` – Cube Escapes Import verlangt dort die Karten und hätte das Modell
abgelehnt; der Vertrag prüfte es nicht. Jetzt: kein `textures`-Eintrag (die Teile tragen ihre `M_*`-Materialien), und
der Vertrag meldet „mode baked needs baked“. Gegen 0.21.3 nachgestellt (gleicher Aufruf, alter Stand im Worktree).

## 2. Manifestdaten für Cube Escape (ToDo 16, 25, 30, 31)

Geprüft, was der Modell-Browser braucht und was fehlte:

| Bedarf | vorher | jetzt |
|---|---|---|
| Sets: Name, Typ, Mitglieder (ToDo 25) | `sets[]` mit `name`, `type`, `members`, `pinned`, `outline_ok`, `deviation_m`, `preview` | unverändert, dazu `models[].set` (Rückverweis) |
| geprüfte Anschlussseiten (ToDo 31) | `sets[].faces` nur in Generator-Achsen (`x-`, `y+` …, Blender) | `sets[].faces_unity`: Richtung nach außen (Unity) und Abstand vom Pivot; `sets[].bounds` (Umriss) |
| Anschlüsse je Familie (ToDo 16) | `models[].connectors` (Unity); welche Arten zusammenpassen, stand nur in `families.JOINS` | `joins` (Arten, `face`/`align`, `fit_check`); `connectors[].moves` – der Anschluss der ausfahrenden Brücke verlor bisher seine Bewegung |
| Anbauten je Thema (ToDo 30) | nur in `meta.params`, und nur wenn ungleich `none` | `dressings` (Werte, Standard, Typen, passendes Thema) und `models[].dressing` mit wirksamen Werten |

`format: 2` kennzeichnet den Stand (bis 0.21 ohne Schlüssel = 1). Nur Ergänzungen – vorhandene Schlüssel behalten
ihre Bedeutung, ein Leser von Format 1 läuft weiter. Beschreibung mit Beispielen:
[docs/UNITY_INTEGRATION.md](docs/UNITY_INTEGRATION.md) › „Manifest für Cube Escape“ und „Versionen des Vertrags“.

`crystals` zählt nur dort als Anbau, wo es eine Auswahl ist (`test_wall_modules`); bei Fels, Schwebeinsel und
Hängekristallen ist es eine Anzahl und gehört zur Form.

## 3. Aufräumen

`.DS_Store` steht in `.gitignore` (es war keine Datei eingecheckt).

## Prüfung (Stufe 1)

- Neue Regressionen `tests/test_release_0220.py` (15 Tests): Vertragsversionen, `contract --version 1`,
  Sidecar-Karten je Version, fehlende Kartendateien, `--contract` in Konfiguration, CLI und Unity-Check,
  Manifest (Format, Sets in Unity-Koordinaten gegen die Sidecar-Bounds, Anbauten, `joins`, bewegte Anschlüsse);
  mit Blender: Dark mit Leuchtkarte in Manifest, Sidecar, Datei und GLB; Industrial ohne Karte; `--contract 1`;
  `puddle` ohne `textures`.
- Bewusst geändert: `test_release_0170` erwartete für Organic eine Emission im Manifest – Organic leuchtet nicht,
  die schwarze Karte entfällt.
- Volle Suite in der Cloud (`tools/run_tests.py --tier full`, Blender 5.2.2 als bpy-Modul, ImageMagick 6.9):
  355 Tests grün in 236 s (vorher 340), 4 übersprungen wie vor der Änderung – Vision-Bericht (nur macOS),
  PNG-Define (nur ImageMagick 7), echter Unity-Check (`CUBEGEN_UNITY_CHECK=1`), 2048-px-Kiste
  (`CUBEGEN_SLOW_TESTS=1`).

## Abnahme (Stufe 2)

Lokal auf dem Mac (Apple M5, Blender 5.2.2 LTS, ImageMagick 7.1.2, Python 3.12), Stand `a72d0c7`:

- **Volle Suite** `CUBEGEN_UNITY_CHECK=1 CUBEGEN_SLOW_TESTS=1 python3 tools/run_tests.py --tier full`: 355 Tests grün
  in 233 s (models 41, quality 12, params 38, rest 264), darunter der echte Unity-Lauf, die 2048-px-Kiste, der
  Vision-Bericht und der PNG-Vergleich mit ImageMagick 7. Übersprungen nur
  `test_release_0180…test_dust_and_moss_leave_patches_instead_of_covering_the_top` (das System-Python hat kein numpy) –
  mit Blenders Python 3.13 (numpy 2.3.4) `tests.test_release_0180`: 8 Tests grün, keiner übersprungen.
- **Unity-Check** `python3 tools/unity_check.py --require` gegen Cube Escape `875ef216` (0.55.0, Vertrag Version 1):
  **9 Prüfsätze, 262 Modelle, 0 abgelehnt, 0 Fehler** (1:48 min). Laufzeitpfad: 187 GLB, 179 angenommen, 8 mit nicht
  unterstütztem Verhalten, 0 fehlgeschlagen – gleich wie 0.21.3 (`--only runtime` gegengeprüft).
- **Echte Exporte** `test_wall_modules` und `crate`, Seed 19, `--textures baked --formats fbx,glb`, je `--paint crystal`,
  `dark` und `industrial`: Crystal und Dark nennen `textures.baked.Emission` (sRGB, 512 px, eine Datei je Modell),
  Industrial schreibt keine Leuchtkarte. `check --export`: Vertrag 2 alle 6 Modelle gültig; Vertrag 1 lehnt die vier
  leuchtenden wie vorgesehen ab, Industrial bleibt gültig.
- **Sichtprüfung im Blender-Plugin** (laufendes Blender, eigene Szene, nichts gespeichert): GLB-Import hängt die
  Leuchtkarte an `Emission Color` mit Stärke 3 (`MTA_…`); gerendert leuchten bei Crystal die Kanten cyan, bei Dark rot,
  deckungsgleich mit den Kanten der Albedo; Industrial ohne Leuchtkanten. Die Glow-Teile (`M_Glow…`) bleiben untexturiert.
- Import und Kollision in der Cube-Escape-Testkopie über den Unity-Check (Editor-Import mit Collidern, LODs,
  Wiederimport); keine neuen Typen und kein neues Verhalten, daher keine eigene Physikprüfung.

## Grenzen

- Cube Escape liest Version 2 noch nicht: bis zur Umstellung (CE 0.57/0.58) `--contract 1` für Exporte ins Spiel.
  Danach `python3 tools/unity_check.py --require` erneut, dann mit Version 2 (Leuchtkarte im Editor-Import).
- Der Laufzeitpfad der Werkbank (GLB) bekommt die Leuchtkarte unabhängig vom Vertrag über `emissiveTexture`.
- `joins` beschreibt Paare von Anschlussarten, kein Layout; der Raumgenerator (Erweiterung 1) bleibt offen.

# Cubegen 0.24.0 – Primer

*ungeprüft: Blender-/Unity-Abnahme offen* – Stufe 1 in der Cloud (Blender 5.2 als bpy-Modul, ImageMagick 6); offen
sind die Sichtprüfung, `tools/unity_check.py --require` und der Import in der Cube-Escape-Testkopie (unten).

Unveröffentlicht; vorherige Version [0.23.0](VERSION_0.23.0.md).
Zuarbeit für Cube Escape 0.57 „Undercoat“, Phase 3 „Anstrich“ (Cube Escape `Docs/MATERIALS.md` › „Zuarbeit für
Cubegen 0.22“): Punkte 2, 3, 4, 6 und 7. Punkt 1 (Leuchtkarte) kam mit 0.22 „Beacon“; Punkt 4 stand dort als
geliefert, fehlte aber (`cubegen/materials.py` kannte nur `M_Crystal`) und kommt hier. Punkt 5 (GLB-Laufzeitpfad)
bleibt offen. Generatorseite; Cube Escape stellt selbst um.

## 1. Neutrale Karten im Sidecar (Zuarbeit 2, ROADMAP ToDo 27)

**Fund.** `--paint` legte die neutralen Karten seit 0.17.0 einzeln unter `Textures/Neutral` ab (Gewichte W0–W2, AO,
Kante, oben, Höhe, Diffus, Normale – bis zu neun Bilder), nur im Manifest genannt. Das Rauschen, das `compose` braucht,
entstand bei jedem Zusammensetzen aus einem numpy-Seed (`stylebake._noise`) und das Detail aus der Diffus-Karte als
Gleitkommazahl – ein Shader hätte beides nur nachbauen können, nie exakt.

**Umsetzung** (`cubegen/neutral.py`, `stylebake.pack_maps`/`paint_asset`):

- Fünf gepackte Karten je Modell, `Textures/MTN_<Modell>_<Karte>.png`, linear, 8 Bit:
  `W0` (RGB Gewichte der ersten Dreiergruppe, A **Rauschen**), `W1` (RGB zweite Gruppe oder schwarz, A **Detail**,
  `0,35 + A × 1,45`), `W2` (dritte Gruppe, nur wenn es sie gibt, A reserviert = 1), `Fields` (R AO, G Kante, B oben,
  A Höhe), `Normal` (gleiche Pixel wie die Normalenkarte des Themas). Bis zu acht Karten werden fünf.
- **Die fertigen Karten (`MTP_`) entstehen aus genau diesen 8-Bit-Werten** (`neutral.compose_packed` →
  `paint.compose`). Damit rechnet ein Shader, der die `MTN_`-Karten liest, das Referenzbild exakt nach. `compose`
  selbst ist unverändert (Entscheidung 2 in `MATERIALS.md`). Folge: Die `MTP_`-Karten ändern sich gegenüber 0.23 um
  höchstens 5/255 (Albedo; im Mittel 0,14/255; Rauheit 3/255, Metall/Glätte 3/255, Emission 0), gemessen an Kiste,
  Säule und Modulwand in allen elf Themen – nicht sichtbar.
- Das Rauschen bleibt die Formel von 0.17.0 (`neutral.noise`, Test gegen die alte Rechnung); PNG ohne Blender lesen
  und schreiben (`neutral.read_png`/`write_png`, alle Zeilenfilter), damit Werkzeuge und Tests ohne Blender rechnen.
- Sidecar (Vertrag 3): `textures.neutral` (Karte → Pfad) und `textures.weight_layout`. Manifest: `models[].neutral_maps`
  bei jeder Vertragsversion; die Rohdaten unter `Textures/Neutral` bleiben (`models[].neutral`, Stiltest).
- Budget: Die neutralen Karten liegen nicht im GLB (Werkbank-Budget unverändert); im Editor-Import sind es fünf statt
  acht Texturen je Modell, die fertigen Karten bleiben der Rückfall für niedrige Stufen.

## 2. Thema als Daten (Zuarbeit 3)

- Sidecar-Wurzelschlüssel `paint` (Vertrag 3): Name eines eingebauten Themas – oder ein eigenes Thema vollständig
  (`name` und alle `SCHEME_KEYS`, alle neun Farben). `check_sidecar` prüft es mit `paint.check_scheme`.
- `cubegen catalog --paints` liefert nur die Themen (`paints`, `paint_schemes`, `paint_fields`, neu `paint_keys`) –
  schnell, ohne Modelle zu bauen; Cube Escape spiegelt die Datei wie `cubegen_contract.json`. Der volle Katalog trägt
  `paint_keys` ebenfalls.

## 3. Eigene Materialnamen statt `M_Crystal` (Zuarbeit 4, ToDo 28)

**Fund.** `M_Crystal` trugen auch Wasser, Schlamm, Laborflüssigkeiten, Hologramme, Energiefelder, Lampen, Sterne,
Alien-Blätter, Pilze, Leuchtknospen, die Sequenzfarbe, Teleporterring, Linsen und Prismen – 20 Typen. Ein
Kristallmaterial nach Namen hätte all das getroffen.

**Umsetzung** (`materials.CRYSTAL_SPLIT`): acht neue Namen am Ende der Materialtabelle, vorerst mit den Werten von
`M_Crystal` (gleiches Aussehen): `M_Liquid`, `M_Hologram`, `M_Lamp`, `M_Leaf`, `M_Biolume`, `M_Signal`, `M_Accent`,
`M_Optic` (Zuordnung je Typ: `docs/UNITY_INTEGRATION.md` › „Eigene Materialnamen“). `M_Crystal` tragen nur noch echte
Kristalle (`materials.CRYSTAL_TYPES`: Fels, Kristallgruppe, Hängekristalle, Asteroid, Stalagmit, Schwebeinsel,
Plattform-Unterseite, Reaktorkern, Kryo-Reif, Ersatzteil „crystal“, Modulwand). Die neuen Namen behalten wie Glow,
Kristall und Glas ihr eigenes Material beim Backen, Anstreichen und in Paletten (dort die Zelle von `M_Crystal`, das
Palettenbild bleibt gleich) und zählen bei Zerstörung als Leuchtteil. Die Kristallfarbe eines Themas gilt nur noch
für `M_Crystal`.

- Vertrag 3, Abschnitt `materials` (`split` mit Verwendung, `like`, `legacy`); Manifest `materials` mit Farbe (sRGB),
  Glätte, Metall, Emission je Name und `written`.
- **Rückweg:** `--contract 2`/`1` setzt das Spec-Flag `legacy_materials` – `Asset.legacy_materials` schreibt wieder
  `M_Crystal` (Flächen, Verhaltensfelder, Meta, auch in Texten wie der Notiz am `SignalIndicator`). Der Vertrag lehnt
  die neuen Namen für Version 2/1 ab (Teile und Verhaltensfelder).
- **Unveränderte Geometrie belegt:** Für alle 187 Typen × 27 Golden-Fälle ist das Modell mit Rückweg bitgleich zum
  Digest von 0.23.0. Die Golden-Daten der 20 betroffenen Typen sind neu (nur die Materialnamen); die alten Digests
  liegen als `tests/fixtures/golden_0230_crystal.json` bei, ein Test prüft den Rückweg dagegen.
- Alte Ausgabe bleibt historisch: Exporte bis 0.23 tragen `M_Crystal`.

## 4. Vertrag Version 3

`contract.json` Version 3 mit `history["3"]`, `root.keys` + `paint` (`root.since`), neuen Abschnitten `textures`
(Schlüssel mit `since`), `neutral_maps`, `materials` und `paint_scheme`. `contract_for(2)` ist die Datei von
0.22/0.23 (Fixture `tests/fixtures/contract_v2.json`, bytegleich im Inhalt), `contract_for(1)` die von 0.21.
`generate --contract 2|1`, `contract --version 2|1`, `check --export … --contract 2|1` wie gehabt. Unbekannte Schlüssel
melden die Version, ab der sie gelten.

## 5. Vergleichsbilder (Zuarbeit 6)

`tools/paint_reference.py <Lauf>` setzt aus den `MTN_`-Karten eines Laufs jedes eingebaute Thema (und das eigene des
Laufs) ohne Blender zusammen: `paint_reference/<Thema>/MTP_<Modell>_<Thema>_*.png` und `reference.json` (Modelle,
Layout, Themendaten, vorgeschlagene Toleranz 3/255 je Kanal, im Mittel 0,5/255). `--check` vergleicht das Thema des
Laufs mit den Karten, die Blender speicherte: **bitgleich** – in den Tests Dark und Toxic (Kiste, Verkaufsautomat
mit drei Gewichtsgruppen), von Hand dazu Organic, Ruin, Crystal und das eigene Thema `rust_bucket` (Seed 7: Modulwand,
Verkaufsautomat, Boden, Hologramm, 128 px). Braucht numpy (in Blenders Python vorhanden:
`blender -b --python tools/paint_reference.py -- <Lauf>`).

## 6. Unity-Check: Prüfsatz „Anstrich neutral“ (Zuarbeit 7)

`tools/unity_check.py` Prüfsatz `neutral` (Seed 23, Kiste, Boden, Säule, Wand, Modulwand, Verkaufsautomat mit `W2`,
Hologramm und Flutlicht mit neuen Materialnamen; Thema Dark, 128 px), auch in `--quick`. Liest Cube Escape
Vertrag 3: echter Import. Darunter zwei Läufe: für Version 3 geschrieben muss der Import **jedes** Modell ablehnen
(jeder Modellname in der Fehlerausgabe oder im Unity-Log, `rejected_as_expected`), für Cube Escapes Version
geschrieben (ohne neutrale Karten, `M_Crystal`) muss er sie annehmen. Jeder Prüfsatz mit Anstrich bekommt seine
Vergleichsbilder (`<Prüfsatz>/paint_reference`, als `$CUBEGEN_PAINT_REFERENCE` an Unity); ohne numpy wird das mit
Hinweis übersprungen.

## Prüfung (Stufe 1)

- Neue Regressionen `tests/test_release_0240.py`: Vertragsversionen (Fixture Version 2), Abschnitte = Code,
  Sidecar-Regeln für neutrale Karten und Thema, fehlende Dateien, Paint-Katalog, Packen/Entpacken, Detail-Kodierung,
  Rauschformel, PNG mit allen Filtern, `compose_packed`, Referenzwerkzeug (ohne Blender), Prüfsatz `neutral`
  (Läufe, Ablehnung), Kristall-Aufteilung (nur Kristall-Typen nutzen `M_Crystal`, jeder neue Name wird benutzt,
  Werte, Rückweg gegen 0.23-Digests, Vertragsprüfung je Version); mit Blender: echte `--paint`-Läufe (Sidecar,
  Manifest, Dateien, `W2`, Python = Blender bitgleich, `--contract 2`, eigenes Thema, reproduzierbare Bytes, Werkzeug
  auf der Kommandozeile).
- Bewusst geändert: `test_release_0220` erwartete Version 2 als aktuelle Version – jetzt über `contract_for(2)`;
  Golden-Daten der 20 Typen mit neuen Materialnamen (oben belegt).
- Volle Suite in der Cloud (`tools/run_tests.py --tier full`, Blender 5.2.2 als bpy-Modul, ImageMagick 6.9):
  381 Tests grün in 7:24 min (models 41, quality 12, params 38, rest 290), 4 übersprungen wie bisher –
  Vision-Bericht (nur macOS), PNG-Define (nur ImageMagick 7), echter Unity-Check (`CUBEGEN_UNITY_CHECK=1`),
  2048-px-Kiste (`CUBEGEN_SLOW_TESTS=1`).

## Vor dem Merge noch offen (Stufe 2, lokal)

- Volle Suite mit Blender-App und ImageMagick 7 ohne übersprungene Tests.
- Echte Exporte mit `--paint` (mehrere Themen, eigenes Thema), `MTN_`-Karten ansehen (Kanäle einzeln), Kontaktbogen.
- `python3 tools/unity_check.py --require` gegen Cube Escape (liest Vertrag 2): `neutral` muss mit Vertrag 3
  abgelehnt und mit Vertrag 2 angenommen werden; die übrigen Prüfsätze unverändert grün. Die Ablehnungserkennung
  (Modellnamen in Ausgabe/Log) ist ohne Unity nur an Textbeispielen getestet.
- Sobald Cube Escape die acht Materialien in der `MaterialLibrary` hat und Vertrag 3 liest: `neutral` als echter Import.

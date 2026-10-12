# Cubegen 0.17.0 – Prism

*ungeprüft: Richtungsentscheidung offen* – experimenteller Stiltest, die normale Ausgabe (`generate`) ist unverändert.
Unveröffentlicht, Branch `release/0.17.0`; vorherige Version [0.16.0](VERSION_0.16.0.md).

## Inhalt

Stiltest „Texturen wie der Roboter-Generator“ nach dem Konzeptbogen „Umgebungs-Konzepte“ des Nutzers: Ein Modell wird
**einmal neutral gebacken**, jeder **Anstrich** (Paint Scheme) ist nur Daten und wird aus diesen Karten zusammengesetzt –
das Skin-Prinzip des Roboter-Generators (1.8: Skins aus Gewichtskarten) für Umgebungsmodelle.

| Teil | Inhalt |
|---|---|
| `cubegen/paint.py` | Anstriche als Daten (`industrial`, `crystal`): Farbe je Spielmaterial, Abnutzung, Schmutz, Staub, Kantenleuchten, Rauheit, Leuchtfarbe (die vorhandene `--glow`-Farbe); Gewichts-Layout (drei Materialien je RGB-Bild); `compose` und `detail_map` (numpy) |
| `cubegen/stylebake.py` | in Blender: neutrale Karten auf einem Atlas einer zusammengefügten Kopie – Gewichte, Umgebungsverdeckung, Kantenmaske (Cycles-Bevel-Normale gegen echte Normale), „oben“-Maske (Staub/Bewuchs), dazu Helligkeit und Normalen der Kacheltexturen (Fugen, Nieten, Kratzer); Zusammensetzen eines Anstrichs mit numpy (`float32`), ein Material je Anstrich |
| `tools/style_test.py` | Werkzeug: plant die Modelle, startet Blender, rendert heute (Spielfarben, Kacheln) und jeden Anstrich, baut den Vergleichsbogen mit Konzeptausschnitten (`--concept`) |

Bild: [docs/style_test_0170.png](docs/style_test_0170.png) – Wand, Plattform, Säule, Kiste (Seed 42, Variante 0) heute
und als Industrial/Crystal, rechts Ausschnitte des Konzeptbogens.

```bash
python3 tools/style_test.py --concept <Konzeptbogen.png>    # -> output/style_test/style_test.png
```

## Ergebnis

Gemessen am 12. Oktober 2026 (Apple M5, Blender 5.2.2, Atlas 1024 px, Metal):

| | Wand | Plattform | Säule | Kiste |
|---|---|---|---|---|
| neutrales Backen (einmal) | 42,3 s* | 3,3 s | 2,9 s | 3,0 s |
| zwei Anstriche zusammensetzen | 0,6 s | 0,4 s | 0,4 s | 0,6 s |
| Gewichtsbilder | 2 | 1 | 1 | 1 |

\* einmaliges Kompilieren der Metal-Kernel im ersten Back-Lauf einer Blender-Sitzung.

- **Das Prinzip trägt:** Jeder weitere Anstrich kostet 0,2–0,3 s statt eines neuen Backens (etwa 3 s je Modell bei
  1024 px); zwei Läufe ergeben bytegleiche Karten (Test).
- **Industrial:** orange Riffelblech-Einsätze in der Wand (Spielmaterial `M_Ground`), Stahlgrau, abgestoßene helle Kanten,
  Schmutz in Fugen, etwas Staub oben – nahe am Konzept „01 Industrial“.
- **Crystal:** Schiefer und Stahlblau, wenig Abnutzung, leuchtend blaue Kanten und Leuchtleisten (`--glow cyan`) –
  der Energie-Eindruck von „04 Crystal“.
- **Grenze:** Das Konzept lebt von deutlich mehr Geometrie (Kristalle, Rohre, Kabel, Paneele, Bewuchs). Ein Anstrich
  liefert Farbe, Abnutzung, Staub und Leuchten, aber keine neuen Formen – dafür bräuchte es Anbauteile im Generator.

## Offen – Richtungsentscheidung

1. Anstriche als Ausgabemodus übernehmen (`--paint industrial` o. ä., Karten wie `--textures baked`)?
2. Wie in Unity: Karten je Anstrich fertig zusammengesetzt (einfach, ein Material je Modell und Anstrich) oder neutrale
   Karten + Palette in einem URP-Shader (ein Satz Karten für alle Anstriche, Umfärben zur Laufzeit – wie die Robot-Skins
   in Cube Escape geplant)?
3. Weitere Anstriche aus dem Konzept (Clean, Ruin, Dark, Organic mit Bewuchs über die „oben“-Maske) und Anbauteile
   (Kristalle, Rohre) für mehr Geometrie?

## Prüfung

- `tests/test_release_0170.py` (3 Tests): Anstrich-Daten vollständig und gültig, Gewichts-Layout, ein echter Lauf in
  Blender zweimal mit bytegleichen Karten.
- Vergleichsbogen angesehen (Ausschnitte des Konzepts korrekt, Anstriche wie beschrieben).

## Grenzen

- Experimentell: kein Unity-Import, keine Freigabe im Vertrag; Emissionskarten sind dort noch nicht vorgesehen.
- Nur zwei Anstriche und vier Modelle; Rauschen und Abnutzung sind von Hand abgestimmt, nicht an vielen Typen geprüft.

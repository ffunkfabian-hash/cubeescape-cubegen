# Cube Escape Generator – Version 0.10.2.5

## Überblick

Version 0.10.2.5 erweitert die Geometrie-Primitive um strukturierte Profil- und Konstruktionsformen, die in vorhandenen Familien besonders häufig genutzt werden: Rohr-/Kanalprofile, L-/T-/I-Profile, Keile, Gitter, gerundete Boxen und modulare Rahmenstücke. Dadurch lassen sich Maschinen, Leitungen, Laufstege, Rahmen und technische Umgebungen konsistenter und schneller zusammensetzen, ohne einzelne Spezialmodelle für jedes Bauteil zu erzeugen.

## Änderungen gegenüber 0.10.2.4

### Neue Geometrieformen

Die Geometrie-Engine ergänzt acht wiederverwendbare Formen:

- `pipe_section`: Hohlrohr-/Rohrsegment-Primitive
- `u_channel`: U-/C-Profil für Rahmen, Schachtsysteme und Leitungsanlagen
- `angle_profile`: L-Profil für Eck- und Halterungsbauteile
- `tee_profile`: T-Profil für tragende und verbindende Querschnitte
- `i_beam`: I-Träger für längere, robuste Strukturprofile
- `wedge`: Keil-/Schrägteil für Rampen, Übergänge und Neigungsbauteile
- `grate`: Gitter- und Siebplatten für Lüftung, Bodenraster und Techbereiche
- `rounded_box`: gerundete Box / niedrige „capsule-like“-Variante für Maschinen und Geräte

Alle Formen sind als reine Python-Primitive in `cubegen/geometry.py` verfügbar und folgen den gleichen Layout- und Volumenregeln wie die bestehenden Geometrien.

### Experimentelle CLI-Demo

Der registrierte Typ `geometry_test` stellt alle acht Primitive in einem einzelnen Asset nebeneinander. Die Mesh-Teile sind im Export getrennt benannt. Er dient nur der visuellen Prüfung und ist kein fertiger Gameplay-Gegenstand. Beispiel:

```bash
python -m cubegen generate --seed 42 --types geometry_test --count 1 --out /tmp/cubegen_geometry_test
```

Mit Blender und aktivem Rendern erzeugt der normale Build-Workflow FBX, Render-Vorschau und Kontaktbogen. In der GUI kann derselbe Testtyp über die Typauswahl gebaut und angeschaut werden.

### Zehn experimentelle Gameplay-Asset-Prototypen

Zusätzlich sind zehn einzeln auswählbare, mit `test_` markierte Modelle registriert. Ihre Konzepte stammen aus dem Ideen-Backlog (siehe `IDEEN.md`):

| CLI-Typ | Konzept | Eingebaute neue Geometrien |
|---|---|---|
| `test_utility_trench` | Technikrinne / Kühlmittelweg | U-Profil, Hohlrohre |
| `test_pipe_rack` | Rohrgestell | I-Träger, Hohlrohre |
| `test_relay_box` | Relais-/Leistungsschalterkasten | gerundete Box, Hohlrohre |
| `test_coolant_loop` | Kühlkreislauf mit Serviceventil | Hohlrohre |
| `test_warning_beacon` | Warnleuchte | L-Profile |
| `test_lens_array` | Linsen-Array für Strahl-Ausrichtung | Keil |
| `test_magnetic_lock` | Magnetsperre auf Führungsschiene | U-Profil, Keil |
| `test_scanner_pad` | Scanner-Matte | Gitter, U-Profil, Keil |
| `test_power_routing` | Energie-Verteilpanel | gerundete Box, T-Profil, Hohlrohre |
| `test_thermal_switch` | Thermoschalter / Kühlsteuerung | gerundete Box |

Alle zehn können zusammen als gerenderte Beispielsammlung gebaut werden:

```bash
python -m cubegen generate --seed 42 \
  --types test_utility_trench,test_pipe_rack,test_relay_box,test_coolant_loop,test_warning_beacon,test_lens_array,test_magnetic_lock,test_scanner_pad,test_power_routing,test_thermal_switch \
  --count 1 --out /tmp/cubegen_gameplay_tests
```

Die Modelle sind visuelle Test-Prototypen: Collider sind grobe Platzhalter; Puzzle-Zustände, Unity-Scripts und tatsächliche Interaktionen sind nicht implementiert oder Unity-geprüft.

### Verteilung und Qualität

- kompakter, modularer Zusatz für die vorhandenen Bau- und Maschinenfamilien
- saubere, wiederverwendbare Box-/Profil-Primitiven für deterministische Seeds
- kompatibel mit den vorhandenen Mesh- und Volumenprüfungen
- zehn Test-Prototypen rendern erfolgreich; Qualitätsprüfung ohne Überschreitung des Dreiecksbudgets, Z-Fighting oder Geometrie außerhalb der Collider

## Prüfungen

- Geometrie-Primitive sind als reine Python-Meshes validierbar.
- Neue Formen erzeugen positive Volumina und bleiben im vorhandenen Qualitätsmodell nutzbar.
- Die zehn `test_`-Typen bestehen den Modellvertrag und den CLI-Batch-Build mit Blender.
- Paket, CLI und Generator melden `0.10.2.5`.

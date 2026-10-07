# Cube Escape Generator – Version 0.10.2.4

## Überblick

Version 0.10.2.4 erweitert die Desktop-GUI um gerenderte und interaktive Modellvorschauen. Die bestehende Generator-
und Blender-Add-on-Oberfläche bleibt unverändert nutzbar.

## Änderungen gegenüber 0.10.2.3

### Modellvorschau in der Desktop-GUI

Die Modellvorschau ist ein eigenes Fenster, das sich über **Modellvorschau öffnen** aufrufen lässt und nach einem
erfolgreichen Build automatisch erscheint. Es listet die erzeugten Assets und zeigt Blender-Render neben einer
interaktiven 3D-Ansicht. Das Modell lässt sich per Ziehen drehen und mit dem Mausrad zoomen. Bei aktivem Blender
exportiert die GUI zusätzlich OBJ für den 3D-Viewer; mit `--no-blender` wird die OBJ-Datei des bestehenden Fallback-
Exports verwendet. Ohne Blender-Render bleibt die 3D-Ansicht verfügbar. Das Vorschaufenster passt seine Startgröße
an den Bildschirm an; beide Vorschauflächen wachsen beim Vergrößern mit, und das Renderbild wird passend skaliert.

## Prüfungen

- Die OBJ-Vorschau liest Geometrie, Materialfarben und ignoriert zusätzliche LOD1-Geometrie.
- Der GUI-Build stellt OBJ für die interaktive Ansicht bereit.
- Paket, CLI und Blender-Add-on melden `0.10.2.4`.

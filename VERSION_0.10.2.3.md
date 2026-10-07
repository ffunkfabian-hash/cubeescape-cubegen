# Cube Escape Generator – Version 0.10.2.3

## Überblick

Version 0.10.2.3 macht die drei priorisierten Verbesserungen in CLI und Desktop-Workflow nutzbar: explizite
Vorabprüfung mit vergleichbarer Variantenbewertung, inkrementelle OBJ-Builds und eine eigenständige GUI.
Bestehende Blender- und CLI-Workflows bleiben verfügbar.

## Änderungen gegenüber 0.10.2.2

### Vorabprüfung und Variantenbewertung

Validierungsreports weisen zusätzlich Score (0–100), Qualitätsmetriken, Rang innerhalb des Modelltyps und
Ähnlichkeit zu einer früheren Variante aus. Die Bewertung verwendet bestehende Dreiecks-, Draw-Call-,
Z-Fighting- und Collider-Prüfungen; Fehler und Warnungen bleiben separat sichtbar. `--strict` verhindert wie
bisher den Export, falls die Vorabprüfung Fehler oder Warnungen findet.

### Inkrementelle OBJ-Builds

Auch `--no-blender` prüft Build-Schlüssel und vorhandene Ausgabedateien vor dem Schreiben. Unveränderte OBJ-Assets
werden übernommen. Der Zielordner der Modelldateien ist Teil des Build-Schlüssels, damit ein geänderter
`--models-dir` neue Dateien am gewünschten Ort erzeugt. `--force` erzwingt weiterhin einen Neuaufbau.

### Eigenständige Desktop-GUI

`cubegen gui` und `cubegen-gui` starten eine Tkinter-Oberfläche. Sie unterstützt Modelltyp- und Rezeptauswahl,
Seeds, Variantenanzahl, Ausgabeordner, Ähnlichkeitsfilter, Qualitäts-Vorabprüfung und Exportstatus. Das Blender-
Add-on bleibt als 3D-Workflow bestehen.

## Prüfungen

- Qualitätsreport enthält Score, Severity und die einzelnen Prüfergebnisse.
- Validierungsreport rangiert Varianten deterministisch und meldet ähnliche Varianten.
- Wiederholte OBJ-Builds übernehmen unveränderte Assets; `--force` deaktiviert die Wiederverwendung.
- GUI-CLI-Befehl, Version und Dokumentation sind integriert.

## Technische Hinweise

- Paket- und CLI-Version: `0.10.2.3`
- Desktop-GUI verwendet Tkinter aus der Python-Standardbibliothek; manche Linux-Distributionen paketieren Tkinter
  separat.
- Blender- und OBJ-Build-Caches berücksichtigen Asset-Spezifikation, Export-/Textur-Einstellungen und
  Generator-Quellcode.

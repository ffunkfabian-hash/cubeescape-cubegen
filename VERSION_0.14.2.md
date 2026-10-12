# Cubegen 0.14.2 – Werkstattbuch

Release vom 12. Oktober 2026 (reiner Doku-Stand, Ausgabe unverändert). Release-Zweig `release/0.14.2`; vorherige
Version [0.14.1](VERSION_0.14.1.md).

## Inhalt

Prüfung, ob die Neural Engine Cubegen nützt – gemeinsam mit Roboter-Generator 1.9.2 (dort README › „Neural Engine –
geprüft“ mit allen Messwerten).

- **Messung (Seed 42, je 12 Varianten von `crate`, `door`, `console`, Vorschauen 256 px):** Apple Vision Feature Prints
  laufen standardmäßig auf der Neural Engine, 3,8 ms je Bild (GPU 15,8 ms, CPU 35,4 ms); 36 Vorschauen in 0,1 s.
  Dasselbe Bildpaar ergibt auf der Neural Engine 0,0026, auf der CPU 0,0003 – die Werte sind gerätabhängig und damit
  für Entscheidungen über ausgegebene Varianten (Reproduzierbarkeit) ungeeignet.
- **Nebenbefund:** Die engsten Paare der Feature Prints (`Door_003`/`Door_010` 0,11, `Console_000`/`Console_001`
  0,13) sehen fast gleich aus, gelten für `variety.similar` aber als verschieden – die Signatur verlangt exakt gleiche
  Dreieckszahlen (Türen: 420 gegen 408 Dreiecke, 5,66 gegen 5,26 m Breite). Die Abhilfe gehört deterministisch in die
  Signatur, nicht in eine Bildprüfung.
- **ROADMAP:** Signatur toleranter; Doubletten-Bericht und Icon-Lesbarkeit per Neural Engine nur als Hinweiswerkzeuge
  (macOS), jeweils mit Zeitregel – kosten sie zu viel Zeit, werden sie nicht umgesetzt.

Generator, Geometrie, Kollision, Materialien, Sidecar und Add-on-Logik sind unverändert; Golden-Daten unverändert.

## Prüfung

- `python3 -m unittest discover -s tests`: **262 Tests grün**, keiner übersprungen (Blender 5.2.2 und ImageMagick 7
  vorhanden), 256 s, am 12. Oktober 2026.

## Grenzen

- Gemessen nur an drei Typen mit je 12 Varianten; der Doubletten-Bericht über den ganzen Katalog ist noch nicht gebaut.

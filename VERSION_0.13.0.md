# Cubegen 0.13.0 – Patina

Release vom 10. Oktober 2026. Release-Zweig `release/0.13.0`; vorherige Version [0.12.0](VERSION_0.12.0.md).
Begleitet Cube Escape 0.35 „Prägung“, in dem Texturen ausdrücklich erlaubt werden.

## Inhalt

- **Texturen im Desktop-Fenster:** `cubegen gui` bietet jetzt die Auswahl **Texturen** (keine, Kacheln,
  Kacheln + Gebrauchsspuren, Farbpalette), die Texturgröße und – nur im Paletten-Modus – die Farbpalette. Die Argumente
  entstehen in `texture_args()` und sind dieselben wie bei `--textures`, `--texture-size` und `--palette`. Damit bieten
  Kommandozeile, Blender-Add-on, Desktop-Fenster und die Cube-Escape-Werkbank dieselbe Option. Standard bleibt
  „keine“ (einfarbige `M_…`-Materialien); Glow-/Status-, Glas- und Kristallmaterialien bleiben untexturiert.
- **AGENTS.md:** Abschluss in zwei Stufen (Stufe 1 „ungeprüft“ ohne Blender/Unity, Stufe 2 „abgenommen“ lokal) mit
  fester Vorlage für den lokalen Test-Prompt; Werkzeuge ImageMagick (Texturen, Gestalten, Bildprüfung) und das
  Blender-Plugin (MCP) als Prüfstand.

Generator, Geometrie, Kollision, Materialien, Sidecar und Add-on-Logik sind unverändert; Golden-Daten unverändert.

## Prüfung

- Neue Tests `tests/test_gui_textures.py`: keine Argumente ohne Textur, jede angebotene Art wird vom echten
  Kommandozeilen-Parser angenommen, Palette nur im Paletten-Modus, falsche Werte werden abgelehnt.

## Ergebnis

- `python3 -m unittest discover -s tests`: **262 Tests grün**, keiner übersprungen (Blender 5.2.2 und ImageMagick 7
  vorhanden), 254 s, am 10. Oktober 2026 auf dem Arbeitsstand. Keine Exporte nötig, weil sich die Ausgabe nicht ändert.

## Grenzen

- Das Desktop-Fenster selbst (Tk) ist nicht per Bild geprüft; geprüft ist die erzeugte Kommandozeile.

# Cubegen · verbindliche Arbeitsregeln für KI-Agenten

## Passende Kollision für jedes Modell

Jedes neue oder geänderte Modell braucht ein zur tatsächlichen Geometrie und Funktion
passendes Kollisionsrezept. Das gilt für Gameplay und statische Dekoration, intakte,
beschädigte und zerstörte Varianten, Parameterformen, LODs und bewegte Unterteile.
Ein erfolgreicher Export oder eine reine Prüfung der Bounds ist kein Physiknachweis.

- Feste Öffnungen und Zwischenräume bleiben frei. Eine Gesamtbox oder konvexe Hülle
  darf Käfige, Rohre, Tresore, Durchgänge oder Trümmerzwischenräume nicht auffüllen.
  Ein einfacher Box-/Hull-Collider ist nur für eine tatsächlich passende solide Form geeignet.
- Bewegte Teile und ihre Kinder tragen ihre Collider mit; Meshes unter bewegten
  Rigidbodies sind konvex. Feste komplexe Geometrie erhält genaue nichtkonvexe Meshes
  oder passend zerlegte einfache Shapes. Eine Schadenszone ersetzt keinen festen Collider.
- Rein visuelle Teile und Pickups werden ausdrücklich passend behandelt; Pickups
  behalten ihre Interaktionstrigger. Sichtbarkeit allein verlangt keine feste Kollision.
- Eigene vorhandene Shapes vor Änderungen prüfen. Generation 3 ergänzt fehlende
  Gameplay-/statische Shapes; ältere Generationen sind historische Ausgabe. Erhaltene
  alte Ausgabe niemals als korrigiert deklarieren. Alte fehlerhafte Exporte müssen
  mit dem aktuellen Rezept neu erzeugt und in Unity erneut geprüft werden.
- Dünne feste Teile (z. B. Stegstützen) zusätzlich durch tatsächliche Innenpunkte und
  exportierte Unity-Physik prüfen; Mindestvolumen-/Dickenfilter allein sind kein vollständiger Nachweis.
- Fehlende Kollisionsdeckung und blockierte Freiräume sind Fehler. Qualitätsprüfung
  muss den tatsächlichen Unity-Import abbilden, keine ersatzweise angenommene Hülle.
- Regressionen für Modelle, Seeds, Parameter und Zustände ergänzen. Bestehende Tests
  nicht löschen oder Importprüfungen lockern. Bei bewusster Änderung Golden-Daten
  gezielt aktualisieren und unveränderte Geometrie separat belegen.
- Python-Suite und echte FBX in der isolierten Cube-Escape-Testkopie prüfen:
  Geometrie-/Shape-Zuordnung, freie Öffnungen, bewegte Collider, Reimport und passende
  Laufzeit-/Physiktests. Kein Unity-Start auf einem Checkout.

Belegte Generatorfehler (Kollision, Geometrie, Export, Sidecar-/Metadaten) sofort beheben. Neue Befunde
gehören in den nächsten unveröffentlichten Versionsbericht `VERSION_<Version>.md`; Zielversion aus
Nutzerauftrag und Changelog ermitteln. 0.11.0 übernimmt das frühere 0.10.6-Vorhaben und besitzt den
Bericht `VERSION_0.11.0.md`. 0.12.0 (10. Oktober 2026) veröffentlicht die Arbeitsstände 0.11.1–0.11.4
(`VERSION_0.11.2.md` bis `VERSION_0.11.4.md`, Release-Bericht `VERSION_0.12.0.md`); neue Befunde gehören in
den nächsten offenen Bericht `VERSION_0.12.1.md` (bei Bedarf anlegen).
Veröffentlichte Berichte bleiben historisch.
Fund, Ursache, Korrektur, geprüfte Varianten und verbleibende Grenzen festhalten.
Diese Regel gilt auch in allen späteren Integrationsphasen.

## Ausrichtung gerichteter Modelle

Bei Kameras und anderen gerichteten Modellen die tatsächliche Funktionsfläche prüfen,
nicht nur die Objektrotation: Blender-/Unity-Achsen, Neigung und beide Schwenkvorzeichen
gegen die exportierte Geometrie testen. Ein Anker- oder Bounds-Test ersetzt keinen
Nachweis der Blickrichtung. Beabsichtigte Korrekturen gegenüber alten Generationen
ausdrücklich dokumentieren und historische Ausgaben getrennt prüfen.

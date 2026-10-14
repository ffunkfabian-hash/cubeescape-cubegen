# Cubegen 0.21.2 – Monolith

Korrektur vom 14. Oktober 2026, Release-Zweig `release/0.21.2`; vorherige Version [0.21.1](VERSION_0.21.1.md).
Nur ein Test; die Ausgabe ist unverändert.

## Fund

Nach dem Push von 0.21.1 war der GitHub-Job `blender` rot: `CrateRegressionTest` erwartete 8 Texturen, auf dem
Ubuntu-Runner waren es 9.

## Ursache

Die Kiste (Seed 4242, Kacheln) lädt 9 Karten. Mit ImageMagick 7 (lokal, auch beim Erzeugen der Cube-Escape-Fixture
`CrateTiled2048_000`) sind die Metall-/Rauheitskarten von `MT_HazardOrange` und `MT_Wall` bytegleich und zählen
einmal – 8. ImageMagick 6 auf dem Runner schreibt sie minimal verschieden – 9. Die Zählung selbst ist richtig; der Test
war zu streng.

## Korrektur

Der Test verlangt 8 mit ImageMagick 7 (wie die Fixture), sonst 8 oder 9, und in jedem Fall das Budget bei 2048 px
(9 Texturen = 50,3 MiB von 64 MiB).

## Prüfung

- `tests/test_release_0211.py` lokal grün; GitHub Actions nach dem Push geprüft.

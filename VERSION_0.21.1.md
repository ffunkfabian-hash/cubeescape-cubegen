# Cubegen 0.21.1 – Monolith

Korrektur vom 14. Oktober 2026, Release-Zweig `release/0.21.1`; vorherige Version [0.21.0](VERSION_0.21.0.md).

## Anlass

Cube Escape 0.51 „Tight Ship“ hat die drei Unity-Punkte aus 0.21.0 umgesetzt (ToDo 32–34) und darum gebeten, die
Budget-Schätzung im Generator an die neue Rechnung anzupassen: Die Warnung „texture memory … > 67108864“ aus 0.21.0
war für die Werkbank von 0.51 veraltet.

## Neue Rechnung (wie `CubegenTextures` in Cube Escape 0.51)

- Gezählt wird, was die Materialien des GLB laden: je verschiedene **(Rolle, Bildinhalt)** einmal. Gleiche PNG-Bytes
  in derselben Rolle laden einmal, auch wenn zwei Materialien sie nutzen; Albedo und Normalmap zählen getrennt, auch
  bei gleichem Bild.
- **Komprimiert:** BC3/DXT5, 1 Byte je Pixel, Mipmaps × 4/3 (0.21.0: RGBA32, 4 Bytes je Pixel).
- **Metall/Rauheit** wird zu einer Metall-/Glättekarte umgerechnet, die Quelle bleibt nicht liegen: zählt einmal.
- Grenzen unverändert: 64 MiB, höchstens 16 Texturen, höchstens 2048 px.

`contract.glb_summary` liefert dafür die geladenen Texturen (`textures`: Rolle, Inhalt, Größe), `texture_bytes`
rechnet komprimiert, `check_runtime_budget` zählt die Texturen und den Speicher daraus.

## Ergebnis

| Modell (Kacheln, 2048 px) | 0.21.0 | 0.21.1 | Cube Escape 0.51 |
|---|---|---|---|
| Kiste, Seed 4242 | 9 Bilder, 268 MB (Warnung) | 8 Texturen, 42,7 MB | 8 Texturen, 42,7 MB |
| Konsole, Seed 4242 | 201 MB (Warnung) | 9 Texturen, 48,0 MB | ~48 MB |

## Prüfung

- `tests/test_release_0211.py`: gleiche Bytes in gleicher Rolle einmal, andere Rolle zählt, Metall/Glätte als eigene
  Rolle; die Kiste (Seed 4242) hat 8 Texturen und passt bei 2048 px (schnell bei 256 px gebaut und hochgerechnet – die
  geteilten Karten hängen nicht von der Größe ab; der echte 2048er-Lauf mit `CUBEGEN_SLOW_TESTS=1`, unter Last
  über sechs Minuten, einmal lokal grün).
- `tests/test_release_0210.py`: die Erwartung der Formel bewusst angepasst (komprimiert statt RGBA32), das Test-GLB
  verweist seine Bilder jetzt über Materialien.
- `tools/run_tests.py` (volle Stufe, mit Blender und ImageMagick): **340 Tests grün** (127 s); Golden-Daten unverändert.

# Cubegen 0.28.0 – Clean Slate

Veröffentlicht am 15. Oktober 2026; Release-Zweig `release/0.28.0`; vorherige Version [0.27.0](VERSION_0.27.0.md).
Nur ein Test; kein Generator-Code, keine Ausgabe geändert – nur die Versionsangabe im Sidecar.

## Fund

`tests/test_release_0160.py` › `OverlapTest.test_blender_starts_while_the_textures_are_built` scheitert mit
`python3 -m unittest discover -s tests` (auch auf `main`), sobald der gemeinsame Blender-Ergebnis-Cache (seit 0.26.0,
`cubegen/modelcache.py`) seed 3 `crate,door` mit denselben Einstellungen enthält: `len(timings["workers"])` ist 0
statt 2. Gefunden beim Testlauf für 0.26.2; mit `CUBEGEN_CACHE=0` grün.

## Ursache

Der Test prüft, dass Blender startet, während die Texturen entstehen, nutzte aber den Cache des Rechners. Bei einem
Treffer kommen Export und Karten aus dem Cache, ein Blender-Worker startet zu Recht nicht. `tools/run_tests.py`
setzt je Lauf einen frischen Cache, doch auch dort teilen sich alle Gruppen eines Laufs denselben – ein früherer Test
mit gleichem Auftrag hätte ihn ebenso füllen können.

## Korrektur

Der Test läuft mit einem eigenen, leeren `CUBEGEN_CACHE`-Ordner (`mock.patch.dict`, Muster von `BakeTest` in
`tests/test_release_0150.py`). Das Cache-Verhalten bleibt unverändert.

Weitere Blender-Tests mit derselben Annahme gesucht (Prüfungen auf `workers`, `worker_seconds`, `process(es)`,
Blender-Logzeilen): `BakeTest` (0150) läuft schon mit `CUBEGEN_CACHE=0`, die Cache-Tests in 0250/0260 setzen ihren
eigenen Speicher und erwarten Treffer, `test_pipeline` erwartet ausdrücklich keinen Blender-Start. Empirisch: volle
Suite zweimal hintereinander mit dem warmen Cache des Rechners (siehe Prüfung).

## Prüfung

- Vorher auf `main` mit warmem Rechner-Cache (1672 Einträge): `OverlapTest` rot, `AssertionError: 0 != 2`.
- Nachher `OverlapTest` zweimal hintereinander grün (je rund 1–1,5 s, Blender startet zwei Worker).
- `python3 -m unittest discover -s tests` zweimal hintereinander mit dem Cache des Rechners: je 442 Tests, OK,
  15 übersprungen (numpy fehlt im System-Python, `CUBEGEN_SLOW_TESTS`/`CUBEGEN_UNITY_CHECK` nicht gesetzt); 257 s und 273 s.

# Cube Escape Generator – Version 0.10.2.2

## Überblick

Version 0.10.2.2 baut auf 0.10.2.1 auf und ergänzt die Qualitäts- und Family-Validierung um
explizite, auditierbare Abläufe. Bestehende Export-Workflows bleiben standardmäßig unverändert.

## Änderungen gegenüber 0.10.2.1

### Sichere Reparaturen

`Asset.repair_safe()` entfernt ausschließlich leere Mesh-Objekte, die weder Parent eines anderen
Objekts noch in Behaviours oder Collidern referenziert sind. Die Bereinigung ist über
`generate --repair-safe` optional; protokollierte Reparaturen erscheinen im Asset-Metadatenfeld
`safe_repairs`. Verwaiste Hierarchie- oder Script-Referenzen werden nicht stillschweigend umgebogen.

### Severity-Stufen

Qualitätsprüfungen liefern nun `pass`, `warning` oder `error`. Fehler und Warnungen bleiben als
separate Listen abrufbar. `generate --strict` lässt den Export bei Qualitätswarnungen nicht starten;
der Standardmodus und `--relaxed` lassen Warnungen zu.

### Family-Kompatibilitätsmatrix

`compatibility_matrix()` fasst Connector-Prüfungen für jedes Asset-Paar einer Kit-Familie zusammen.
Jedes Paar wird als `compatible`, `incompatible` oder `no_matching_connector` ausgewiesen. Die
Matrix wird im Family-Check ausgegeben und ist auch im Familienabschnitt des Build-Manifests enthalten.

### Build-Metadaten und Reports

Das Build-Manifest enthält jetzt einen UTC-Zeitstempel, einen Hash des Generator-Quellcodes und pro
Asset einen SHA-256-Hash über Geometrie, Pivots, Materialien, Colliders, Behaviour-Wiring und Metadaten.
`--report FILE` schreibt Manifest oder Validierungsreport separat als JSON.

### CLI-Validierung ohne Export

`generate --validate-only` baut und prüft die geplanten Assets in Python, ohne Blender zu starten oder
Modelldateien zu exportieren. Der Report enthält Severity, Fehler, Warnungen, Asset-Hashes und Family-
Kompatibilität. `--dry-run` bleibt für die bisherige kurze Vorschau erhalten.

## Prüfungen

- Sichere Reparatur entfernt ausschließlich unreferenzierte leere Meshes.
- Severity-Klassifikation und Strict-/Relaxed-Verhalten.
- Family-Matrix für passende, unpassende und nicht verbundene Asset-Paare.
- Validierungsreport ohne Blender-Export sowie Metadaten im regulären Manifest.
- Vorhandene Regressionstests aus 0.10.2.1.

## Technische Hinweise

- Paket- und CLI-Version: `0.10.2.2`
- Die neuen Reparatur- und Strict-Verhaltensweisen sind opt-in.
- Der bisherige `--dry-run` bleibt unverändert.

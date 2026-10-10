# Cubegen 0.11.1 · Korrekturen aus der Unity-Integration (unveröffentlicht)

> **Veröffentlicht mit 0.12.0** (10. Oktober 2026, Release-Zweig `release/0.12.0`, Bericht [VERSION_0.12.0.md](VERSION_0.12.0.md)).
> Die Angaben unten beschreiben den damaligen Arbeitsstand.

Stand: 8. Oktober 2026. Offener Bericht für die nächste Patch-Version nach 0.11.0. Paket, CLI und
Add-on stehen weiterhin auf 0.11.0; die Versionsnummer wird erst mit der ersten Korrektur angehoben.

## Auftrag (gilt für alle folgenden Integrationsphasen)

Belegte Fehler des Generators werden sofort im Generator behoben – mit Regressionstest, gezieltem
Reexport und erneutem echten Unity-Audit in der Cube-Escape-Testkopie. Jeder Fund wird hier mit
Fund, Ursache, Korrektur, geprüften Varianten und verbleibenden Grenzen eingetragen. Fehler in
Cube Escapes eigener Importlogik werden dort behoben und nur als Abgrenzung erwähnt.

## Korrekturen

Noch keine.

## Integrationsprüfungen ohne Generatorbefund

### Cube Escape · Modell-Browser der Werkbank (8. Oktober 2026)

- Geprüft: alle 49 Katalogeinträge mit Tag `cubegen` als Vorschaubilder (Kontaktbogen) und in der neuen
  3D-Vorschau des Browsers; Herkunftserkennung über den Sidecar-/Metadaten-Tag `cubegen`.
- Ergebnis: kein Generatorfehler. Der orange Kasten an `Gen_Phase4_SteamVent_000/001` ist Cube Escapes
  eigenes Reichweitenvolumen (`_CubegenSteamVolume`, Werkbank-Vorschau, im Spiel ausgeblendet), kein
  sichtbar exportierter `FX_Steam`-Anker.
- Abgrenzung in Cube Escape: Schwenkkameras und -geschütze (Phase 3, `sweep`) übernehmen den Vertrag einer
  Signallampe und stehen deshalb in der Kategorie „Beleuchtung“; Anzeigenamen mit Laufnummer
  („Cubegen-Bodenklappe 000“) stammen aus den Cube-Escape-Profilen. Beides ist keine Generatoraufgabe.

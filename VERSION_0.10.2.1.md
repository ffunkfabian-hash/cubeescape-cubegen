# Cube Escape Generator – Version 0.10.2.1
## Überblick

Diese Version ist eine gezielte Qualitäts- und Stabilitäts-Verbesserung auf Basis der konkreten Vorschläge für den Generator. Sie baut auf dem vorhandenen 0.10.2-Stand auf und fügt drei zentrale Sicherheits-/Qualitätsmechanismen hinzu:

- strenge Asset-Contract-Validierung
- Familie-/Kit-Kompatibilitätsprüfung
- kompakte Qualitätsbewertung pro Asset

## Änderungen gegen 0.10.2

### 1. Strengere Asset-Contract-Validierung

Die Asset-Generierung validiert nun den erzeugten Inhalt vor dem Export und vor der Integration in Familien-/Kit-Recipes. Dabei werden automatisch geprüft:

- doppelte Objektnamen im selben Asset
- Parent-Verweise auf nicht vorhandene Objekte
- leere Mesh-Objekte ohne faces
- fehlerhafte Unity-Behaviour-Verknüpfungen
- Collider, die auf nicht existente Teile verweisen

Diese Prüfungen sind in `cubegen/asset.py` als `Asset.validate_contract()` eingebaut und werden beim normalen `generate_asset()` automatisch aufgerufen.

### 2. Familie-/Kit-Kompatibilitätsprüfung

Für Family-Recipes und Kit-Definitionen gibt es nun eine dedizierte Validierungshilfe in `cubegen/families.py`:

- `validate_family_recipe(recipe, ...)`
- prüft die in der Familie enthaltenen Typen beim Build
- validiert den Asset-Contract jedes Modells
- erkennt fehlende Connector-Informationen für wichtige Bau-Teile wie Wand, Tür, Plattform, Catwalk, Ramp, Treppe und Rohr

Damit wird ein wichtiger Teil der zuvor beschriebenen “kit compatibility”-Verbesserung direkt in den Generator eingebaut, statt nur als manuelle Regel im Dokument zu verbleiben.

### 3. Qualitätsbewertung pro Asset

In `cubegen/quality.py` wurde `asset_quality_report()` ergänzt. Diese Funktion liefert eine kompakte Zusammenfassung mit:

- Triangle Count
- Draw Calls
- Anzahl z-fighting-Paare
- Anzahl unbedeckter Geometriebereiche
- Qualitäts-Score
- Boolesche Pass/Fail-Flags

Das schafft eine sinnvolle Grundlage für CI-, UI- und nachgelagerte Review-Prozesse, ohne die bestehende Qualitätslogik zu ersetzen.

## Warum diese Version?

Der Generator war bereits funktional stark und reproduzierbar. Die größte Schwachstelle war nicht mehr “Funktionalität”, sondern “Verlässlichkeit im Pipeline-Lauf und in der Kit-Kompatibilität”. Diese Version verbessert genau dieses Problemfeld.

## Technische Hinweise

- Versionsnummer: `0.10.2.1`
- Neuer Code ergänzt bestehende Sprünge, ohne die Laufzeit-Pipelines bestehender Assets zu verändern.
- Die Änderungen sind bewusst so gestaltet, dass bestehende Generator-Workflows kompatibel bleiben.

## Geprüfte Umsetzung

Die neue Version wurde mit gezielten Tests validiert, darunter:

- Asset-Contract-Prüfung
- Qualitätsreport
- Family-Recipe-Validierung

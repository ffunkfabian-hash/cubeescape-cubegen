# Cubegen 0.10.4.1 · Arbeits- und Prüfbericht

Ausgangspunkt ist die Kopie des 0.10.4-Projekts. Diese Arbeitskopie liegt unter
`Cubegen_v0.10.4.1`; Git-Metadaten und Finder-`.DS_Store`-Dateien wurden nicht übernommen.
Paket, CLI und Blender-Add-on melden 0.10.4.1.

## Clutter-/Accessoire-Pass

- `Style.clutter` und `generate --clutter none|clean|lived-in|chaotic` ergänzen einen
  seed-deterministischen Pass. Rezepte verwenden `style.clutter`; das Blender-Add-on hat
  dieselben vier Dichte-/Off-Werte, übernimmt standardmäßig die Rezept-/Familienvorgabe
  und gibt explizite CLI-Overrides weiter.
- Die erste unterstützte Fläche ist die Oberseite von intakten `table`- und `lab`-Tischen.
  Andere Typen und Tisch-Varianten ohne explizit definierte sichere Fläche bleiben
  unverändert. Es gibt bewusst keine automatische Flächenerkennung.
- Kleine `tool`-, `spare_part`- und `keycard`-Modelle werden geometrisch auf die Fläche
  gelegt und als eigene `Clutter_*`-Mesh-Objekte in der jeweiligen Exportdatei gehalten.
  Sie werden nicht mit dem Host-Mesh verschmolzen. Die Registry-Typen lassen sich
  weiterhin separat erzeugen/exportieren.
- Der Generator verwendet unabhängige Seed-Ableitungen pro Fläche und Prop. Eine
  zusätzliche Accessoire-Platzierung verschiebt daher keine vorhandenen Modell-Rolls.
- Jeder Platz wird anhand der gedrehten Prop-Bounding-Box geprüft: Prop muss innerhalb
  der markierten Rechteckfläche liegen und einen Mindestabstand zu bereits gesetzten
  Props einhalten. Versuche ohne gültigen Platz werden gezählt und in
  `clutter_pass.skipped` im Sidecar sichtbar gemacht.
- Wenn der Pass aktiv ist, ersetzt er den älteren, in die Tischgeometrie gebackenen
  Kleinkram. `table.clutter=true` gleichzeitig mit globalem Pass wird auf unterstützten
  Varianten explizit abgelehnt statt stillschweigend überschrieben. Bei `clutter=none`
  bleibt das bisherige Verhalten erhalten.
- Für Kombinationen mit `damage != intact` wird eine klare Style-Validierungsfehlermeldung
  ausgegeben; beschädigte Oberflächen werden nicht als sicher angenommen.

## Bekannte Grenzen / offene Punkte

- Die Flächendeklarationen sind aktuell für einfache rechteckige Tischflächen ausgelegt.
  Runde Tische, Schreibtische mit festem Monitor/Keyboard sowie Regalböden sind noch nicht
  freigegeben.
- Die Überlappungsprüfung betrifft Props, die der Pass selbst setzt. Später ergänzte
  eingebaute Details müssen entweder bei der Flächendeklaration ausgespart oder ebenfalls
  als Hindernisse beschrieben werden.
- Die Prüfung verwendet achsenparallele Bounding-Boxen nach Drehung; sie ist absichtlich
  konservativ und kann freie Fläche ungenutzt lassen. Sie garantiert keinen semantisch
  sinnvollen Griff-/Interaktionsabstand in Unity.
- Der Pass ist noch nicht als echter Unity-Laufzeitnachweis dokumentiert. Er erzeugt
  eigenständige FBX-Mesh-Objekte, weist ihnen aber keine Gameplay-Scripts oder Collider zu.
- Die bisherige Ziel-Dichte ist eine einfache Fläche-mal-Profil-Heuristik mit Obergrenze,
  keine prozentuale Flächenbelegung. Zusätzliche Host-Oberflächen sollten erst nach
  Regressionen für Randabstände, Kollisionen und Export dazukommen.
- `Style.clutter` plus `damage != intact` wird absichtlich abgelehnt, auch wenn ein Batch
  gerade keinen Tisch enthält; die Einstellung ist global und soll nicht auf einzelnen
  Typen stillschweigend ignoriert werden.

## Verifizierungsprotokoll

- Clutter-Regressionsgruppe: 7 Tests, deterministischer Digest, unverändertes Verhalten
  bei `clutter=none`, getrennte Einzeltypen, Flächen-/Abstandsprüfung und Fehlerfälle.
- Die vollständige Suite besteht aus **178 Tests** (41 Modell-, 12 Qualitäts- und 125
  übrige Tests); alle drei Gruppen sind grün. Die Modell-Golden bleiben unverändert.
- Versionsprüfung: Paket, CLI, Add-on-Metadaten und tatsächlich gebautes Add-on-Bundle
  melden einheitlich 0.10.4.1; Add-on-Rauchtest in isolierter Blender-Umgebung endet mit
  `ADDON_SMOKE_OK` (175 Typen im Raster und Export, Accessoire-Option geprüft).
- CLI-Vorabprüfung für drei Tischvarianten mit Seed 42 und `--clutter lived-in`:
  `validation: pass (3 asset(s))`.
- Echter Blender-5.2.2-FBX-Export `Table_000` mit zwei Accessoire-Gruppen: vier eigene
  `Clutter_*`-Mesh-Parts in FBX/Sidecar; `cubegen check --export` meldet 1 Modell,
  0 Ablehnungen und 0 offene Item-Zuordnungen.
- Erster Rand-/Höhentest verglich Geometrie mit auf vier Dezimalstellen gerundeten
  Sidecar-Flächenangaben strenger als deren dokumentierte Präzision. Die Assertions
  verwenden jetzt eine Toleranz von 0,1 mm; die Geometrie musste nicht geändert werden.
- Der externe Unity-Importer/Laufzeittest wurde nicht ausgeführt; `check --export` ist
  ausschließlich die lokale Vertragsprüfung und kein Unity-Importnachweis.
- Ein Volltestlauf fand nach manueller Erläuterung der generierten README-Parametertabelle
  eine Abweichung. Die Tabelle wurde mit `tools/param_table.py --write` neu erzeugt;
  der abschließende Volltestlauf besteht danach in allen drei Gruppen.

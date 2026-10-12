---
name: golden-daten
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: tests/(golden\.json|golden_cases\.py|quality_baseline\.json)$
---

**Golden-Daten nur gezielt aktualisieren:** bei bewusster Änderung genau die betroffenen Modelle, Seeds und Zustände
anpassen und unveränderte Geometrie separat belegen; keine Prüfungen lockern, keine Tests löschen (AGENTS.md ›
Passende Kollision).

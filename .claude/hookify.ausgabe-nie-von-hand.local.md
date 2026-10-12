---
name: ausgabe-nie-von-hand
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: /output/
---

**Generierte Ausgabe nicht von Hand ändern:** Exporte, Sidecars und Texturen entstehen nur durch den Generator. Fehler
im Generator beheben und neu erzeugen; alte Ausgabe nie als korrigiert erklären (AGENTS.md › Passende Kollision).

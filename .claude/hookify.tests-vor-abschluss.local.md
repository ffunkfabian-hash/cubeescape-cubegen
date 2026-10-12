---
name: tests-vor-abschluss
enabled: true
event: stop
action: block
conditions:
  - field: transcript
    operator: regex_match
    pattern: "name":"(Edit|Write|MultiEdit)","input":\{"file_path":"[^"]*\.py"
  - field: transcript
    operator: not_contains
    pattern: tests in
---

**Python geändert, aber die Suite lief nicht:** vor dem Abschluss `python3 -m unittest discover -s tests` ausführen
(ohne Blender/ImageMagick übersprungene Tests im Bericht nennen; AGENTS.md › Abschluss in zwei Stufen).

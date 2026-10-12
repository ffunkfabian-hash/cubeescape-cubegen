---
name: unity-nie-auf-checkout
enabled: true
event: bash
action: block
conditions:
  - field: command
    operator: regex_match
    pattern: -projectPath\s+["']?(/Users/ffunk/Claude/Cube Escape|\S*\.codex/worktrees)
---

**Unity nie auf einem Checkout starten** (Cube-Escape-AGENTS.md › Arbeitsumgebung). Der Nutzer hat den Editor meist auf dem
Haupt-Checkout offen; Worktrees sind ebenfalls Checkouts. Unity läuft nur in der Testkopie:
`verify.sh` im Cube-Escape-Repository (Skill `ce-testing` bzw. `ce-cubegen` dort); Cubegen-AGENTS.md › Passende Kollision.

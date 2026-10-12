---
name: git-nur-auf-wunsch
enabled: true
event: bash
action: warn
conditions:
  - field: command
    operator: regex_match
    pattern: \bgit\s+(-C\s+("[^"]*"|'[^']*'|\S+)\s+)?(commit|push|merge|tag\s+-a|tag\s+v)\b
---

**Release, Merge, Tag und Push nur auf Wunsch des Nutzers** (AGENTS.md › Versionen, Branches und Worktrees).
Nachricht auf Deutsch („Cubegen <Version> – …“); Release: Datum statt „unveröffentlicht“, Tests grün,
`git merge --no-ff` in `main`, Tag `v<Version>`, Push von `main`, `release/<Version>` und Tag ohne `--force`.

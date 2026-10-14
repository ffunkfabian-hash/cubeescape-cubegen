---
name: actions-sparsam
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.github/workflows/[^/]+\.ya?ml$
---

**GitHub Actions sparsam** (~/.claude/CLAUDE.md und AGENTS.md › „GitHub Actions sparsam“; 2.000 min/Monat, Budget 0 $ – leer heißt: keine
Läufe bis zum Monatsanfang): `push` nur auf `main`, sonst über den PR; `concurrency` mit `cancel-in-progress`;
`paths-ignore` für Doku; wenige volle Jobs statt einer Job-Matrix je Testgruppe; volle Python-Matrix nur auf `main`
und auf Wunsch; `timeout-minutes` an jedem Job. Neuer Job/Workflow: Minuten je Lauf × Läufe im Monat im Bericht schätzen.

---
name: versionen-gemeinsam
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: (pyproject\.toml|cubegen/__init__\.py|cubegen_addon/__init__\.py)$
  - field: content
    operator: regex_match
    pattern: version
---

**Version überall gemeinsam anheben:** `pyproject.toml`, `cubegen/__init__.py` und `bl_info` in
`blender_addon/cubegen_addon/__init__.py`, dazu das Add-on-ZIP neu bauen (`tools/build_addon.py`);
`tests/test_versions.py` prüft die Gleichheit (AGENTS.md › Versionen, Branches und Worktrees).

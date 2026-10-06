"""The "Parameter pro Typ" table of README.md, generated from the model registry.

    python3 tools/param_table.py            ->  print the table
    python3 tools/param_table.py --write    ->  replace it in README.md (between the params markers)

tests/test_params.py fails when README.md and the registry disagree, so a new type or parameter
can't be forgotten in the README.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
BEGIN, END = "<!-- params:begin -->", "<!-- params:end -->"

sys.path.insert(0, ROOT)


def _num(x) -> str:
    return f"{x:g}"


def _describe(p) -> str:
    if p.kind == "choice":
        values = " / ".join(str(c) for c in p.choices)
    elif p.kind == "bool":
        values = "ja/nein"
    elif p.kind == "text":
        values = "Text"
    else:
        values = f"{_num(p.lo)}–{_num(p.hi)}"
    if p.default is not None and p.kind != "bool":
        values += f", Standard {p.default if p.kind in ('choice', 'text') else _num(p.default)}"
    return f"`{p.name}` ({values}){' 🔗' if p.unity else ''}"


def table() -> str:
    from cubegen.models import REGISTRY

    rows = ["| Typ | Parameter (Wertebereich; 🔗 = Wert für ein Unity-Script) |", "|---|---|"]
    for name, entry in sorted(REGISTRY.items()):  # alphabetical: easy to find
        if entry.params:
            rows.append(f"| `{name}` | {', '.join(_describe(p) for p in entry.params)} |")
    return "\n".join(rows)


def readme_table(text: str) -> str:
    start, end = text.index(BEGIN) + len(BEGIN), text.index(END)
    return text[start:end].strip("\n")


def write() -> None:
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    start, end = text.index(BEGIN) + len(BEGIN), text.index(END)
    with open(README, "w", encoding="utf-8") as fh:
        fh.write(text[:start] + "\n" + table() + "\n" + text[end:])


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
        print(f"{README}: parameter table updated")
    else:
        print(table())

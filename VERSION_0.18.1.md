# Cubegen 0.18.1 – Chameleon

Korrektur vom 13. Oktober 2026, Release-Zweig `release/0.18.1`; vorherige Version [0.18.0](VERSION_0.18.0.md).

## Fund

Erster echter Lauf des Nutzers nach dem Release:
`cubegen generate --types test_wall_modules --count 5 --set --param test_wall_modules.dressing=organic --paint organic`.
Set und Umriss stimmen (`outline_ok`, 0 mm), aber der Leuchtschlitz der Akzentsäule leuchtet **orange**, obwohl
Organic Cyan als Leuchtfarbe hat (Manifest `config.style.glow = cyan`).

## Ursache

`test_wall_modules` setzte den Schlitz fest auf `M_GlowOrange`. Der Stiltest (`tools/style_test.py`) färbt
Leuchtteile beim Rendern selbst in die Themenfarbe um – deshalb sahen alle Vergleichsbilder von 0.17.0 und 0.18.0
richtig aus, der echte `--paint`-Weg aber nicht.

## Korrektur

- `ParamReader.glow_or(default)`: die Leuchtfarbe des Stils (`--glow`, Thema) ohne Würfelwurf, sonst `default` – der
  Zufallsstrom und damit jede bestehende Variante bleibt gleich.
- Der Schlitz nutzt `a.p.glow_or("M_GlowOrange")`. Ohne Vorgabe bleibt er orange.
- Regel in AGENTS.md › „Anstriche“: Leuchtfarben auch in einem echten `--paint`-Lauf prüfen, Leuchtteile nie fest färben.

## Prüfung

- `tests/test_release_0181.py`: Organic → `M_GlowCyan`, Dark → `M_GlowRed`, `--glow red` → `M_GlowRed`, ohne Vorgabe
  `M_GlowOrange` (Seed des Nutzers, 5 Varianten als Set).
- Golden-Daten: nur `test_wall_modules` in den Fällen mit Leuchtvorgabe (`themed`, `gen1_themed`, `gen2_themed`),
  alle übrigen Fälle und Typen unverändert.
- Befehl des Nutzers mit 0.18.1 wiederholt: drei Leuchtschlitze, alle `M_GlowCyan`; Set-Reihenbild angesehen.
- `tools/run_tests.py` (volle Stufe): **304 Tests grün** (105 s).

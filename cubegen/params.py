"""Parameters: fix single properties of a model instead of rolling them from the seed.

Every builder reads its tunable values through a :class:`ParamReader`. The
reader ALWAYS consumes the random generator exactly like an unparameterised
roll would and only then applies an override. So fixing one parameter changes
that one property - the rest of the variant stays as the seed made it, and
models without overrides are bit-identical to earlier versions.

Two kinds of settings:

* per-type parameters, declared on the model type (``door.style``,
  ``wall.length`` ...), set with ``--param door.style=airlock``
* global :class:`Style` settings for all types (size class, grid snapping,
  glow colour, material style, warning paint, wear, detail level)

A *theme* (``Style.theme``, any text) rolls glow colour, material style, wear
and warning paint once for the whole batch, so all assets of a room match.
Settings given explicitly win over the theme.
"""

from __future__ import annotations

import contextvars
import difflib
from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, Optional, Sequence, Tuple

GLOW = {"cyan": "M_GlowCyan", "red": "M_GlowRed", "orange": "M_GlowOrange"}
MATERIAL_STYLES = {
    "metal": ("M_Metal",),
    "wall": ("M_Wall",),
    "dark": ("M_RobotDark",),
    "light": ("M_Platform", "M_RobotBody"),
}
SIZE_CLASSES = {"S": (0.0, 1 / 3), "M": (1 / 3, 2 / 3), "L": (2 / 3, 1.0)}
DAMAGE_STATES = ("intact", "damaged", "destroyed", "fractured")


#: model generations - what changed in each (existing seeds keep their look within a generation):
#: 1 = cubegen 0.9.0; 2 = flush details lifted 2 mm (no z-fighting), two materials per moving part;
#: 3 = empties for sound and effects (Audio_*, FX_*: models/anchors.py); damaged models knock nothing off the
#: parts Unity builds colliders from (a door frame piece on the floor blocked the passage); colliders for solid
#: pieces that had none (crusher cylinder, island crystals, fill under stair ramps, big knocked-off pieces) -
#: else as in 2
GENERATIONS = (1, 2, 3)
LATEST_GENERATION = GENERATIONS[-1]


@dataclass
class Style:
    """Global look settings - ``None`` / ``"seed"`` means: as the seed rolls it.

    ``generation`` picks the model generation: corrections that change existing seeds (2: flush details lifted
    against flickering, two materials per moving part; 3: anchors for sound and effects) only apply from their
    generation on, so a batch exported with an older cubegen can be rebuilt bit for bit with ``generation`` 1 or 2.
    """

    size: Optional[str] = None       # S | M | L  -> picks from the lower / middle / upper third of size ranges
    snap: float = 0.0                # round main dimensions to multiples of this (m), 0 = off
    glow: Optional[str] = None       # cyan | red | orange for decorative glow (status parts keep their state colour)
    material: Optional[str] = None   # metal | wall | dark | light - preferred body material where it is an option
    warning: Optional[str] = None    # none | always - warning stripes / bands
    wear: Optional[str] = None       # none | light | heavy - rubble, loose plates, torn cables (None = none / theme)
    detail: str = "normal"           # low (no bevels, fewer sides) | normal | high (rounder cylinders)
    damage: str = "intact"           # intact | damaged | destroyed (ruin: static, no scripts) | fractured
    theme: Optional[str] = None      # any text: rolls glow, material, wear and warning once for all assets
    generation: int = LATEST_GENERATION  # model generation (GENERATIONS): 1 = as cubegen 0.9.0, 2 = without anchors

    def validate(self) -> None:
        checks = [
            ("size", self.size, (None, "S", "M", "L")),
            ("glow", self.glow, (None, *GLOW)),
            ("material", self.material, (None, *MATERIAL_STYLES)),
            ("warning", self.warning, (None, "none", "always")),
            ("wear", self.wear, (None, "none", "light", "heavy")),
            ("detail", self.detail, ("low", "normal", "high")),
            ("damage", self.damage, DAMAGE_STATES),
        ]
        for name, value, allowed in checks:
            if value not in allowed:
                raise ValueError(f"style {name}: {value!r} not in {', '.join(str(a) for a in allowed if a)}")
        if self.generation not in GENERATIONS:
            raise ValueError(f"style generation: {self.generation!r} not in {', '.join(map(str, GENERATIONS))}")
        if self.snap < 0:
            raise ValueError("style snap must be >= 0")
        if self.theme is not None and not str(self.theme).strip():
            raise ValueError("style theme must not be empty")

    def resolved(self) -> "Style":
        """The style the builders use: theme rolls filled into the settings left open, wear None -> none."""
        style = self
        if self.theme is not None:
            rolled = theme_style(self.theme)
            style = replace(self, **{k: v for k, v in rolled.items() if getattr(self, k) is None})
        if style.wear is None:
            style = replace(style, wear="none")
        return style

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Style":
        data = {k: v for k, v in (data or {}).items() if v not in ("", "seed")}
        fields = list(cls.__dataclass_fields__)
        for key in data:
            if key not in fields:
                close = difflib.get_close_matches(key, fields, n=1)
                hint = f" (did you mean {close[0]!r}?)" if close else ""
                raise ValueError(f"style: unknown key {key!r}{hint}; allowed: {', '.join(fields)}")
        if "generation" in data:  # "1" from the command line / add-on
            try:
                data["generation"] = int(data["generation"])
            except (TypeError, ValueError):
                raise ValueError(f"style generation: {data['generation']!r} is not a number") from None
        return cls(**data)


def theme_style(theme) -> Dict[str, Optional[str]]:
    """What a theme rolls (always all four, in this order - fixing one setting never changes the others)."""
    from .seeds import StableRandom, derive_seed

    rng = StableRandom(derive_seed(0, "theme", str(theme).strip()))
    return {
        "glow": rng.choices(["cyan", "red", "orange"], weights=[5, 2, 3])[0],
        "material": rng.choice(["metal", "wall", "dark", "light"]),
        "wear": rng.choices(["none", "light", "heavy"], weights=[5, 3, 2])[0],
        "warning": rng.choices([None, "none", "always"], weights=[6, 2, 2])[0],  # None: every asset rolls
    }


@dataclass
class Param:
    """A tunable property of a model type (used for CLI help, add-on fields and validation)."""

    name: str
    kind: str                      # float | int | choice | bool | text
    label: str                     # German UI label
    description: str = ""
    lo: Optional[float] = None     # float / int: allowed override range
    hi: Optional[float] = None
    choices: Tuple = ()            # choice: allowed values
    size: bool = False             # float: affected by Style.size / Style.snap
    snap_factor: float = 1.0       # radius = 2: snap the diameter, not the radius
    unity: bool = False            # value of a game script (goes to <Name>.cubegen.json)
    default: Any = None            # for options that are not rolled (e.g. Unity values)
    # option: only recorded in "params" when set (variants added later: the default builds the model as
    # before, its params stay unchanged)
    quiet: bool = False

    def parse(self, value: Any) -> Any:
        """Convert a CLI / recipe / UI value and check it."""
        if self.kind == "text":
            text = str(value).strip()
            if not text or len(text) > 100 or any(ord(c) < 32 for c in text):
                raise ValueError(f"{self.name}: expected a text of 1-100 characters, got {value!r}")
            return text
        if self.kind == "bool":
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in ("1", "true", "yes", "ja", "on", "an"):
                return True
            if text in ("0", "false", "no", "nein", "off", "aus"):
                return False
            raise ValueError(f"{self.name}: expected true/false, got {value!r}")
        if self.kind == "choice":
            for choice in self.choices:
                if str(choice) == str(value).strip() or choice == value:
                    return choice
            raise ValueError(f"{self.name}: {value!r} not in {', '.join(str(c) for c in self.choices)}")
        number = float(value)
        if self.kind == "int":
            if number != int(number):
                raise ValueError(f"{self.name}: expected a whole number, got {value!r}")
            number = int(number)
        if (self.lo is not None and number < self.lo) or (self.hi is not None and number > self.hi):
            raise ValueError(f"{self.name}: {number} outside {self.lo} .. {self.hi}")
        return number

    def describe(self) -> str:
        if self.kind == "choice":
            rng = " | ".join(str(c) for c in self.choices)
        elif self.kind == "bool":
            rng = "true | false"
        elif self.kind == "text":
            rng = "TEXT"
        else:
            rng = f"{self.lo:g} .. {self.hi:g}"
        tags = " [Unity]" if self.unity else ""
        return f"{self.name:<14} {rng:<46} {self.label}{tags}"


# detail level of the asset currently being built (per thread / context)
DETAIL: contextvars.ContextVar = contextvars.ContextVar("cubegen_detail", default="normal")


class ParamReader:
    """Rolls values like the plain ``random.Random`` calls did, then applies overrides and style."""

    def __init__(self, rng, specs: Sequence[Param], overrides: Optional[Dict[str, Any]] = None,
                 style: Optional[Style] = None):
        self.rng = rng
        self.specs = {p.name: p for p in specs}
        self.style = style or Style()
        self.overrides: Dict[str, Any] = {}
        for name, value in (overrides or {}).items():
            if name not in self.specs:
                raise KeyError(f"unknown parameter {name!r}; available: {', '.join(self.specs) or '-'}")
            self.overrides[name] = self.specs[name].parse(value)
        self.used: Dict[str, Any] = {}

    def _spec(self, name: str) -> Param:
        if name not in self.specs:
            raise KeyError(f"builder uses undeclared parameter {name!r}")
        return self.specs[name]

    def _result(self, name: str, rolled: Any) -> Any:
        value = self.overrides.get(name, rolled)
        self.used[name] = value
        return value

    # -- rolled values ------------------------------------------------------------
    def float(self, name: str, lo: float, hi: float) -> float:
        spec = self._spec(name)
        value = self.rng.uniform(lo, hi)
        if name in self.overrides:
            return self._result(name, value)
        if spec.size and self.style.size in SIZE_CLASSES and hi > lo:
            a, b = SIZE_CLASSES[self.style.size]
            value = lo + (a + (value - lo) / (hi - lo) * (b - a)) * (hi - lo)
        if spec.size and self.style.snap > 0:
            step = self.style.snap / spec.snap_factor
            value = max(step, round(value / step) * step)
        return self._result(name, value)

    def int(self, name: str, lo: int, hi: int) -> int:
        self._spec(name)
        return self._result(name, self.rng.randint(lo, hi))

    def choice(self, name: str, options: Sequence[Any]) -> Any:
        self._spec(name)
        return self._result(name, self.rng.choice(list(options)))

    def bool(self, name: str, probability: float, enabled: bool = True, warning: bool = False) -> bool:
        """``rng.random() < probability`` (only rolled while ``enabled``, like ``cond and rng.random() < p``)."""
        self._spec(name)
        rolled = self.rng.random() < probability if enabled else False
        if name not in self.overrides and warning and self.style.warning:
            rolled = self.style.warning == "always"
        return self._result(name, rolled)

    def value(self, name: str, rolled: Any) -> Any:
        """Apply override (and snapping for size parameters) to a value the builder rolled itself."""
        spec = self._spec(name)
        if name not in self.overrides and spec.kind == "float" and spec.size and self.style.snap > 0:
            step = self.style.snap / spec.snap_factor
            rolled = max(step, round(rolled / step) * step)
        return self._result(name, rolled)

    def option(self, name: str) -> Any:
        """Not rolled at all - the declared default unless overridden (e.g. Unity script values).

        An option without default that wasn't given (``item_id``) returns None and isn't recorded.
        """
        spec = self._spec(name)
        if name not in self.overrides and (spec.default is None or spec.quiet):
            return spec.default
        return self._result(name, spec.default)

    # -- style --------------------------------------------------------------------
    def glow(self, weights: Sequence[float] = (0.7, 0.1, 0.2)) -> str:
        rolled = self.rng.choices(["M_GlowCyan", "M_GlowRed", "M_GlowOrange"], weights=weights)[0]
        return GLOW.get(self.style.glow or "", rolled)

    def glow_from(self, options: Sequence[str]) -> str:
        rolled = self.rng.choice(list(options))
        return GLOW.get(self.style.glow or "", rolled)

    def styled(self, default: str, options: Sequence[str]) -> str:
        """Material style without a roll: the style's preference if it is one of ``options``, else ``default``."""
        for preferred in MATERIAL_STYLES.get(self.style.material or "", ()):
            if preferred in options:
                return preferred
        return default

    def material(self, options: Sequence[str]) -> str:
        """``rng.choice(options)``, replaced by the material style's preference when it is one of the options."""
        rolled = self.rng.choice(list(options))
        for preferred in MATERIAL_STYLES.get(self.style.material or "", ()):
            if preferred in options:
                return preferred
        return rolled


def parse_param_overrides(items: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """``["door.style=airlock", "wall.length=4"]`` -> ``{"door": {"style": "airlock"}, "wall": {"length": "4"}}``."""
    result: Dict[str, Dict[str, str]] = {}
    for item in items:
        key, sep, value = item.partition("=")
        model_type, dot, name = key.strip().partition(".")
        if not sep or not dot or not name:
            raise ValueError(f"--param expects TYPE.NAME=VALUE, e.g. door.style=airlock (got {item!r})")
        result.setdefault(model_type, {})[name.strip()] = value.strip()
    return result


__all__ = ["Param", "ParamReader", "Style", "DETAIL", "GLOW", "MATERIAL_STYLES", "parse_param_overrides",
           "theme_style"]

"""Model types. Importing this package registers all built-in types."""

from .registry import REGISTRY, ModelType, asset_name, generate_asset, model, model_types  # noqa: F401

# Importing the modules registers their model types.
from . import (appliances, construction, environment, furniture, industrial, items, kit, machinery, mechanisms,  # noqa: F401,E402
               nature, props, puzzle, riddles, robots, ruins, structure, tech, traps, gameplay, buildkit, logic,
               facilities, lighting, rovers, alien, space, wrecks)
from . import geometry_demo  # noqa: F401,E402
from . import gameplay_tests  # noqa: F401,E402
from . import station_wave  # noqa: F401,E402

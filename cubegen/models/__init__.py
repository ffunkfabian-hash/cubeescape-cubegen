"""Model types. Importing this package registers all built-in types."""

from .registry import REGISTRY, ModelType, asset_name, generate_asset, model, model_types  # noqa: F401

# Importing the modules registers their model types.
from . import environment, industrial, props, ruins, tech  # noqa: F401,E402

"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import enrich_context  # noqa: F401
from app.hooks.handlers import start_analysis  # noqa: F401

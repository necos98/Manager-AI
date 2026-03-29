"""Hook handlers package: import modules here to trigger @hook decorator autodiscovery."""

from app.hooks.handlers import auto_completion  # noqa: F401
from app.hooks.handlers import auto_start_implementation  # noqa: F401
from app.hooks.handlers import auto_start_workflow  # noqa: F401
from app.hooks.handlers import enrich_context  # noqa: F401

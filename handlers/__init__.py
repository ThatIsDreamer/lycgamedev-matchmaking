from .admin import router as admin_router
from .common import router as common_router
from .solo import router as solo_router
from .start import router as start_router
from .team import router as team_router

__all__ = ["start_router", "solo_router", "team_router", "common_router", "admin_router"]

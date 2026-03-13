from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.agent import router as agent_router
from app.routers.notifications import router as notifications_router
from app.routers.files import router as files_router

__all__ = [
    "auth_router",
    "clients_router",
    "agent_router",
    "notifications_router",
    "files_router",
]

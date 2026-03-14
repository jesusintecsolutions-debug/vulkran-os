from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.agent import router as agent_router
from app.routers.notifications import router as notifications_router
from app.routers.files import router as files_router
from app.routers.content import router as content_router
from app.routers.leads import router as leads_router
from app.routers.briefing import router as briefing_router
from app.routers.accounting import router as accounting_router
from app.routers.render import router as render_router

__all__ = [
    "auth_router",
    "clients_router",
    "agent_router",
    "notifications_router",
    "files_router",
    "content_router",
    "leads_router",
    "briefing_router",
    "accounting_router",
    "render_router",
]

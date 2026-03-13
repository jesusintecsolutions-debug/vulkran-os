# BUILD LOG — VULKRAN OS

> Registro obligatorio de cada actualización del sistema.
> Cada entrada debe añadirse **antes** de hacer commit.

---

## [0.1.0] — 2026-03-13

### Fase 0: Infraestructura
- VPS Hostinger KVM4 (4 vCPU, 16GB RAM, 200GB NVMe) — `46.202.130.233`
- Ubuntu 24.04 LTS
- Docker 29.3 + Compose 5.1
- Firewall UFW (22, 80, 443)
- SSH key auth, password auth disabled
- Swap 2GB
- GitHub repo: `jesusintecsolutions-debug/vulkran-os`
- Deploy key configurada

### Fase 1: Backend Core
- **Config**: Pydantic Settings con env vars
- **Database**: SQLAlchemy 2.0 async + PostgreSQL 16 + asyncpg
- **Auth**: JWT (access + refresh) con bcrypt, HTTPBearer
- **Modelos**: User, Client, ClientUser, Conversation, Message, AgentTask, Notification, Setting
- **Routers**: auth (login/register/refresh/me), clients (CRUD), agent (chat/conversations), notifications
- **LLM Bridge**: Claude API via httpx, multi-turn tool-use loop
- **Agent Core**: 6 herramientas (get_client_list, get_client_context, create_task, get_pending_tasks, notify_user, get_system_status)
- **Worker**: ARQ con health check cron cada 30min
- **System prompt**: Agent persona como COO virtual
- **Docker Compose**: 6 servicios (caddy, api, worker, db, redis, n8n)

### Mejoras de seguridad (post-Fase 1)
- Dockerfile multi-stage build (deps → runtime) con non-root user (UID 1001)
- Healthcheck en container (curl /health cada 30s)
- .dockerignore para build optimizado
- Rate limiting en /api/auth/* (10 req/min por IP)
- Error handling centralizado (ApiError + unhandled catch)
- FK indexes añadidos: conversations.user_id, agent_tasks.conversation_id, agent_tasks.status
- Swagger docs en /api/docs
- ANTHROPIC_API_KEY configurada en producción

### Datos iniciales
- Admin: jesus@vulkran.es
- Clientes: Canal YouTube (600€), Inmobiliaria García (250€), Farmacia Central (340€)

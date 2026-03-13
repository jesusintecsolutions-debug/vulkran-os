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

### Fase 2: File Storage & Asset Management
- **FileStorage service**: upload, download, list, delete con seguridad completa
  - Magic bytes validation (no confía en extensión del cliente)
  - Filename sanitization (anti path traversal)
  - Size limits (10MB por archivo)
  - Blocked extensions (.exe, .bat, .sh, .py, etc.)
  - SHA-256 hash para integridad
- **Endpoints**: POST /api/files/upload/{client_id}, GET /api/files/download/{path}, GET /api/files/list/{client_id}, DELETE /api/files/{path}, POST /api/files/init/{client_id}
- **Caddy**: servido estático de /files/* directo desde /data (sin Python overhead)
- **Docker Compose**: Caddy ahora monta ./data:/data:ro (read-only)
- **Agent tool**: list_client_files — el agente puede consultar archivos de clientes
- **Estructura por cliente**: brand/, templates/static/, templates/video/, content/, invoices/

### Fase 3: Content Engine
- **Modelos**: ContentTemplate, ContentBatch, ContentItem
  - ContentTemplate: plantillas reutilizables por plataforma/tipo (prompt_template, schema_fields, visual_template)
  - ContentBatch: lote de contenido para un cliente (status workflow: draft → generating → review → approved → published)
  - ContentItem: pieza individual con content_data (JSONB), posición, estado independiente
- **Content Engine service**: generación via Claude API
  - Construye prompt enriquecido con brand_config del cliente + template + brief
  - Parseo robusto de JSON (maneja markdown wrapping)
  - Regeneración individual de items con feedback
  - Metadata de generación (tokens, tiempo, modelo)
- **Endpoints**:
  - Templates: GET /api/content/templates, POST /api/content/templates, GET /api/content/templates/{id}
  - Batches: GET /api/content/batches, POST /api/content/batches, GET /api/content/batches/{id}
  - Generate: POST /api/content/batches/{id}/generate (llama a Claude, genera items)
  - Approve: POST /api/content/batches/{id}/approve
  - Items: GET /api/content/batches/{id}/items, PATCH /api/content/items/{id}, POST /api/content/items/{id}/regenerate
  - Seed: POST /api/content/seed-templates (carga 6 plantillas base)
- **6 plantillas seed**: instagram-post, instagram-carousel, linkedin-post, blog-article, reel-script, email-newsletter
- **Agent tools**: create_content_batch (crea + genera batch completo), get_content_status (resumen de batches y items)
- **Testado en producción**: generación de 3 posts Instagram en ~18s con contenido profesional

### Fase 4: Leads/CRM
- **Modelos**: Lead, LeadActivity
  - Lead: pipeline completo (new → contacted → meeting → proposal → negotiation → won/lost)
  - LeadActivity: log automático de cada acción (notas, emails, llamadas, cambios de etapa)
  - Campos: name, company, email, phone, source, estimated_value, tags, next_action, lost_reason
- **Endpoints**:
  - CRUD: GET /api/leads, POST /api/leads, GET /api/leads/{id}, PATCH /api/leads/{id}, DELETE /api/leads/{id}
  - Pipeline: GET /api/leads/pipeline (stats por etapa, valor total, won/lost del mes)
  - Stage: POST /api/leads/{id}/stage (cambio de etapa con log automático)
  - Activities: GET /api/leads/{id}/activities, POST /api/leads/{id}/activities
  - Filtros: stage, source, search (nombre/empresa)
- **Agent tools**: create_lead, get_pipeline_status, update_lead_stage
- **get_system_status actualizado**: ahora incluye active_leads
- **Testado en producción**: 2 leads creados, pipeline stats con valor total 1050€, stage change con activity log

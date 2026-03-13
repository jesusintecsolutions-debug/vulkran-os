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

### Fase 5: Daily Briefing
- **Daily Briefing service**: recopila métricas de negocio y genera resumen ejecutivo con Claude Haiku
  - Métricas: clientes activos + MRR, pipeline leads por etapa + valor, contenido en revisión + generado 24h, tareas pendientes, acciones próximas
  - Generación de briefing con Claude Haiku (rápido + económico)
  - Briefing estructurado: resumen, clientes, pipeline, contenido, acciones prioritarias
- **Endpoints**: GET /api/briefing (briefing completo con AI), GET /api/briefing/metrics (métricas raw)
- **ARQ cron job**: daily_briefing_job ejecuta a las 07:00 UTC (08:00 Madrid), genera briefing + notificación a admins
- **Agent tool**: get_daily_briefing — el agente puede generar el briefing bajo demanda
- **Testado en producción**: briefing generado en ~5s con Haiku, métricas reales (3 clientes, 1190€ MRR, 2 leads, 1 batch)

### Fase 6: Accounting
- **Modelos**: Invoice, Expense
  - Invoice: numeración automática VK-YYYY-NNN, cálculo IVA (21% default), items JSONB, workflow (draft → sent → paid → overdue → cancelled)
  - Expense: categorías (hosting, software, marketing, tools, freelancer...), deducibilidad fiscal, vinculable a cliente
- **Endpoints**:
  - Invoices: GET /api/accounting/invoices, POST /api/accounting/invoices, GET /{id}, POST /{id}/send, POST /{id}/pay
  - Expenses: GET /api/accounting/expenses, POST /api/accounting/expenses
  - Summary: GET /api/accounting/summary?year=&month= (facturado, cobrado, pendiente, gastos, income neto, IVA)
- **Agent tool**: get_financial_summary — resumen financiero por mes
- **Testado en producción**: factura VK-2026-001 (600€ + 126€ IVA = 726€), gasto hosting 12.99€, income neto 713.01€

### Fase 8: Frontend — Scaffold & Core Pages
- **Stack**: React 19 + Vite 8 + TypeScript + Tailwind CSS v4 + React Router v7 + TanStack Query + Zustand + Axios + Lucide React
- **Arquitectura modular**: estructura de carpetas preparada para crecimiento (pages/, layouts/, components/ui/, stores/, hooks/, api/, lib/)
- **Diseño**: sistema de tokens custom con colores VULKRAN (#6d28d9), sidebar + top bar layout, badges por estado
- **Auth completa**: login con JWT, Zustand store (login/logout/loadUser), rutas protegidas con redirect a /login, interceptor Axios 401
- **API client**: Axios con baseURL configurable (VITE_API_URL), interceptor JWT en requests, refresh token handling
- **Routing**: React Router v7, rutas protegidas con ProtectedRoute wrapper, role-based sidebar navigation
- **Páginas implementadas**:
  - **LoginPage**: formulario email/password con error handling y loading state
  - **DashboardPage**: 4 stat cards (clientes/MRR, leads/pipeline, contenido 24h, tareas) + pipeline breakdown
  - **ClientsPage**: tabla con nombre, sector, email, cuota mensual, estado
  - **ContentPage**: grid de cards con badges de estado colorizados (draft, generating, review, approved, published, failed)
  - **LeadsPage**: tabla pipeline con nombre, empresa, origen, etapa (badges), valor estimado
  - **AccountingPage**: tabla facturas con nº, fecha, vencimiento, estado (badges), total
  - **BriefingPage**: briefing diario generado por AI con timestamp
  - **ChatPage**: chat completo con el agente AI (mensajes user/assistant, loading state, scroll automático)
  - **FilesPage**: placeholder para gestor de archivos
  - **SettingsPage**: perfil del usuario actual
- **AppLayout**: sidebar izquierdo (w-60) con 9 items de navegación filtrados por rol, header con título dinámico + campana notificaciones, footer con avatar + logout
- **Build**: 0 errores TypeScript, build de producción OK (352KB JS + 19KB CSS)
- **Config**: vite.config.ts con @tailwindcss/vite, path alias @/, proxy API dev

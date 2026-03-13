# ADR-001: VULKRAN OS — Agentic CEO System Architecture

## Status
**Accepted** — 2026-03-13

---

## Context

VULKRAN OS es un sistema operativo empresarial AI-first para una agencia de transformación digital (1 fundador, 3 clientes). El agente debe funcionar como un **COO virtual** capaz de:

- Generar contenido (texto, imágenes, vídeos) de nivel producción
- Enviar emails a leads y clientes
- Investigar empresas/leads en la web
- Generar briefings proactivos con propuestas
- Crear producciones visuales con Remotion (113 templates, 5 familias de diseño)
- Gestionar CRM, contabilidad, archivos
- Comunicarse via chat con interfaz futurista holográfica

**Constraints:**
- Equipo: 1 persona (Jesús) — arquitectura simple, mantenible
- Infra: 1 VPS (4 vCPU, 16GB RAM) + Vercel (frontend)
- Budget: Mínimo — Claude API, Resend (free tier), FAL.ai (pay-per-use)
- Timeline: Iterativo, cada fase entrega valor

---

## Architecture Decisions

### 1. Modular Monolith (no microservicios)

**Chosen**: FastAPI monolith con servicios modulares

| Option | Pros | Cons |
|--------|------|------|
| Microservicios | Scaling independiente | Overkill para 1 dev, complejo |
| **Monolith modular** | Simple, debuggable, 1 deploy | Todo en 1 proceso |
| Serverless | Auto-scale | Cold starts, vendor lock-in |

**Rationale**: 1 desarrollador, 3 clientes, 1 VPS. No necesita escalar partes independientes. Puede extraer servicios luego si crece.

### 2. Agent Tool Architecture — Flat Executor

**Chosen**: ToolExecutor con métodos planos (no multi-agent)

| Option | Pros | Cons |
|--------|------|------|
| Multi-agent (CrewAI) | Especialización | Complejidad, latencia, caro |
| **Flat ToolExecutor** | Simple, predecible, barato | Un solo "cerebro" |
| LangGraph | State machine | Overhead, learning curve |

**Rationale**: Claude con tool-use ya maneja 20+ tools bien. Multi-agent es prematuro. Añadir tools es trivial (1 método por tool). Si se necesita especialización, se añade después.

### 3. Nuevas Agent Tools (Fase B)

```
TOOLS ACTUALES (16):
✅ get_client_list, get_client_context
✅ create_task, get_pending_tasks
✅ notify_user, list_client_files
✅ create_content_batch, get_content_status
✅ create_lead, get_pipeline_status, update_lead_stage
✅ get_daily_briefing, get_financial_summary, get_system_status

TOOLS NUEVAS (+8 = 24 total):
🆕 send_email          → Resend API, plantillas, tracking
🆕 research_company    → Tavily/Perplexity, enriquecimiento de leads
🆕 research_topic      → Investigación web para briefs de contenido
🆕 generate_image      → FAL.ai (flux-pro), imágenes de marca
🆕 generate_video      → Remotion render API, templates videoflow
🆕 create_invoice_pdf  → reportlab, factura profesional
🆕 schedule_content    → Programar publicación (con ARQ job)
🆕 propose_actions     → Analizar métricas y sugerir acciones
```

### 4. Streaming Chat — SSE (Server-Sent Events)

**Chosen**: SSE via FastAPI StreamingResponse

| Option | Pros | Cons |
|--------|------|------|
| WebSocket | Bidireccional | Complejidad, reconnect logic |
| **SSE** | Simple, HTTP nativo, auto-reconnect | Solo server→client |
| Polling | Más simple | Latencia, ineficiente |

**Rationale**: El chat es request-response (user→agent→stream back). SSE es perfecto: HTTP nativo, funciona con Vercel proxy, auto-reconnect del navegador.

### 5. Content Engine — Pipeline de Medios

```
TEXT (actual)     → Claude API → ContentItem.content_data (JSON)
IMAGE (nuevo)     → FAL.ai flux-pro → ContentItem.visual_url (CDN URL)
VIDEO (nuevo)     → Remotion Lambda/API → ContentItem.visual_url (S3/storage URL)

Pipeline:
  Brief → Claude genera guión →
    → Texto: directo a ContentItem
    → Imagen: prompt → FAL.ai → URL → ContentItem
    → Vídeo: moments[] → Remotion render → URL → ContentItem
```

### 6. Email System — Resend + Templates

```
Resend API (ya configurado en settings)
├── Transactional: facturas, notificaciones, bienvenida
├── Lead nurture: secuencias automáticas por stage
├── Marketing: newsletters desde ContentBatch
└── Internal: briefing diario al admin

Modelo nuevo: EmailTemplate (subject, body_html, variables)
Job ARQ: send_email_job (async, retry, tracking)
```

### 7. Web Research — Tavily Search API

**Chosen**: Tavily Search API (diseñado para LLM agents)

| Option | Pros | Cons |
|--------|------|------|
| Perplexity | Buena calidad | Caro, rate limits |
| **Tavily** | Hecho para agents, barato | Menos conocido |
| SerpAPI | Google results | Solo links, hay que scrappear |
| Firecrawl | Scraping | Overkill para búsqueda |

**Rationale**: Tavily devuelve contenido estructurado optimizado para LLMs. $1 = 1000 búsquedas. Perfecto para enriquecer leads y research.

---

## Frontend Architecture

### 8. Design System — Dark Mode Holográfico

**Chosen**: Tailwind v4 tokens + Framer Motion + React Three Fiber

```
TEMA: Dark mode por defecto
├── Background: #0A0A0F (deep void)
├── Surface: #12121A (elevated cards)
├── Border: rgba(109, 40, 217, 0.2) (purple glow)
├── Primary: #6D28D9 (vulkran purple)
├── Accent: #8B5CF6 (light purple)
├── Neon: #00F0FF (cyan highlights)
├── Text: #E2E8F0 (off-white)
├── Muted: #64748B (slate)
└── Success/Warning/Error: green/amber/red neon variants

GLASSMORPHISM:
├── backdrop-filter: blur(16px)
├── background: rgba(18, 18, 26, 0.7)
├── border: 1px solid rgba(109, 40, 217, 0.15)
└── box-shadow: 0 0 30px rgba(109, 40, 217, 0.1)
```

### 9. HoloBrain — Cerebro Holográfico 3D

**Stack**: @react-three/fiber + @react-three/drei + @react-three/postprocessing

```
Componentes:
├── HoloBrain.tsx         — <Canvas> + post-processing (Bloom, Scanline, Vignette)
├── BrainNetwork.tsx      — useFrame loop, state transitions
├── NodeInstances.tsx     — InstancedMesh (80-150 nodos, 1 draw call)
├── EdgeLines.tsx         — LineSegments con pulse shader
├── useBrainState.ts      — Zustand store: IDLE | TYPING | THINKING | RESPONDING
└── shaders/
    ├── node.vert/frag    — holographic glow, fresnel, pulse
    └── edge.vert/frag    — traveling light, brightness

Estados de animación:
┌─────────────┬────────────┬──────────┬──────────┬──────────────┐
│ Parámetro   │ IDLE       │ TYPING   │ THINKING │ RESPONDING   │
├─────────────┼────────────┼──────────┼──────────┼──────────────┤
│ Rotación    │ 0.1 rad/s  │ 0.15     │ 0.3      │ 0.05         │
│ Pulso       │ 0.5 Hz     │ 1.5 Hz   │ 4.0 Hz   │ 0.8 Hz       │
│ Brillo edge │ 30%        │ 60%      │ 100%     │ 70%          │
│ Escala      │ 1.0        │ 1.05     │ 1.0      │ 1.0          │
│ Color shift │ purple     │ purple   │ warm     │ purple→cyan  │
│ Wave        │ off        │ off      │ random   │ center-out   │
└─────────────┴────────────┴──────────┴──────────┴──────────────┘
```

### 10. Responsive Strategy

```
Mobile-first con 3 breakpoints:
├── sm (640px)  — Stack, sidebar → bottom sheet
├── md (768px)  — Sidebar collapsible
├── lg (1024px) — Full sidebar + content
└── xl (1280px) — Sidebar + content + panel lateral

Sidebar:
├── Desktop: fijo 240px
├── Tablet: collapsible → iconos 64px
├── Mobile: bottom navigation bar (5 items principales)
└── Chat: fullscreen con HoloBrain de fondo
```

---

## Implementation Phases

### Fase B: Backend (email, research, streaming, tools)
1. `send_email` service + Resend integration
2. `research` service + Tavily API
3. SSE streaming endpoint para chat
4. `generate_image` service + FAL.ai
5. 8 nuevas agent tools
6. Email templates (invoice, notification, nurture)

### Fase C: Frontend (design system + HoloBrain)
1. Dark mode theme tokens + glassmorphism
2. Component library (Button, Input, Card, Table, Modal, Toast)
3. Responsive AppLayout (sidebar → mobile nav)
4. Framer Motion page transitions + micro-interactions
5. HoloBrain 3D component con 4 estados
6. Chat redesign con streaming + HoloBrain background

### Fase D: Responsive & Mobile
1. Mobile navigation bottom bar
2. Tables → card views en mobile
3. Touch gestures
4. PWA (installable)

### Fase E: Content Engine Pro
1. FAL.ai image generation pipeline
2. Remotion video generation integration
3. Content preview en frontend
4. Template management UI

### Fase F: Polish
1. Performance audit + code splitting
2. Security audit
3. E2E tests
4. Deploy optimization

---

## Trade-offs Accepted

1. **Monolith vs microservicios**: Aceptamos acoplamiento a cambio de simplicidad
2. **SSE vs WebSocket**: Aceptamos unidireccionalidad a cambio de simplicidad
3. **Flat tools vs multi-agent**: Aceptamos un solo cerebro a cambio de predecibilidad
4. **Three.js custom vs librería**: Aceptamos más código a cambio de control total
5. **Dark mode only (inicial)**: Aceptamos no tener light mode a cambio de velocidad

## Revisit Triggers
- Si se superan 10 clientes → considerar multi-tenant más robusto
- Si el agente necesita >30 tools → considerar especialización
- Si latencia de respuesta >10s frecuente → considerar caching/pre-compute
- Si el VPS no escala → considerar cloud managed services

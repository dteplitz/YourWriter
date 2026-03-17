# YourWriter — Arquitectura Técnica

*Documento vivo. Se actualiza al final de cada sprint con lo que fue construido o modificado.*
*Última actualización: Sprint 4 ✅ — 2026-03-16*

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, Vite, TypeScript, Zustand, react-router-dom |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Base de datos | SQLite (SQLAlchemy async + aiosqlite) |
| Agent layer | LangChain, LangGraph, Anthropic SDK |
| Auth | JWT (email/password) |

**Puertos locales:**
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8001`
- API base: `http://localhost:8001/api`

**Para correr la app:** `bash dev.sh` desde el root del proyecto. El script mata procesos zombie, limpia lock files y arranca backend y frontend.

---

## Estructura de directorios

```
yourwriter/
├── backend/
│   ├── api/
│   │   ├── routes/          # FastAPI routers (auth, writers, identity, chat, evolution)
│   │   └── deps.py          # get_current_user dependency
│   ├── auth/
│   │   └── auth.py          # JWT creation + validation
│   ├── db/
│   │   ├── database.py      # Engine, session factory, init_db()
│   │   └── models.py        # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas (request/response)
│   └── services/            # Business logic (writer_service, chat_service, user_service)
│
├── frontend/src/
│   ├── api/
│   │   └── client.ts        # Todas las llamadas al backend (única fuente de verdad)
│   ├── components/          # Componentes reutilizables
│   ├── pages/               # Páginas (LoginPage, DashboardPage, WriterPage)
│   ├── stores/              # Zustand stores (authStore, writerStore)
│   ├── types/               # TypeScript types
│   ├── index.css            # Design system: variables CSS, base styles
│   └── config-panel.css     # Estilos del Artist Profile / character sheet
│
├── agents/
│   ├── graphs/
│   │   ├── writer_graph.py  # LangGraph principal (chat + write pipeline)
│   │   └── evolution_graph.py # Grafo de evolución (existe, no se dispara aún)
│   ├── nodes/
│   │   ├── chat_node.py     # Nodo de chat conversacional
│   │   ├── writing_nodes.py # outline_node, draft_node, refine_node, refine_node_stream
│   │   └── evolution_nodes.py
│   ├── tools/
│   │   ├── web_search.py    # STUB — retorna mock data
│   │   ├── memory.py        # Dict en memoria (no persiste a DB)
│   │   └── constraints.py
│   ├── prompts/
│   │   └── system.py        # System prompts para los nodos
│   └── evolution/
│       ├── identity.py      # Dataclass Identity con to_dict/from_dict/to_prompt_string
│       ├── diff.py          # Lógica de diff de identidad
│       └── templates.py
│
└── data/
    └── yourwriter.db        # SQLite file (generado en runtime)
```

---

## Base de datos

**Sin Alembic.** Las tablas se crean en startup via `Base.metadata.create_all` en `backend/db/database.py::init_db()`. Para agregar una tabla o columna: modificar el modelo y reiniciar el servidor (en desarrollo). Para producción: pendiente definir estrategia de migrations.

### Modelos actuales

**`users`**
```
id              PK
email           unique, indexed
hashed_password
api_key_encrypted  nullable
created_at
```

**`writers`**
```
id              PK
user_id         FK → users (cascade delete)
name
purpose
created_at
updated_at
```

**`writer_identities`**
```
id              PK
writer_id       FK → writers (cascade delete)
personality     JSON  {"voice": "neutral", "creativity": 0.7, ...}
emotions        JSON  {"energy": 0.8, "melancholy": 0.3, ...}
memories        JSON  [...]
topics          JSON  [...]
constraints     JSON  {"audience": "tech enthusiasts", ...}
lifelong_objectives  JSON  [...]
version         int   (incrementa en cada update)
created_at
```

**`chat_messages`**
```
id              PK
writer_id       FK → writers (cascade delete)
role            enum: user | assistant | system
content         text
created_at
```

**`evolution_logs`**
```
id              PK
writer_id       FK → writers (cascade delete)
field_changed
old_value       nullable
new_value       nullable
reason          nullable
created_at
```

### Patrón crítico de sesiones SQLite

SQLite serializa writes. Si una sesión queda abierta durante una LLM call (10–30s), bloquea toda la base.

**Regla:** nunca tener una sesión abierta durante LLM calls o streaming.
- Los endpoints normales usan `Depends(get_db)` (session corta, auto-commit al finalizar la request)
- El endpoint de streaming **NO usa `Depends(get_db)`** — maneja sessions manualmente: abrir → escribir → commit → cerrar, antes de iniciar el stream
- Engine configurado con `NullPool` + WAL mode + `busy_timeout=5000`

---

## API Endpoints

Todas las rutas tienen prefijo `/api`.

### Auth — `/api/auth`
```
POST /auth/register     body: {email, password}   → {access_token}
POST /auth/login        body: {email, password}   → {access_token}
```

### Writers — `/api/writers`
```
GET    /writers                          → list[WriterResponse]
POST   /writers      body: WriterCreate  → WriterResponse (201)
GET    /writers/{id}                     → WriterWithIdentity
PUT    /writers/{id} body: WriterUpdate  → WriterResponse
DELETE /writers/{id}                     → 204
```

### Identity — `/api/writers`
```
GET /writers/{id}/identity                          → IdentityResponse
PUT /writers/{id}/identity  body: IdentityUpdate    → IdentityResponse (nueva versión)
PUT /writers/{id}/constraints body: ConstraintsUpdate → IdentityResponse (nueva versión)
```

Cada PUT de identidad crea una nueva fila en `writer_identities` con `version+1`. No hay updates destructivos — el historial queda.

### Chat — `/api/chat`
```
POST /chat/{id}/message          body: {content}  → ChatMessageResponse (201)  [non-streaming, deprecated]
POST /chat/{id}/message/stream   body: {content}  → SSE stream
GET  /chat/{id}/history                           → list[ChatMessageResponse]
```

### SSE Event types (stream endpoint)
```json
{"token": "text chunk"}                              // fragmento de texto
{"phase": "outlining" | "drafting" | "refining"}    // cambio de fase del pipeline
{"done": true, "message_id": 123}                   // stream completado
{"error": "message"}                                // error
```

---

## Agent Layer

### writer_graph (LangGraph)

```
START
  └─► detect_intent_node
        ├─ mode="chat"  ──────────────────────────────► chat_node ──► END
        └─ mode="write" ──► outline_node ──► draft_node ──► refine_node ──► respond_node ──► END
```

**detect_intent_node**: keyword matching sobre el último mensaje del usuario. No usa LLM.

**Nota:** El streaming NO corre a través del grafo compilado. `chat_service.py::stream_writer_agent()` orquesta los nodos manualmente para poder hacer yield de eventos SSE entre pasos. El grafo compilado (`writer_graph.ainvoke`) solo lo usa el endpoint non-streaming (deprecated).

### Estado del grafo (`WriterState`)
```python
messages: list[dict]       # historial completo
writer_id: str
writer_name: str
identity: dict             # purpose, personality, emotions, constraints, lifelong_objectives
constraints: dict
mode: "chat" | "write"
outline: str               # output de outline_node
draft: str                 # output de draft_node
refined_content: str       # output de refine_node
evolution_pending: bool
```

### Herramientas (agents/tools/)
| Tool | Estado |
|------|--------|
| `web_search.py` | **STUB** — retorna mock data, no conectado al pipeline |
| `memory.py` | Dict en memoria, no persiste a DB |
| `constraints.py` | Parseo de constraints en plain English |

---

## Frontend

### Rutas
```
/login          → LoginPage
/               → DashboardPage (protegida)
/writer/:id     → WriterPage (protegida)
```

### Stores (Zustand)
- `authStore` — token JWT, isAuthenticated, login/logout
- `writerStore` — selectedWriter, lista de writers

### Design System (`index.css`)
Variables CSS canónicas — no usar colores o radii hardcodeados:
```css
--bg-primary: #0f0f13      --bg-secondary: #1a1a24    --bg-tertiary: #24243a
--bg-card: #1e1e2e         --bg-input: #2a2a3e        --bg-hover: #2e2e44
--text-primary: #e4e4ef    --text-secondary: #a0a0b8  --text-muted: #6c6c88
--accent: #7c6ff7          --accent-hover: #6b5ce6    --accent-subtle: rgba(124,111,247,0.15)
--danger: #e05555          --success: #4ade80         --warning: #facc15
--border: #2e2e44          --border-light: #3a3a54
--radius: 8px              --radius-lg: 12px
--font-sans: Inter         --font-mono: JetBrains Mono
```

Estilos específicos del Artist Profile / character sheet en `config-panel.css` (Sprint 4).

### Componentes clave
| Componente | Qué hace |
|-----------|---------|
| `ConfigPanel` | Artist Profile — character sheet editable (EmotionBar, TraitBadge, ConstraintCard) |
| `EmotionBar` | Barra de progreso animada para valores 0–1 |
| `TraitBadge` | Badge para traits/topics/objectives |
| `ConstraintCard` | Tarjeta individual para cada constraint |
| `ChatPanel` | Chat con SSE streaming, muestra fases del pipeline |
| `EvolutionFeed` | Log de cambios de identidad |
| `WriterCard` | Card en el dashboard |
| `CreateWriterModal` | Modal de creación de writer |

### Patrón de CSS para layouts
- Layouts de altura fija: `min-height: 0` en **toda** la cadena de flex children
- Columnas con scroll independiente: `overflow-y: auto` + `min-height: 0`
- CSS de área en archivos separados (`config-panel.css`), no en `index.css`
- Animaciones: CSS keyframes + React state (sin framer-motion)

---

## Lo que existe pero no está activo

| Qué | Dónde | Estado |
|-----|-------|--------|
| `evolution_graph.py` | `agents/graphs/` | Grafo construido, nunca se dispara |
| `evolution_nodes.py` | `agents/nodes/` | Implementado, no conectado |
| `evolution/identity.py` | `agents/evolution/` | Identity dataclass con to_dict/from_dict/to_prompt_string |
| `backend/api/routes/evolution.py` | `backend/api/routes/` | Ruta existe, sin endpoints útiles aún |
| `web_search` tool | `agents/tools/web_search.py` | Stub con mock data |
| `memory` tool | `agents/tools/memory.py` | Dict en memoria, sin persistencia |

---

## Notas técnicas para próximos sprints

**Sprint 5 — qué agregar:**
- Modelo `WriterPiece` en `models.py` + recrear tablas (create_all)
- Tool Registry en `agents/tools/registry.py` (arquitectura general para tools)
- `research_node` como llamada directa al Anthropic SDK (no LangGraph) — web_search_20250305
- Endpoint `/brief` en `backend/api/routes/chat.py`
- Endpoints `/pieces` en `backend/api/routes/writers.py`
- Ruta `/studio/:writerId` en el router de React
- Ver `SPRINT5.md` para el plan completo

**Sprint 6 — evolution graph:**
- Trigger al guardar un `WriterPiece` completado
- `evolution_graph.py` ya existe — necesita conectarse al trigger post-sesión

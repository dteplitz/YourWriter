# YourWriter — Arquitectura Técnica

*Documento vivo. Se actualiza al final de cada sprint con lo que fue construido o modificado.*
*Última actualización: Sprint 5 ✅ — 2026-03-17*

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, Vite, TypeScript, Zustand, react-router-dom |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Base de datos | SQLite (SQLAlchemy async + aiosqlite) |
| Agent layer | LangChain, LangGraph, Anthropic SDK ≥0.49.0 |
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
│   ├── schemas/
│   │   ├── ...              # Pydantic schemas existentes
│   │   └── studio.py        # BriefRequest, BriefResponse, PieceResponse (Sprint 5)
│   └── services/            # Business logic (writer_service, chat_service, user_service)
│
├── frontend/src/
│   ├── api/
│   │   └── client.ts        # Todas las llamadas al backend (única fuente de verdad)
│   ├── components/          # Componentes reutilizables
│   ├── pages/               # Páginas (LoginPage, DashboardPage, WriterPage, StudioPage)
│   ├── stores/              # Zustand stores (authStore, writerStore)
│   ├── types/               # TypeScript types
│   │   ├── index.ts         # Re-exports
│   │   ├── writer.ts        # Writer, Identity, Constraints
│   │   └── studio.ts        # Brief, Piece, ToolUseEvent, ToolResultEvent (contrato canónico)
│   ├── index.css            # Design system: variables CSS, base styles, WriterPage layout
│   ├── config-panel.css     # Estilos del Artist Profile / character sheet
│   ├── writing.css          # Estilos del Studio (Sprint 5)
│   └── session.css          # Estilos de la sesión activa (Sprint 5)
│
├── agents/
│   ├── graphs/
│   │   ├── writer_graph.py  # LangGraph principal (chat + write pipeline)
│   │   └── evolution_graph.py # Grafo de evolución (existe, no se dispara aún)
│   ├── nodes/
│   │   ├── chat_node.py     # Nodo de chat conversacional
│   │   ├── writing_nodes.py # outline_node, draft_node, refine_node, studio_refine_node_stream
│   │   ├── research_node.py # research_node_stream: web_search_20250305 con SSE (Sprint 5)
│   │   └── evolution_nodes.py
│   ├── tools/
│   │   ├── registry.py      # Tool Registry con WriterTool dataclass + get_anthropic_tools() (Sprint 5)
│   │   ├── web_search.py    # STUB — ya no se usa (reemplazado por registry.py)
│   │   ├── memory.py        # Dict en memoria (no persiste a DB)
│   │   └── constraints.py
│   ├── prompts/
│   │   └── system.py        # System prompts (incluye BRIEF_GENERATION_PROMPT, STUDIO_REFINE_PROMPT)
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
emotions        JSON  {"enthusiasm": 0.5, "humor": 0.3, ...}   ← valores 0–1
memories        JSON  [...]
topics          JSON  [...]
constraints     JSON  {"max_characters": "1000", ...}
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

**`writer_pieces`** ← Sprint 5
```
id              PK
writer_id       FK → writers (cascade delete)
title           string(500)
content         text
format          string(100)   — "short story", "poem", "essay", etc.
word_count      int
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

### Pieces — `/api/writers` ← Sprint 5
```
GET /writers/{id}/pieces                 → list[PieceResponse]
GET /writers/{id}/pieces/{piece_id}      → PieceResponse
```

### Chat — `/api/chat`
```
POST /chat/{id}/message          body: {content}  → ChatMessageResponse (201)  [non-streaming, deprecated]
POST /chat/{id}/message/stream   body: {content}  → SSE stream
GET  /chat/{id}/history                           → list[ChatMessageResponse]
POST /chat/{id}/brief            body: {message}  → BriefResponse             [Sprint 5]
POST /chat/{id}/studio/stream    body: {brief}    → SSE stream                [Sprint 5]
```

### SSE Event types — chat stream
```json
{"token": "text chunk"}
{"phase": "outlining" | "drafting" | "refining"}
{"done": true, "message_id": 123}
{"error": "message"}
```

### SSE Event types — studio/stream ← Sprint 5
```json
{"token": "text chunk"}
{"phase": "outlining" | "drafting" | "refining"}
{"tool_use": {"name": "web_search", "display_name": "Buscando", "query": "..."}}
{"tool_result": {"name": "web_search", "summary": "..."}}
{"piece": {PieceResponse}}
{"done": true}
{"error": "message"}
```

---

## Agent Layer

### Dos pipelines separados (Sprint 5)

| Pipeline | Función | Trigger |
|----------|---------|---------|
| `stream_writer_agent()` | Chat conversacional + write por keywords | `POST /chat/{id}/message/stream` |
| `stream_studio_session()` | Studio con research → outline → draft → refine | `POST /chat/{id}/studio/stream` |

**`stream_studio_session()` NO usa el grafo compilado.** Orquesta manualmente:
1. `research_node_stream()` → yielda tool_use/tool_result, acumula search_results
2. `outline_node(state)` → genera outline
3. `draft_node(state)` → genera draft
4. `studio_refine_node_stream(state)` → streama tokens + parsea `---TITLE: <title>---` al final
5. Guarda `WriterPiece` en sesión corta → yielda evento `{"piece": {...}}`

### writer_graph (LangGraph)

```
START
  └─► detect_intent_node (word-boundary regex sobre keywords de escritura)
        ├─ mode="chat"  ──────────────────────────────► chat_node ──► END
        └─ mode="write" ──► outline_node ──► draft_node ──► refine_node ──► respond_node ──► END
```

**Nota:** El streaming del chat tampoco corre a través del grafo compilado. `chat_service.py::stream_writer_agent()` orquesta los nodos manualmente.

### Tool Registry (Sprint 5)

`agents/tools/registry.py` — arquitectura general para herramientas:

```python
@dataclass
class WriterTool:
    name: str
    display_name: str      # para mostrar en la UI ("Buscando")
    anthropic_type: str | None   # "web_search_20250305" para built-ins
    executor: Callable | None    # para tools custom

TOOL_REGISTRY = {
    "web_search": WriterTool(
        name="web_search",
        display_name="Buscando",
        anthropic_type="web_search_20250305",
        executor=None
    )
}

def get_anthropic_tools(tool_names: list[str]) -> list[dict]: ...
```

### research_node (Sprint 5)

`agents/nodes/research_node.py` — llama a Claude con `web_search_20250305`:
- Yielda `{"tool_use": ToolUseEvent}` cuando Claude inicia una búsqueda
- Yielda `{"tool_result": ToolResultEvent}` cuando llegan los resultados
- Yielda `{"search_results": str}` como evento final (acumulado para el outline)

### Título generado automáticamente

`studio_refine_node_stream()` instruye al modelo a agregar `---TITLE: <título>---` al final del stream. El backend parsea esto antes de guardar el `WriterPiece`:
- El título se extrae y se usa como `WriterPiece.title`
- El marcador se elimina del contenido antes de guardar

---

## Frontend

### Rutas
```
/login              → LoginPage
/                   → DashboardPage (protegida)
/writer/:id         → WriterPage (protegida)
/studio/:writerId   → StudioPage (protegida)  ← Sprint 5
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

Estilos por área en archivos separados (no en `index.css`):
- `config-panel.css` — Artist Profile / character sheet
- `writing.css` — Studio views (StudioTransition, BriefSetup, WritingArtifact, PiecesLibrary)
- `session.css` — SessionExperience (streaming view, phase pills, tool use pills)

**Regla de imports CSS:** siempre relativo a `src/`, no al directorio del componente:
- Desde `src/pages/`: `import '../writing.css'`
- Desde `src/components/`: `import '../session.css'`

### Componentes clave

| Componente | Qué hace |
|-----------|---------|
| `ConfigPanel` | Artist Profile — character sheet editable (EmotionBar, TraitBadge, ConstraintCard) |
| `EmotionBar` | Barra de progreso animada para valores 0–1 (muestra como %) |
| `TraitBadge` | Badge para traits/topics/objectives con tier colors |
| `ConstraintCard` | Tarjeta individual para cada constraint |
| `ChatPanel` | Chat con SSE streaming, fases del pipeline, botón "Studio →" |
| `EvolutionFeed` | Log de cambios de identidad |
| `WriterCard` | Card en el dashboard |
| `CreateWriterModal` | Modal de creación de writer |
| `StudioTransition` | Pantalla de fade-in al entrar al Studio |
| `BriefSetup` | Brief en 4 estados: input → loading → preview → clarifying |
| `SessionExperience` | Sesión activa: stream + phase pills + tool use pill + artifact |
| `WritingArtifact` | Documento final: título, formato badge, copy, Iterar/Finalizar |
| `IterationInput` | Textarea de notas del productor, relanza el pipeline |
| `PiecesLibrary` | Discografía del writer — lista expandible con fechas en español |

### WriterPage — layout scroll

La WriterPage usa un layout vertical scrollable en vez del grid de 3 columnas:

```
writer-page (overflow-y: auto)
  writer-sticky-header (position: sticky, top: 0)
    writer-page-header (Back + nombre + purpose)
    writer-rpg-strip (colapsable via max-height transition)
      → emotion mini-bars + trait chips
      → visible solo cuando el hero scrolló fuera de la vista
  writer-hero
    ConfigPanel (héroe a ancho completo)
  writer-below-fold (height: calc(100vh - 108px))
    writer-chat-col (flex: 1)   ← ChatPanel
    writer-evolution-col (300px) ← EvolutionFeed
```

`WriterPage` usa un scroll event listener sobre `pageRef` para detectar cuando el hero scroll fuera de vista y activar el `writer-rpg-strip`. `ConfigPanel` recibe `onIdentityLoaded` callback para que WriterPage tenga los datos de identidad disponibles para el strip.

### Patrón de CSS para layouts
- Layouts scrollables: el contenedor principal tiene `overflow-y: auto`
- Secciones de altura fija dentro de un layout scroll: usar `height` (no `min-height`) para que los children con `height: 100%` resuelvan correctamente
- CSS de área en archivos separados, imports relativos a `src/`
- Animaciones: CSS keyframes + React state (sin framer-motion)

---

## Lo que existe pero no está activo

| Qué | Dónde | Estado |
|-----|-------|--------|
| `evolution_graph.py` | `agents/graphs/` | Grafo construido, nunca se dispara |
| `evolution_nodes.py` | `agents/nodes/` | Implementado, no conectado |
| `evolution/identity.py` | `agents/evolution/` | Identity dataclass con to_dict/from_dict/to_prompt_string |
| `backend/api/routes/evolution.py` | `backend/api/routes/` | Ruta existe, sin endpoints útiles aún |
| `memory` tool | `agents/tools/memory.py` | Dict en memoria, sin persistencia |

---

## Notas técnicas para próximos sprints

**Sprint 5.5 — Deploy:**
- PostgreSQL migration (reemplazar SQLite)
- Containerización + deploy en Railway/Render
- GitHub Actions: tests → deploy
- PR review automático con Claude API

**Sprint 6a — Identity Evolution:**
- Trigger: al guardar un `WriterPiece` → disparar `evolution_graph.py`
- `evolution_graph.py` ya existe — necesita conectarse al trigger post-sesión
- Actualizar el character sheet animado al recibir cambios

**Sprint 6b — Writer Initialization Flow:**
- Creación con descripción libre ("quiero un escritor tipo GRRM")
- Reemplaza el modal simple actual

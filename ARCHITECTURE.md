# YourWriter — Arquitectura Técnica

*Documento vivo. Se actualiza al final de cada sprint con lo que fue construido o modificado.*
*Última actualización: 2026-04-15 — Sprint 6b.5 completo (writer initialization flow simple + preview estructurado con Lang). Para el contexto completo de decisiones sobre LangChain/LangGraph/LangMem, ver `LANG_PLAYBOOK.md`.*

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, Vite, TypeScript, Zustand, react-router-dom |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Base de datos | PostgreSQL en runtime (SQLAlchemy async + asyncpg). SQLite (aiosqlite) en tests. |
| Agent layer | LangChain, LangGraph, Anthropic SDK ≥0.49.0 |
| Auth | JWT (email/password) |

**Puertos locales:**
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8001`
- API base: `http://localhost:8001/api`

**Producción:**
- URL: `https://yourwriter-production.up.railway.app`
- Platform: Railway (monorepo, single service)
- DB: PostgreSQL managed (Railway)
- Deploy: auto-deploy en push a `main`

**Para correr la app (local):**
```bash
bash dev.sh          # arranca docker compose up --build
```
Requiere Docker Desktop corriendo. Primera vez tarda ~2 min (build de imágenes + pull de `postgres:16-alpine`). Las siguientes arrancan rápido.

Cuando ves esto, está listo:
```
db-1        | LOG:  database system is ready to accept connections
backend-1   | INFO:     Application startup complete.
frontend-1  | VITE ready in ... Local: http://localhost:3000/
```

- `Ctrl+C` para parar. `docker compose down` para limpiar contenedores (los datos persisten en el volume `pg_data`). `docker compose down -v` también borra los datos.
- Hot reload activo: cambios en `.py` recargan el backend, cambios en `.tsx/.ts` recargan el frontend.
- **DB local:** PostgreSQL corriendo en el service `db` de docker-compose, datos persistidos en el volume `pg_data`. La connection string vive en `docker-compose.yml`, no en `.env`.
- Para abrir un shell de psql: `docker compose exec db psql -U yourwriter -d yourwriter`.

**Ambientes:**
| | Local | Railway (prod) | Tests / CI |
|---|---|---|---|
| Cómo arranca | `bash dev.sh` → docker compose | auto-deploy desde push a `main` | `pytest backend/tests/` |
| Backend | uvicorn `--reload`, source montado | uvicorn, source baked en imagen | — |
| Frontend | vite dev HMR en :3000 | static files servidos por FastAPI | `npm run test`, `tsc --noEmit` |
| DB | PostgreSQL en service `db` (volume `pg_data`) | PostgreSQL (Railway managed) | SQLite in-memory (`./test.db`) |
| Env vars | `.env` local + `docker-compose.yml` | Variables de entorno en Railway | `DATABASE_URL` override en CI |

**Por qué Postgres también en local (Sprint 6b Slice 0, 2026-04-08):**
Antes corríamos SQLite local + PostgreSQL en prod. La asimetría iba a doler con Sprint 6b Slice 3 (LangGraph checkpointer + SSE streaming) que tiene gotchas conocidos en SQLite. Unificar el motor en runtime elimina toda una clase de bugs "anda en local, rompe en prod" sin costo significativo (un service más en el compose, ~30s al primer build). Tests siguen en SQLite por velocidad y porque testean lógica, no integración con el motor.

---

## Estructura de directorios

```
yourwriter/
├── backend/
│   ├── api/
│   │   ├── routes/          # FastAPI routers (auth, writers, identity, chat, evolution, sessions)
│   │   └── deps.py          # get_current_user dependency
│   ├── auth/
│   │   └── auth.py          # JWT creation + validation
│   ├── db/
│   │   ├── database.py      # Engine, session factory, init_db()
│   │   └── models.py        # SQLAlchemy models
│   ├── schemas/
│   │   ├── ...              # Pydantic schemas existentes
│   │   ├── studio.py        # BriefRequest, BriefResponse, PieceResponse (Sprint 5)
│   │   ├── evolution.py     # EvolutionEvent, EvolutionResult Pydantic schemas (Sprint 6a)
│   │   └── session.py       # Session summary/detail + import flow contracts (Sprint 6b)
│   │   └── writer_initialization.py  # Free-text init request/preview/create contracts (Sprint 6b.5)
│   └── services/            # Business logic (writer_service, chat_service, user_service, import flow, session queries)
│       ├── evolution_service.py      # run_evolution() + shared identity persistence helper + source_session_id derivation
│       ├── session_import_service.py # load session context → proposal → import → skip
│       └── session_query_service.py  # summary/detail/resume-mode/abandon for Studio sessions (Slice 4)
│       └── writer_initialization_service.py # Lang structured-output preview + create-from-preview (Sprint 6b.5)
│
├── frontend/src/
│   ├── api/
│   │   └── client.ts        # Todas las llamadas al backend (única fuente de verdad)
│   ├── components/          # Componentes reutilizables
│   ├── pages/               # Páginas (LoginPage, DashboardPage, WriterInitializationPage, WriterPage, StudioPage, SessionImportPage)
│   ├── stores/              # Zustand stores (authStore, writerStore)
│   ├── types/               # TypeScript types
│   │   ├── index.ts         # Re-exports
│   │   ├── writer.ts        # Writer, Identity, Constraints, WriterInitializationPreview
│   │   └── studio.ts        # Brief + Studio SSE types + post-session import contracts
│   ├── index.css            # Design system: variables CSS, base styles, WriterPage layout
│   ├── config-panel.css     # Estilos del Artist Profile / character sheet
│   ├── writing.css          # Estilos del Studio (Sprint 5)
│   ├── writer-init.css      # Estilos del flow de creacion simple (Sprint 6b.5)
│   ├── session.css          # Estilos de la sesión activa (Sprint 5)
│   └── import-flow.css      # Estilos del post-session import flow (Sprint 6b Slice 2)
│
├── agents/
│   ├── graphs/
│   │   ├── evolution_graph.py # Grafo de evolución 2-stage: detect → compute → apply (Sprint 6a)
│   │   └── studio_graph.py    # Grafo real del Studio: research → outline → draft → refine + checkpointer (Sprint 6b Slice 3)
│   ├── nodes/
│   │   ├── chat_node.py     # ChatAnthropic + cache_control (Lang Refresh)
│   │   ├── writing_nodes.py # outline_node, draft_node, refine_node, studio_refine_node_stream — todos en ChatAnthropic (Lang Refresh)
│   │   ├── research_node.py # ChatAnthropic.bind_tools(web_search_20250305) con SSE (Lang Refresh)
│   │   └── evolution_nodes.py  # detect_node (Haiku) + compute_node (Sonnet) + apply_node — Pydantic structured output (Lang Refresh)
│   ├── tools/
│   │   ├── memory.py        # Dict en memoria (no persiste a DB)
│   │   └── constraints.py
│   ├── prompts/
│   │   └── system.py        # System prompts (incluye BRIEF_GENERATION_PROMPT, STUDIO_REFINE_PROMPT, SESSION_IMPORT_PROMPT, WRITER_INITIALIZATION_PROMPT)
│   └── evolution/
│       ├── identity.py      # Dataclass Identity con to_dict/from_dict/to_prompt_string
│       ├── diff.py          # Lógica de diff de identidad
│       └── templates.py
│
└── data/
    # (vacío — Postgres corre en el service `db` del compose, datos en volume pg_data)
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

**`studio_sessions`** ← Sprint 6b Slice 1
```
id              PK
writer_id       FK → writers (cascade delete)
brief_json      JSON snapshot del brief original
lifecycle       string   active | complete | imported | skipped | abandoned
created_at
updated_at
```

**`studio_takes`** ← Sprint 6b Slice 1
```
id              PK
session_id      FK → studio_sessions (cascade delete)
take_number     int
iteration_notes nullable
content         text
title           nullable
word_count      int
created_at
```

Slice 2 backend no agregó columnas nuevas de identidad: el origen del import post-sesión queda trazado hoy en `evolution_logs.reason` con el prefijo `[post_session_import session_id=...]`. Slice 4 deriva de ahí `source_session_id` para exponerlo al frontend sin abrir migraciones.

**Checkpoint tables (LangGraph) ← Sprint 6b Slice 3**
- No viven en SQLAlchemy models del producto.
- Las crea/migra `setup_studio_checkpointer()` en startup cuando el runtime usa PostgreSQL.
- Guardan el state interno del Studio graph y su historial de checkpoints por `thread_id = StudioSession.id`.

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
POST   /writers/initialize-preview       → WriterInitializationPreviewResponse   ← Sprint 6b.5
POST   /writers/from-preview             → WriterResponse (201)                  ← Sprint 6b.5
GET    /writers/{id}                     → WriterWithIdentity
GET    /writers/{id}/sessions/summary    → WriterSessionsSummaryResponse   ← Slice 4
PUT    /writers/{id} body: WriterUpdate  → WriterResponse
DELETE /writers/{id}                     → 204
```

### Identity — `/api/writers`
```
GET  /writers/{id}/identity                          → IdentityResponse
PUT  /writers/{id}/identity  body: IdentityUpdate    → IdentityResponse (nueva versión)
PUT  /writers/{id}/constraints body: ConstraintsUpdate → IdentityResponse (nueva versión)
POST /writers/{id}/identity/rollback                 → IdentityResponse (nueva versión copiando N-1)
```

Cada PUT/rollback de identidad crea una nueva fila en `writer_identities` con `version+1`. Nunca hay updates destructivos — el historial queda completo.

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
POST /chat/{id}/studio/stream    body: {brief, session_id?, iteration_notes?} → SSE stream
```

### Sessions — `/api/sessions` ← Sprint 6b Slice 2/4 backend
```
GET  /sessions/{id}                             → SessionDetailResponse
POST /sessions/{id}/abandon                     → SessionAbandonResponse
POST /sessions/{id}/import-proposal              → SessionImportProposalResponse
POST /sessions/{id}/import        body: {changes, reasoning} → SessionImportResponse
POST /sessions/{id}/skip                          → SessionSkipResponse
```

### SSE Event types — chat stream
```json
{"token": "text chunk"}
{"phase": "outlining" | "drafting" | "refining"}
{"done": true, "message_id": 123}
{"evolution_detected": true, "changes": [
  {"field": "emotions", "action": "modify", "key": "melancholy", "old_value": 0.3, "new_value": 0.5, "reason": "..."},
  {"field": "topics", "action": "add", "value": "noir fiction", "reason": "..."}
], "reasoning": "..."}
{"error": "message"}
```

Los eventos de evolución se emiten **después** del `done`. El stream permanece abierto hasta que la evolución completa o el timeout (45s). El frontend puede procesar el `done` inmediatamente (re-habilitar chat UI) y seguir el stream abierto para los eventos de evolución.

### SSE Event types — studio/stream ← Sprint 5
```json
{"session_started": {"session_id": 123}}
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
| `stream_writer_agent()` | Chat conversacional (siempre — sin keyword detection) | `POST /chat/{id}/message/stream` |
| `stream_studio_session()` | Studio con research → outline → draft → refine | `POST /chat/{id}/studio/stream` |

**`stream_studio_session()` ahora es un wrapper delgado sobre `studio_graph`.**
1. Si no viene `session_id`, crea `StudioSession` y yielda `session_started`
2. Compila `build_studio_graph()` con `AsyncPostgresSaver`
3. Usa `thread_id = str(session_id)` para leer el checkpoint actual
4. Si hay trabajo pendiente, reanuda el take actual con `graph.astream(None, config, stream_mode="custom")`
5. Si no hay trabajo pendiente, crea un `StudioTake` nuevo y arranca el graph con input state nuevo
6. Los nodos del graph emiten eventos custom (`phase`, `tool_use`, `tool_result`, `token`) vía `get_stream_writer()`
7. Al terminar, el service persiste `WriterPiece` + actualiza `StudioTake`

**Semántica de resume (Slice 3):**
- Reanuda desde el último nodo completado
- Si el corte ocurre durante un nodo streaming (`research`/`refine`), ese nodo se reinicia al reanudar
- Si el graph ya terminó pero faltó persistir `WriterPiece`, el service materializa la pieza desde el checkpoint final sin rerun del pipeline

### Session import flow ← Sprint 6b Slice 2 backend

- `session_import_service.py` carga `StudioSession` + `StudioTake[]` + identidad actual en una sesión DB corta, validando ownership.
- `POST /sessions/{id}/import-proposal` mueve `active → complete` si hace falta y llama a Claude con `ChatAnthropic.with_structured_output(SessionImportPlan)`.
- El prompt `SESSION_IMPORT_PROMPT` recibe identidad general actual, `brief_json` original y todos los takes en orden (con `iteration_notes`, `title`, `content`).
- `POST /sessions/{id}/import` aplica solo los cambios seleccionados usando `apply_node()` de `evolution_nodes.py` y persiste la nueva `WriterIdentity` vía `persist_identity_changes()`.
- `POST /sessions/{id}/skip` exige `lifecycle = complete` y transiciona a `skipped` sin crear identidad nueva.
- La trazabilidad de origen queda en `evolution_logs.reason` con el prefijo `[post_session_import session_id=...]`, sin abrir columnas nuevas en `writer_identities` en este slice.
- Frontend:
  - `SessionExperience` conserva el `session_id` de la sesión activa y `Finalizar sesión` navega a `/studio/:writerId/import/:sessionId`.
  - `SessionImportPage` llama `POST /sessions/{id}/import-proposal`, renderiza la propuesta con checkboxes y deja importar un subset o skipear explícitamente.
  - `WriterPage` consume `location.state.sessionImportFeedback` para mostrar un banner transitorio al volver desde el import flow.

### Sessions summary / resume UX ← Sprint 6b Slice 4

- `session_query_service.py` concentra la lectura de sesiones para UI:
  - `get_writer_sessions_summary(...)`
  - `get_session_detail(...)`
  - `abandon_session(...)`
- El summary elige un `highlight` para la UI con prioridad `active > complete`.
- `history` excluye `abandoned` por default y trae solo el shape necesario para card + lista.
- `SessionDetailResponse` expone `resume_mode`:
  - `checkpoint` si el checkpointer tiene trabajo pendiente para `thread_id = session.id`
  - `artifact` si el runtime no tiene trabajo pendiente pero el último take ya fue materializado
- Esto evita un bug sutil de Slice 4: sin `resume_mode`, abrir una sesión activa ya materializada desde `WriterPage` podía crear un take nuevo por accidente. Con `artifact`, el frontend abre el último documento existente sin autoarrancar otra iteración.
- `POST /sessions/{id}/abandon` implementa la semántica de `Empezar nueva` desde el gate del Studio.
- `GET /api/evolution/{writer_id}` ahora incluye `source_session_id` derivado server-side para que `EvolutionFeed` linkee a la sesión origen sin regex en React.

### Grafos compilados activos

Grafos compilados activos en runtime:
- **`evolution_graph`** — pipeline 2-stage de identidad vía chat
- **`studio_graph`** — pipeline del Studio con checkpointer persistente

El antiguo `writer_graph.py` (que compilaba un detect_intent + write pipeline) fue borrado en Lang Refresh porque nunca se llamaba. Ver A4 en `LANG_PLAYBOOK.md`.

### Evolution Pipeline (Sprint 6a)

`evolution_service.py::run_evolution()` orquesta el grafo. `persist_evolution()` crea la nueva versión de identidad en una sesión DB corta separada.

```
START → detect_node (Haiku) → [should_evolve?]
                                    ├── no → END (returns None)
                                    └── sí → compute_node (Sonnet) → apply_node (sin LLM) → END
```

**`EvolutionState`** (TypedDict): `current_identity`, `chat_history`, `signal`, `confidence`, `changes`, `reasoning`, `new_identity`

**Structured output (Lang Refresh):** `detect_node` y `compute_node` usan `ChatAnthropic.with_structured_output(PydanticSchema)`. Las schemas (`EvolutionDecision`, `EvolutionPlan`, `EvolutionChange`) viven en `agents/nodes/evolution_nodes.py`. Eliminó por completo `_parse_json_response()` y la familia entera de silent failures por markdown fences (anti-pattern A2 del PLAYBOOK).

### Principio: no SDK directo en el agent layer ✅

**Todo LLM call usa LangChain** (`ChatAnthropic` de `langchain_anthropic`). Sin excepciones.

**Estado actual (post Sprint Lang Refresh):** la regla se cumple en el 100% del agent layer. `chat_node.py`, `writing_nodes.py`, `research_node.py`, `evolution_nodes.py` y `chat_service.py::generate_brief()` usan exclusivamente `ChatAnthropic`. Modelos centralizados en `backend/config.py` (`chat_model`, `writing_model`, `evolution_detect_model`, `evolution_compute_model`).

**Por qué importa:** habilita middleware nativo, content blocks tipados, prompt caching via `cache_control`, y structured output integrado en el loop. Es la base sobre la que se construye Sprint 6b/6c/7.

### research_node — web_search via bind_tools (Lang Refresh)

`agents/nodes/research_node.py` llama a Claude con la built-in `web_search_20250305` via `ChatAnthropic.bind_tools([{"type": "web_search_20250305", "name": "web_search"}])`. La spec del tool vive inline como constante local en el propio nodo (no hay tool registry — A3 del PLAYBOOK).

Eventos SSE emitidos:
- `{"tool_use": ToolUseEvent}` cuando Claude inicia la búsqueda
- `{"tool_result": ToolResultEvent}` con un resumen capeado a 200 chars
- `{"search_results": str}` como evento final (acumulado para el outline)

**Pitfall descubierto en QA:** los built-in tools server-side de Anthropic emiten bloques de tipo `server_tool_use` (no `tool_use`) y la síntesis llega partida en múltiples bloques `text` (algunos con `citations`). `research_node` los reconoce explícitamente y joinea todos los text blocks en un único summary. Reconocemos ambos tipos por compatibilidad.

### chat_node — prompt caching (Lang Refresh)

`agents/nodes/chat_node.py` envía el `ARTIST_PROFILE_CHAT_SYSTEM_PROMPT` como un `SystemMessage` con `content` estructurado:

```python
SystemMessage(content=[{
    "type": "text",
    "text": system_prompt,
    "cache_control": {"type": "ephemeral"},
}])
```

A partir del segundo turno del mismo writer, Anthropic reusa el KV-cache del prefix → ~85% menos latencia, ~90% menos costo en cache hits. Ver D3 en el PLAYBOOK.

### Título generado automáticamente

`studio_refine_node_stream()` instruye al modelo a agregar `---TITLE: <título>---` al final del stream. El backend parsea esto antes de guardar el `WriterPiece`:
- El título se extrae y se usa como `WriterPiece.title`
- El marcador se elimina del contenido antes de guardar

---

## Frontend

### Rutas
```
/writers/new        → WriterInitializationPage (protegida)  ← Sprint 6b.5
/login              → LoginPage
/                   → DashboardPage (protegida)
/writer/:id         → WriterPage (protegida)
/studio/:writerId   → StudioPage (protegida)  ← Sprint 5
/studio/:writerId/import/:sessionId → SessionImportPage (protegida) ← Sprint 6b Slice 2
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
- `writing.css` — Studio views (BriefSetup, WritingArtifact, PiecesLibrary)
- `session.css` — SessionExperience (streaming view, phase pills, tool use pills)

**Regla de imports CSS:** siempre relativo a `src/`, no al directorio del componente:
- Desde `src/pages/`: `import '../writing.css'`
- Desde `src/components/`: `import '../session.css'`

### Componentes clave

| Componente | Qué hace |
|-----------|---------|
| `WriterInitializationPage` | Pantalla dedicada de creacion: descripcion libre -> preview generado -> crear writer |
| `CreateWriterModal` | Modal legacy; ya no monta en el flujo principal de creacion |
| `ConfigPanel` | Artist Profile — character sheet editable (EmotionBar, TraitBadge, ConstraintCard) |
| `EmotionBar` | Barra de progreso animada para valores 0–1 (muestra como %) |
| `TraitBadge` | Badge para traits/topics/objectives con tier colors |
| `ConstraintCard` | Tarjeta individual para cada constraint |
| `ChatPanel` | Chat con SSE streaming, fases del pipeline, botón "Studio →" |
| `EvolutionFeed` | Log de cambios de identidad; en imports post-sesión muestra chip/link a la sesión origen |
| `WriterCard` | Card en el dashboard |
| `BriefSetup` | Brief en 4 estados: input → loading → preview → clarifying. Header con nombre+purpose del writer y notice contextual opcional (Slice 4). |
| `SessionStatusCard` | Card compacta de estado de sesión en WriterPage (`active` / `complete`) con CTAs de retomar o revisar import |
| `SessionHistory` | Historial expandible de sesiones separado de la discografía; carga detalle on-demand |
| `SessionExperience` | Sesión activa: stream + phase pills con `LOADING_TIPS` rotativos (cada 4s) + tool use pill + artifact + navegación al import flow al finalizar. En Slice 4 también puede abrir un artefacto previo sin autoarrancar stream |
| `SessionImportPage` | Pantalla separada de revisión post-sesión: carga proposal, renderiza checkboxes, CTA Importar / Skipear, maneja propuesta vacía |
| `WritingArtifact` | Documento final: título, formato badge, copy, Iterar/Finalizar |
| `IterationInput` | Textarea de notas del productor, relanza el pipeline |
| `PiecesLibrary` | Discografía del writer — lista expandible con fechas en español |

### WriterInitializationPage — free-text setup

- ruta dedicada: `/writers/new`
- estado local + `sessionStorage` para preservar descripcion y preview
- preview generado via Lang `with_structured_output(...)`
- confirmacion final crea `Writer` + `WriterIdentity version=1`
- `purpose`, `personality`, `emotions` y `constraints` son la capa prioritaria del setup inicial
- `topics` y `lifelong_objectives` quedan minimizados; `memories` arrancan vacias

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
    writer-sidebar-col (320px)
      → SessionStatusCard (solo si hay `active`/`complete`)
      → EvolutionFeed
  writer-sessions-shell (debajo del fold)
    → SessionHistory (solo si existe historia real)
```

`WriterPage` usa un scroll event listener sobre `pageRef` para detectar cuando el hero scroll fuera de vista y activar el `writer-rpg-strip`. `ConfigPanel` recibe `onIdentityLoaded` callback para que WriterPage tenga los datos de identidad disponibles para el strip.

`WriterPage` también escucha `location.state.sessionImportFeedback` al volver desde el import flow. Copia ese estado a un banner local dismissible y luego limpia el `location.state` con `replace` para que el mensaje no reaparezca en refresh/back.

**Jerarquía visual de Slice 4:**
- El chat sigue siendo la superficie principal del `Artist Profile`.
- El estado de sesión es visible pero compacto.
- `active` pesa más que `complete`.
- Si el writer no tiene sesiones, no se renderiza ningún bloque nuevo.

### StudioPage — gate de retomar

- Si el summary indica una sesión `active`, `StudioPage` no entra directo al Brief Setup: muestra una puerta de decisión con `Retomar sesión` / `Empezar nueva`.
- `Empezar nueva` llama `POST /sessions/{id}/abandon`, refresca el summary y habilita un brief nuevo.
- Si el summary indica `complete` pero no `active`, `BriefSetup` renderiza un aviso suave con CTA `Revisar import`.
- Si la navegación viene desde `WriterPage` con `resumeSessionId`, `StudioPage` carga el detalle:
  - `resume_mode = checkpoint` → abre `SessionExperience` con `autoStart`
  - `resume_mode = artifact` → abre directamente el último artefacto y sus controles de iteración, sin crear un take nuevo

**Scroll fix (Sprint UX):** Tres partes necesarias para que el scroll arranque en la posición correcta:
1. `overflow-anchor: none` en `.writer-page` — deshabilita el scroll anchoring de Chrome. Sin esto, cuando ConfigPanel crece al cargar la identidad (~400ms), Chrome re-scrollea automáticamente para mantener el chat visible, bypaseando JavaScript.
2. `history.scrollRestoration = 'manual'` en `main.tsx` — previene que el browser restaure posiciones de scroll de divs en navegaciones SPA.
3. Reset de scroll en el effect `[loading]` (no en `[id]`) — el `pageRef` es null mientras `loading=true` (el div no está en el DOM); solo es válido después de que `loading → false`.

### Patrón de CSS para layouts
- Layouts scrollables: el contenedor principal tiene `overflow-y: auto`
- Secciones de altura fija dentro de un layout scroll: usar `height` (no `min-height`) para que los children con `height: 100%` resuelvan correctamente
- CSS de área en archivos separados, imports relativos a `src/`
- Animaciones: CSS keyframes + React state (sin framer-motion)

---

## Lo que existe pero no está activo

| Qué | Dónde | Estado |
|-----|-------|--------|
| `memory` tool | `agents/tools/memory.py` | Dict en memoria, sin persistencia — pendiente Sprint 7 |

---

## Notas técnicas para próximos sprints

**Sprint 5.5 Etapa 2 — CI/CD:**
- `.github/workflows/ci.yml` — tests en cada PR (backend pytest, frontend tsc)
- `.github/workflows/pr_review.yml` — Claude revisa diffs de PRs via Anthropic API
- Railway auto-deploy desde `main` ya está activo (configurado en Etapa 1)

**Sprint 5.5 Etapa 3 — Alembic:** ⏸ DIFERIDA — cuando haya usuarios reales en prod con datos que no podemos borrar.

**Sprint 6a — Identity Evolution via Chat: ✅ COMPLETADO (2026-03-19)**

Puntos clave de la implementación:
- Evolución trigger: post-respuesta del writer en el chat (inline en SSE stream)
- 2-stage approach: detect (Haiku) → compute (Sonnet). Solo corre si detect dice sí.
- Rate limiting: solo corre si el mensaje tiene >15 palabras o hay >3 exchanges sin check
- `_parse_json_response()`: strip de markdown code fences antes de `json.loads()` — Haiku wrapa JSON en ` ```json ``` `; sin este fix el pipeline falla silenciosamente. *(Será reemplazado por structured output via Pydantic en el Sprint Lang Refresh — ver decisión D4 del PLAYBOOK)*
- Timeout: `asyncio.wait_for(run_evolution(), timeout=45)` para prevenir hangs
- `evolution_service.py`: separa LLM calls de sesiones DB (regla de sesión corta)
- Frontend: `onDone` callback re-habilita el chat UI inmediatamente; el stream sigue abierto para `evolution_detected`
- Config panel: actualización silenciosa de identidad en el effect de `pendingEvolution` — NO llama `loadIdentity()` (pondría `loading=true` y ocultaría el Undo banner)

**Sprint UX — UX Polish: ✅ COMPLETADO (2026-03-28)**

Cambios principales:
- Keyword detection eliminada: `stream_writer_agent()` llama directamente a `chat_node`. El chat es siempre conversacional.
- `StudioTransition` componente eliminado: el Studio abre directo en `BriefSetup`.
- `BriefSetup`: header con nombre+purpose del writer agregado.
- `SessionExperience`: array `LOADING_TIPS` con tips rotativos cada 4s durante las fases.
- `WriterPage` scroll fix: `overflow-anchor: none` + `scrollRestoration: manual` + reset en effect `[loading]`.
- `ChatPanel` scroll isolation fix.

**Sprint Lang Refresh — Refactor técnico fundacional: ✅ COMPLETADO (2026-04-07)**

Plan original en `SPRINT_LANG_REFRESH.md`. Razonamiento del ecosistema en `LANG_PLAYBOOK.md`.

Lo que se hizo (sin cambios funcionales — 100% refactor):
- ✅ Bump `langchain>=1.0,<2`, `langgraph>=1.0,<2`, `langchain-anthropic>=0.3.20`
- ✅ Modelos centralizados en `backend/config.py` (`chat_model`, `writing_model`, `evolution_detect_model`, `evolution_compute_model`)
- ✅ `evolution_nodes` migrado a `ChatAnthropic` + Pydantic structured output (`EvolutionDecision`, `EvolutionPlan`, `EvolutionChange`). `_parse_json_response()` borrado.
- ✅ `chat_node` migrado a `ChatAnthropic` con prompt caching del system prompt via `cache_control` en content blocks
- ✅ `writing_nodes` (outline/draft/refine + studio_refine_stream) migrado a `ChatAnthropic`
- ✅ `research_node` migrado a `ChatAnthropic.bind_tools` con la built-in `web_search_20250305`
- ✅ `chat_service.generate_brief()` migrado a `ChatAnthropic.with_structured_output(BriefResponse)`
- ✅ Borrado: `agents/graphs/writer_graph.py`, `agents/tools/registry.py`, `agents/tools/web_search.py`, `agents/tests/test_registry.py`
- ✅ Tests rewriteados para mockear `ChatAnthropic` en lugar del SDK directo. 26/26 pasando.

**Learnings clave del sprint:**
- **Built-in tools server-side de Anthropic** emiten `server_tool_use` (no `tool_use`) y reciben sus resultados como `web_search_tool_result`. La síntesis del modelo llega partida en múltiples bloques `text` (algunos con `citations`). El parser de `research_node` joinea todos los text blocks. Descubierto haciendo QA con Playwright cuando el primer Studio test "Indian Wells 2026" salió como "no puedo escribir esto" — el web search no firaba porque buscábamos el block type equivocado.
- **Prompt caching via content blocks**, no `additional_kwargs`. El pattern correcto es `SystemMessage(content=[{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}])`. El P1 del PLAYBOOK fue corregido en este sprint.
- **`with_structured_output` con LangChain 1.x no agrega un LLM call extra** — usa tool-use under the hood en una sola pasada. Validado en `evolution_nodes` y `generate_brief`.

Por qué este sprint primero: desbloquea Sprint 6b (LangGraph 1.x checkpointer + store), Sprint 6c (LangSmith evals) y Sprint 7 (LangMem). Toda la base sobre la que se construye lo que viene.

**Sprint 6b — Session Snapshot + Writer Initialization:**
- Session snapshot: fork de identidad al entrar al Studio. **Implementación: LangGraph checkpointer (Postgres en prod, SQLite en local) + Store namespaces** — el thread state mantiene el fork, el Store namespace `writers/{id}/sessions/{session_id}` mantiene los artefactos. Ver decisión D8 del PLAYBOOK.
- Import post-sesión: el usuario puede importar stats de la sesión al general — implementado moviendo entries del namespace de la sesión al namespace del general.
- Writer initialization flow: descripción libre → LLM genera identity inicial ("quiero un escritor tipo GRRM"). **Empezar simple** (un LLM call estructurado con Pydantic). Si la calidad se queda corta, refactor a deepagents en una iteración posterior — no prematurice. Ver decisión D9.

**Sprint 6c — LangSmith + Evolution Evals:**

Visibilidad sistemática de la calidad del feature diferenciador del producto. Sin esto, escalar es a ciegas.

Setup mínimo:
- LangSmith account + env vars (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`)
- Tracing automático en el agent layer (auto via `ChatAnthropic` cuando las env vars están seteadas)
- Dataset inicial: ~30 conversaciones reales etiquetadas manualmente (`should_evolve` sí/no, qué cambios serían razonables)
- 2 evaluators tipo LLM-as-judge:
  - **`detect_correctness`** — ¿la decisión `should_evolve` está alineada con la etiqueta del dataset?
  - **`compute_coherence`** — dado el `signal`, ¿los cambios propuestos son coherentes y graduales (no rewrites)?
- Online evals en producción con alertas si la calidad cae por debajo de un threshold

Ver decisión D6 del PLAYBOOK.

**Sprint 7 — Memory System (con LangMem):**

Reemplaza el plan original de "construir desde cero". **Adoptamos LangMem SDK** como base: episodic memory (sesiones del Studio como experiencias narrativas), semantic memory (facts del writer), procedural memory (patrones de estilo aprendidos). Ver decisión D7.

El campo `memories` en `writer_identities` ya existe pero hoy no se usa — Sprint 7 lo activa modelando sobre LangMem, no inventando una memoria nueva. Trabajo del sprint: modelar nuestro dominio sobre LangMem (qué namespaces usamos, cómo se popula desde el Studio, cómo se inyecta al chat), no construir la infraestructura de memoria.

**Candidato natural para D1:** Sprint 7 es donde finalmente migraríamos `chat_node` a `create_agent` con un memory tool nativo, porque ahí el chat tiene una herramienta real que justifica el cambio.

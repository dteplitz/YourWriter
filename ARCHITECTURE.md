# YourWriter — Arquitectura Técnica

*Documento vivo. Se actualiza al final de cada sprint con lo que fue construido o modificado.*
*Última actualización: 2026-04-07 — notas técnicas reorganizadas tras research del ecosistema Lang. Para el contexto completo de decisiones sobre LangChain/LangGraph/LangMem, ver `LANG_PLAYBOOK.md`.*

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

**Producción:**
- URL: `https://yourwriter-production.up.railway.app`
- Platform: Railway (monorepo, single service)
- DB: PostgreSQL managed (Railway)
- Deploy: auto-deploy en push a `main`

**Para correr la app (local):**
```bash
bash dev.sh          # arranca docker compose up --build
```
Requiere Docker Desktop corriendo. Primera vez tarda ~2 min (build de imágenes). Las siguientes arrancan rápido.

Cuando ves esto, está listo:
```
backend-1   | INFO:     Application startup complete.
frontend-1  | VITE ready in ... Local: http://localhost:3000/
```

- `Ctrl+C` para parar. `docker compose down` para limpiar contenedores.
- Hot reload activo: cambios en `.py` recargan el backend, cambios en `.tsx/.ts` recargan el frontend.
- Los datos de SQLite persisten en `./data/` entre sesiones (volume mount).

**Ambientes:**
| | Local | Railway (prod) |
|---|---|---|
| Cómo arranca | `bash dev.sh` → docker compose | auto-deploy desde push a `main` |
| Backend | uvicorn `--reload`, source montado | uvicorn, source baked en imagen |
| Frontend | vite dev HMR en :3000 | static files servidos por FastAPI |
| DB | SQLite en `./data/` | PostgreSQL (Railway managed) |
| Env vars | `.env` local | Variables de entorno en Railway |

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
│   │   ├── studio.py        # BriefRequest, BriefResponse, PieceResponse (Sprint 5)
│   │   └── evolution.py     # EvolutionEvent, EvolutionResult Pydantic schemas (Sprint 6a)
│   └── services/            # Business logic (writer_service, chat_service, user_service)
│       └── evolution_service.py  # run_evolution() + persist_evolution() (Sprint 6a)
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
│   │   └── evolution_graph.py # Grafo de evolución 2-stage: detect → compute → apply (Sprint 6a)
│   ├── nodes/
│   │   ├── chat_node.py     # Nodo de chat conversacional
│   │   ├── writing_nodes.py # outline_node, draft_node, refine_node, studio_refine_node_stream
│   │   ├── research_node.py # research_node_stream: web_search_20250305 con SSE (Sprint 5)
│   │   └── evolution_nodes.py  # detect_node (Haiku) + compute_node (Sonnet) + apply_node (Sprint 6a)
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

*Sprint 6b agregará `session_config JSON` para guardar el fork de identidad de la sesión y permitir import post-sesión.*

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
POST /chat/{id}/studio/stream    body: {brief}    → SSE stream                [Sprint 5]
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

**`stream_studio_session()` NO usa el grafo compilado.** Orquesta manualmente:
1. `research_node_stream()` → yielda tool_use/tool_result, acumula search_results
2. `outline_node(state)` → genera outline
3. `draft_node(state)` → genera draft
4. `studio_refine_node_stream(state)` → streama tokens + parsea `---TITLE: <title>---` al final
5. Guarda `WriterPiece` en sesión corta → yielda evento `{"piece": {...}}`

### writer_graph (LangGraph)

`stream_writer_agent()` llama a `chat_node` directamente — el grafo compilado con `detect_intent_node` ya no se usa en el path de chat. El writer siempre responde como conversación; el Studio es el canal exclusivo para escritura.

```
[legacy graph — ya no se llama en runtime]
START
  └─► detect_intent_node (word-boundary regex sobre keywords de escritura)
        ├─ mode="chat"  ──────────────────────────────► chat_node ──► END
        └─ mode="write" ──► outline_node ──► draft_node ──► refine_node ──► respond_node ──► END
```

**Sprint UX:** `detect_intent_node` eliminado del path activo. `ARTIST_PROFILE_CHAT_SYSTEM_PROMPT` define el sistema prompt del writer en el chat. `stream_writer_agent()` llama directamente a `chat_node`.

### Evolution Pipeline (Sprint 6a)

`evolution_service.py::run_evolution()` orquesta el grafo. `persist_evolution()` crea la nueva versión de identidad en una sesión DB corta separada.

```
START → detect_node (Haiku) → [should_evolve?]
                                    ├── no → END (returns None)
                                    └── sí → compute_node (Sonnet) → apply_node (sin LLM) → END
```

**`EvolutionState`** (TypedDict): `current_identity`, `chat_history`, `signal`, `confidence`, `changes`, `reasoning`, `new_identity`

**Pitfall crítico resuelto:** Haiku y Sonnet pueden envolver el JSON en ` ```json\n...\n``` `. `_parse_json_response()` en `evolution_nodes.py` hace strip de las fences antes de `json.loads()`.

### Principio: no SDK directo en el agent layer

**Todo LLM call usa LangChain** (`ChatAnthropic` de `langchain_anthropic`). Sin excepciones.

**Estado actual (pre Sprint Lang Refresh):** la regla está incumplida en la mayoría de los nodos. Solo `evolution_nodes.py` la respeta. `chat_node.py`, `writing_nodes.py`, `research_node.py` y `chat_service.py::generate_brief()` usan `anthropic.AsyncAnthropic()` directamente. Esta deuda se salda completa en el Sprint Lang Refresh — ver `SPRINT_LANG_REFRESH.md` y la decisión D2 del `LANG_PLAYBOOK.md`.

**Por qué importa:** sin esta consistencia no podemos usar middleware nativo, content blocks tipados, prompt caching via `cache_control` en `SystemMessage`, ni structured output integrado en el loop. Es la base que habilita Sprint 6b/6c/7.

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
- `writing.css` — Studio views (BriefSetup, WritingArtifact, PiecesLibrary)
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
| `BriefSetup` | Brief en 4 estados: input → loading → preview → clarifying. Header con nombre+purpose del writer. |
| `SessionExperience` | Sesión activa: stream + phase pills con `LOADING_TIPS` rotativos (cada 4s) + tool use pill + artifact |
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
| `web_search.py` | `agents/tools/` | STUB — reemplazado por `registry.py` + `research_node.py` |

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

**Sprint Lang Refresh — Refactor técnico fundacional (📋 PRÓXIMO):**

Plan completo en `SPRINT_LANG_REFRESH.md`. Razonamiento del ecosistema en `LANG_PLAYBOOK.md`.

Resumen del scope (sin cambios funcionales — 100% refactor):
- Bumpear `langchain` y `langgraph` a 1.x (ambos tienen GA desde oct 2025)
- Migrar `chat_node`, `writing_nodes`, `research_node` y `chat_service.generate_brief()` de `anthropic.AsyncAnthropic()` directo a `ChatAnthropic` (saldar la deuda flagueada arriba)
- Activar prompt caching del system prompt del writer via `cache_control` en `SystemMessage` (impacto: ~85% menos latencia, ~90% menos costo desde el mensaje 2 del chat)
- Reemplazar `_parse_json_response()` por structured output via Pydantic schemas en `compute_node` y `detect_node` (eliminar silent failures por markdown fences)
- Centralizar modelos hardcodeados en `backend/config.py` (`chat_model`, `evolution_detect_model`, `evolution_compute_model`, `studio_model`)
- Borrar código muerto: `agents/graphs/writer_graph.py` (compilado pero no ejecutado), `agents/tools/registry.py` (reemplazado por `bind_tools` nativo), `agents/tools/web_search.py` (stub)

**Por qué este sprint primero:** las versiones desactualizadas y la deuda técnica del SDK directo bloquean Sprint 6b (que necesita LangGraph 1.x para checkpointer + store), Sprint 6c (LangSmith para evals) y Sprint 7 (LangMem). Sin Lang Refresh, los próximos sprints construyen sobre base inestable.

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

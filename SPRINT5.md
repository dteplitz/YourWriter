# Sprint 5 — Writing Experience: Artist Profile + Studio

**Estado:** Refinado y listo para implementar
**Fecha de planning:** 2026-03-16
**Branch a crear:** `feature/writing-experience`

---

## El modelo mental del producto

Después del Sprint 4 (character sheet), el producto tiene dos modos claramente diferenciados:

### Artist Profile — gestión del artista
Todo lo que ya tenemos: el character sheet, personalidad, emociones, constraints, lifelong objectives.
Es el espacio de management. Como en Football Manager: armás la formación, definís la táctica, desarrollás al jugador.
La configuración tiene peso propio — no es un formulario de admin, es arquitectar un sistema creativo.

### Studio — la sesión de grabación
La experiencia activa de escritura. Separada visualmente del Artist Profile. Se *entra* al Studio — hay una transición.
Es la sesión de grabación: el productor y el artista acuerdan qué grabar, el artista ejecuta con su personalidad propia, el productor da notas, se vuelve a grabar. El artefacto final va a la discografía.

**El partido no es el chat. El partido es la sesión.**

---

## Flujo completo (lo que construimos en Sprint 5)

```
Artist Profile
  └─ [Botón "Entrar al Studio"] ─────────────────────────────────┐
                                                                   ↓
                                                    Transición animada
                                                    (writer state: mood, constraints, última pieza)
                                                                   ↓
                                                    Studio — Brief Setup (pre-producción)
                                                    "¿Qué grabamos hoy?"
                                                    [Confirmar] ──────────────────────────┐
                                                                                           ↓
                                                                             Sesión activa
                                                                             [Fases visibles: arranging → raw take → mix]
                                                                             [Web search visible: pastilla animada]
                                                                             [Primer artefacto aparece como documento]
                                                                                           ↓
                                                                             Loop de iteración
                                                                             "Notes" del productor
                                                                             [Nuevo take] ─────► artefacto actualizado
                                                                                           ↓
                                                                             [Finalizar sesión]
                                                                             Pieza guardada → Discografía
```

---

## Decisiones técnicas

| # | Decisión | Elegida | Descartada |
|---|----------|---------|------------|
| 1 | Web search | **Claude built-in** (`web_search_20250305`) via Tool Registry | Tavily |
| 2 | Tool architecture | **Tool Registry general** (`agents/tools/registry.py`) — extensible, agregar tools = una entrada en el dict | Tool hardcodeada |
| 3 | Studio trigger | **Botón explícito** "Entrar al Studio" | Keyword detection en el chat |
| 4 | Brief UX | **Pantalla de pre-producción** en el Studio (form/card), no burbuja de chat | Brief inline en chat |
| 5 | Studio view | **Vista separada** con transición animada (`/studio/:writerId`) | Transformación in-place del chat |
| 6 | Guardar pieza | **Buffering** en `stream_writer_agent` — acumular tokens del refine, guardar al finalizar | Nodo polish separado |
| 7 | Título de pieza | **Instrucción en el prompt** de refine — terminar con `---TITLE: <título>---`, parsear y separar | LLM call separada post-escritura |

---

## Estado actual del codebase (verificado 2026-03-16)

### Lo que existe y NO hay que tocar
- `agents/graphs/writer_graph.py` — `detect_intent_node` (ya no lo usamos para el trigger, pero queda para el chat mode)
- `agents/nodes/writing_nodes.py` — outline, draft, refine, refine_stream
- `agents/nodes/chat_node.py` — chat y chat_stream
- SSE streaming en `backend/api/routes/chat.py` — existe con phase events
- `backend/services/chat_service.py::stream_writer_agent()` — orquesta los nodos manualmente

### Lo que existe pero hay que modificar
- `agents/tools/web_search.py` — stub, reemplazar con Tool Registry real
- `backend/services/chat_service.py` — agregar buffering + save piece + yield piece event
- `frontend/src/components/ChatPanel.tsx` — agregar botón "Entrar al Studio"

### Lo que NO existe (hay que construir)
- `agents/tools/registry.py` — Tool Registry general
- `agents/nodes/research_node.py` — nodo de research usando el registry
- `backend/db/models.py::WriterPiece` — modelo DB
- `backend/api/routes/chat.py` — endpoint `/brief`
- `backend/api/routes/writers.py` — endpoints `/pieces`
- SSE event types `tool_use` y `piece`
- `frontend/src/pages/StudioPage.tsx` — vista del Studio
- `frontend/src/components/StudioTransition.tsx` — pantalla de transición
- `frontend/src/components/BriefSetup.tsx` — pre-producción
- `frontend/src/components/SessionExperience.tsx` — la sesión activa
- `frontend/src/components/WritingArtifact.tsx` — el artefacto como documento
- `frontend/src/components/IterationInput.tsx` — "notes del productor"
- `frontend/src/components/PiecesLibrary.tsx` — discografía

---

## Contratos (definir en main antes de lanzar agentes en paralelo)

### 1. DB Model — WriterPiece

```python
class WriterPiece(Base):
    __tablename__ = "writer_pieces"
    id: int (PK)
    writer_id: int (FK → Writer, cascade delete)
    title: str          # parseado del output del LLM (---TITLE: ...--)
    content: str        # texto completo sin el bloque de título
    format: str         # "tweet", "blog_post", "email", "story", "other"
    word_count: int
    created_at: datetime
```

### 2. Tool Registry

```python
# agents/tools/registry.py
@dataclass
class WriterTool:
    name: str
    display_name: str        # para el pill SSE: "Buscando..."
    anthropic_type: str | None   # "web_search_20250305" para built-ins
    executor: Callable | None    # para tools custom futuras

TOOL_REGISTRY: dict[str, WriterTool] = {
    "web_search": WriterTool(
        name="web_search",
        display_name="Buscando",
        anthropic_type="web_search_20250305",
        executor=None,  # built-in, Anthropic lo maneja
    ),
    # Sprint 6+: "memory_lookup", "read_piece", etc.
}
```

### 3. Brief Schema

```python
class BriefResponse(BaseModel):
    format: str
    tone: str
    constraints_applied: list[str]
    word_limit: int | None
    notes: str | None
    needs_clarification: bool
    clarification_question: str | None
```

```typescript
interface Brief {
  format: string
  tone: string
  constraints_applied: string[]
  word_limit?: number
  notes?: string
  needs_clarification: boolean
  clarification_question?: string
}
```

### 4. Piece Schema

```python
class PieceResponse(BaseModel):
    id: int
    writer_id: int
    title: str
    content: str
    format: str
    word_count: int
    created_at: datetime
```

### 5. SSE Event Types

```typescript
// Existentes (no cambiar):
{"token": "text chunk"}
{"phase": "outlining" | "drafting" | "refining"}
{"done": true, "message_id": 123}
{"error": "message"}

// Nuevos Sprint 5:
{"tool_use": {"name": "web_search", "display_name": "Buscando", "query": "iPhone 16 specs"}}
{"tool_result": {"name": "web_search", "summary": "..."}}   // opcional
{"piece": {"id": 12, "title": "Tweet sobre iPhone 16", "content": "...", "format": "tweet", "word_count": 42}}
```

### 6. Endpoints nuevos

```
POST /api/chat/{writer_id}/brief
  Body: {"message": "escribime un tweet sobre el lanzamiento del iPhone 16"}
  Response: BriefResponse

GET /api/writers/{writer_id}/pieces
  Response: list[PieceResponse]

GET /api/writers/{writer_id}/pieces/{piece_id}
  Response: PieceResponse
```

---

## Slices de implementación

### Slice 1 — Backend: DB + Endpoints + Save Piece
**Archivos:** `backend/db/models.py`, `backend/api/routes/chat.py`, `backend/api/routes/writers.py`, `backend/schemas/`, `backend/services/chat_service.py`

1. Agregar `WriterPiece` a models.py + migration (verificar si hay Alembic o create_all)
2. Agregar `BriefResponse` y `PieceResponse` a schemas
3. Implementar `POST /brief`:
   - Carga identity del writer
   - Llama Claude con prompt dedicado (brief generation)
   - Retorna BriefResponse
4. Implementar `GET /pieces` y `GET /pieces/{id}`
5. Modificar `stream_writer_agent()`:
   - Buffear tokens del refine stream
   - Parsear `---TITLE: <título>---` al final del output
   - Al terminar: guardar `WriterPiece` en DB (sesión short-lived)
   - Yield event `{"piece": {...}}` al final

**Nota SQLite crítica:** Todo el buffering es en memoria. La sesión de DB para guardar la pieza abre y cierra después del stream — nunca durante las LLM calls.

### Slice 2 — Backend: Tool Registry + Research Node
**Archivos:** `agents/tools/registry.py`, `agents/tools/web_search.py`, `agents/nodes/research_node.py`, `backend/services/chat_service.py`

1. Crear `registry.py` con `WriterTool` dataclass y `TOOL_REGISTRY`
2. Reemplazar stub de `web_search.py` — ahora es un wrapper thin sobre el registry
3. Crear `research_node.py`:
   - Llama Anthropic SDK directamente con `tools` del registry (no LangGraph aquí)
   - El writer decide si necesita buscar
   - Si busca: yield `{"tool_use": {...}}` y `{"tool_result": {...}}`
   - Devuelve `{"search_results": [...]}` para pasar al outline_node como contexto
4. Integrar research_node en `stream_writer_agent()` antes del outline

### Slice 3 — Frontend: Studio View + Transición + Brief Setup
**Archivos:** `frontend/src/pages/StudioPage.tsx`, `frontend/src/components/StudioTransition.tsx`, `frontend/src/components/BriefSetup.tsx`, `frontend/src/api/client.ts`, router

1. Agregar ruta `/studio/:writerId` al router
2. `StudioTransition`: pantalla animada de entrada
   - Nombre del writer + estado emocional actual (de identity)
   - Constraints activos para esta sesión
   - Última pieza (si existe) — continuidad
   - CTA para pasar al Brief
3. `BriefSetup`: pantalla de pre-producción
   - Input: "¿qué querés escribir?" (texto libre)
   - Llama `POST /brief` → muestra format, tone, constraints aplicados
   - Si `needs_clarification`: muestra la pregunta del writer
   - CTA "Comenzar sesión" → lanza el stream
4. Botón "Entrar al Studio" en el Artist Profile (ChatPanel o sidebar)

### Slice 4 — Frontend: Session Experience + Artifact + Iteration
**Archivos:** `frontend/src/components/SessionExperience.tsx`, `frontend/src/components/WritingArtifact.tsx`, `frontend/src/components/IterationInput.tsx`, `frontend/src/components/PiecesLibrary.tsx`, `frontend/src/writing.css`

1. `SessionExperience`: orquesta el stream SSE
   - Muestra fases ("Armando estructura", "Primer take", "Mezclando")
   - Parsea evento `tool_use` → pill animada "Buscando: query..."
   - Parsea evento `piece` → renderiza `WritingArtifact`
2. `WritingArtifact`: el artefacto como documento (no burbuja)
   - Título, format badge, word count
   - Contenido con tipografía diferenciada
   - Acciones: Copiar, Iterar, "No era esto"
3. `IterationInput`: canal de feedback sobre el artefacto
   - Aparece después del primer take
   - Input de "producer notes": "más oscuro", "menos formal"
   - Lanza un nuevo stream con el contexto del draft anterior
4. `PiecesLibrary`: tab o panel — carga `/pieces`, lista la discografía
5. `writing.css` — estilos del Studio (dark, focused, distinto al Artist Profile)

---

## Consideraciones visuales

### Transición al Studio
```
[fade a negro] → [aparece: "STUDIO · Writer Name"] → [estado emocional, constraints] → [entrar]
```
Animación: 800-1200ms, no debe sentirse como loading — debe sentirse como entrar a algo.

### Tool use pill
```
[ ◉ Buscando: "iPhone 16 lanzamiento Argentina"... ]
```
Pulse mientras busca, fade a check + summary cuando termina.

### Writing Artifact
```
┌──────────────────────────────────────────────┐
│  TWEET  ·  42 palabras                        │
│                                               │
│  El iPhone 16 llega con [...]                 │
│  [texto completo de la pieza]                 │
│                                               │
│  [Copiar]  [Iterar]  [No era esto]            │
└──────────────────────────────────────────────┘
```
Fondo distinto a las burbujas, borde con accent color, tipografía más grande.

### Brief Setup (pre-producción)
```
┌──────────────────────────────────────────────┐
│  ✍  ¿Qué grabamos hoy?                       │
│                                               │
│  [___________________________________]        │
│                                               │
│  Formato     Tweet                            │
│  Tono        Confiado, directo                │
│  Límite      280 caracteres                   │
│  Activos:    audience: tech enthusiasts       │
│                                               │
│  [Comenzar sesión]                            │
└──────────────────────────────────────────────┘
```

---

## Backlog relacionado (NO este sprint)

**Sprint 6 — Identity Evolution**
- Al completar una pieza: trigger del evolution graph
- El writer evoluciona de tres fuentes: pieza escrita + conversación + tools usados
- Memoria imperfecta por diseño
- El character sheet muestra barras animándose cuando cambian los valores

**Sprint 6+ — Tools adicionales**
- Agregar tools al registry: `memory_lookup`, `read_piece`
- El research_node ya soporta el registry — agregar tools = una entrada en el dict

**Sprint 6 — Writer Initialization Flow**
- Campo de descripción libre al crear writer ("quiero un escritor tipo GRRM")
- LLM parsea y genera identity inicial estructurada

---

## Cómo arrancar la próxima sesión

1. Leer este archivo y `LINEAGE.md` (el por qué detrás de las decisiones de diseño)
2. Explorar los archivos clave listados arriba — no confiar en este doc para el código
3. Crear branch `feature/writing-experience`
4. Verificar si el proyecto usa Alembic o `create_all` para migrations (`backend/db/`)
5. Slice 1 y Slice 2 arrancan en paralelo una vez definidos los contratos en main
6. Slices 3 y 4 pueden arrancar en paralelo después de Slice 1 (necesitan los endpoints)

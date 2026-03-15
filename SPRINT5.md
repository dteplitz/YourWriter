# Sprint 5 — Writing Experience

**Estado:** Planificado, listo para implementar
**Fecha de planning:** 2026-03-15
**Branch a crear:** `feature/writing-experience`

---

## Contexto y motivación

El producto actual es un chat con config. El writer produce texto brillante (outline → draft → refine → polish) pero el resultado aparece como una burbuja de chat más — se pierde el artefacto. No hay distinción visual entre "esto es una respuesta conversacional" y "esto es el texto que el writer produjo".

**Referencia de inspiración:** `../ShortStoryTelledDeepAgentMoltbook` (Muse)
- Muse es un agente autónomo que escribe para sí mismo. YourWriter es colaborativo — escribe para el usuario.
- Lo que rescatamos de Muse: artifact display, tool use visible, memory imperfecta por diseño.
- Lo que mejoramos: la evolución es bidireccional (escritura + conversación + tools), el usuario está en el loop.

**El arco completo que queremos:**
```
Usuario pide algo → Brief Card (writer clarifica si hace falta)
→ Writer busca en internet [visible, diseñado — pastilla animada]
→ Pipeline corre [fases visibles fuera del chat]
→ Artefacto aparece como documento (no burbuja)
→ Usuario reacciona (le gustó, itera, "no era esto")
→ Writer evoluciona de todo eso (Sprint 6)
```

---

## Decisiones técnicas tomadas (2026-03-15)

| # | Decisión | Elegida | Descartada |
|---|----------|---------|------------|
| 1 | Web search | **Claude built-in** (`web_search_20250305`) — cero dependencias | Tavily (requiere API key externa) |
| 2 | Brief flow | **Two-step**: `/brief` endpoint → Brief Card → usuario confirma → `/stream` | Brief inline en chat (ensucia el flujo) |
| 3 | Dónde viven las piezas | **En chat** (card de documento, no burbuja) + **biblioteca lateral** | Panel principal separado |

---

## Estado actual del codebase (research 2026-03-15)

### Lo que ya existe y NO hay que tocar

- `agents/graphs/writer_graph.py` — ya ruteaba chat vs write via `detect_intent_node` (keywords: write, draft, compose, story...)
- `agents/nodes/writing_nodes.py` — outline, draft, refine, refine_stream
- `agents/nodes/chat_node.py` — chat y chat_stream
- SSE streaming en `backend/api/routes/chat.py` — ya existe con phase events
- `backend/services/chat_service.py::stream_writer_agent()` — orquesta manualmente los nodos para streaming

### Lo que existe pero está incompleto

- `agents/tools/web_search.py` — **STUB**, retorna mock data, NO está conectado a ningún graph node
- `agents/tools/memory.py` — dict en memoria, NO persiste a DB
- `agents/graphs/evolution_graph.py` — grafo existe, NUNCA se dispara
- `agents/evolution/identity.py` — dataclass Identity con to_dict/from_dict/to_prompt_string

### Lo que NO existe (hay que construir)

- Modelo DB `WriterPiece` — no existe
- Endpoint `/brief` — no existe
- Endpoint `/pieces` — no existe
- Web search real conectado al pipeline — no existe
- SSE event types `tool_use` y `piece` — no existen
- Artifact display en frontend — no existe
- Pieces library en frontend — no existe

### Archivos clave para este sprint

**Backend:**
- `backend/db/models.py` — agregar `WriterPiece`
- `backend/api/routes/chat.py` — agregar `/brief`, modificar stream para `tool_use` y `piece` events
- `backend/services/chat_service.py` — modificar `stream_writer_agent()` para web search + guardar pieza
- `backend/schemas/` — agregar schemas para brief y piece

**Agents:**
- `agents/tools/web_search.py` — reemplazar stub con Claude built-in tool
- `agents/nodes/writing_nodes.py` — integrar web search antes del outline
- `agents/prompts/system.py` — prompt para generación de brief

**Frontend:**
- `frontend/src/components/ChatPanel.tsx` — parsear eventos `tool_use` y `piece`, Brief Card flow
- `frontend/src/api/client.ts` — agregar llamadas a `/brief` y `/pieces`
- Nuevo: `frontend/src/components/BriefCard.tsx`
- Nuevo: `frontend/src/components/WritingArtifact.tsx`
- Nuevo: `frontend/src/components/PiecesLibrary.tsx`
- `frontend/src/config-panel.css` o nuevo `writing.css`

---

## Contratos nuevos (definir en main antes de lanzar agentes en paralelo)

### 1. DB Model — WriterPiece

```python
class WriterPiece(Base):
    __tablename__ = "writer_pieces"
    id: int (PK)
    writer_id: int (FK → Writer, cascade delete)
    title: str          # auto-generado por el LLM
    content: str        # texto completo de la pieza
    format: str         # "tweet", "blog_post", "email", "story", "other"
    word_count: int
    created_at: datetime
```

### 2. Brief Schema

```typescript
// Response de POST /api/chat/{writer_id}/brief
interface Brief {
  format: string           // "tweet" | "blog post" | "email" | "story" | "other"
  tone: string             // descripción del tono inferido de las emociones del writer
  constraints_applied: string[]  // constraints relevantes que se van a aplicar
  word_limit?: number      // si hay word_count constraint
  notes?: string           // aclaraciones del writer ("voy a necesitar buscar info sobre X")
  needs_clarification: boolean   // si el writer necesita más info antes de arrancar
  clarification_question?: string
}
```

```python
# Pydantic — BriefResponse
class BriefResponse(BaseModel):
    format: str
    tone: str
    constraints_applied: list[str]
    word_limit: int | None
    notes: str | None
    needs_clarification: bool
    clarification_question: str | None
```

### 3. Piece Schema

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

### 4. SSE Event Types nuevos

```typescript
// Existentes (no cambiar):
{"token": "text chunk"}
{"phase": "outlining" | "drafting" | "refining"}
{"done": true, "message_id": 123}
{"error": "message"}

// Nuevos Sprint 5:
{"tool_use": {"name": "web_search", "query": "iPhone 16 specs"}}
{"tool_result": {"name": "web_search", "summary": "..."}}   // opcional, para mostrar resultado
{"piece": {"id": 12, "title": "Tweet sobre iPhone 16", "content": "...", "format": "tweet", "word_count": 42}}
```

### 5. Endpoints nuevos

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

### Slice 1 — Backend: DB + Endpoints (sin web search)
**Archivos:** `backend/db/models.py`, `backend/api/routes/chat.py`, `backend/schemas/`, `backend/services/chat_service.py`

1. Agregar `WriterPiece` a models.py
2. Agregar `BriefResponse` y `PieceResponse` a schemas
3. Implementar `POST /brief`:
   - Carga identity del writer
   - Llama Claude con prompt dedicado (brief generation)
   - Retorna BriefResponse
4. Implementar `GET /pieces` y `GET /pieces/{id}`
5. Modificar `stream_writer_agent()` para:
   - Al finalizar pipeline de escritura: guardar `WriterPiece` en DB
   - Yield event `{"piece": {...}}` al final del stream

### Slice 2 — Backend: Web Search
**Archivos:** `agents/tools/web_search.py`, `agents/nodes/writing_nodes.py`, `backend/services/chat_service.py`

1. Reemplazar stub con Claude built-in `web_search_20250305` tool
2. Agregar nodo `research_node` en el write path (antes de outline):
   - El writer decide si necesita buscar según el request
   - Si busca: yield `{"tool_use": {...}}` event
3. Pasar resultados de search al outline_node como contexto

**Nota SQLite crítica:** El research node hace llamadas LLM — no puede tener DB session abierta. Seguir el mismo patrón que el streaming actual: sessions short-lived, cerrar antes de LLM calls.

### Slice 3 — Frontend: Brief Card + Two-step flow
**Archivos:** `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/BriefCard.tsx`, `frontend/src/api/client.ts`

1. Agregar `api.getBrief(writerId, message)` en client.ts
2. Lógica en ChatPanel: al enviar mensaje, detectar si es probable escritura (keywords) y llamar `/brief` primero
3. Componente `BriefCard`: muestra format, tone, constraints, botones "Escribir" / "Ajustar"
4. Si usuario confirma: llamar `/stream` con el mensaje original
5. Si `needs_clarification: true`: mostrar pregunta del writer en el chat directamente

### Slice 4 — Frontend: Artifact Display + Tool Visibility
**Archivos:** `frontend/src/components/ChatPanel.tsx`, `frontend/src/components/WritingArtifact.tsx`, `frontend/src/components/PiecesLibrary.tsx`

1. Parsear evento `{"tool_use": {...}}` → pastilla animada en chat ("Buscando: query...")
2. Parsear evento `{"piece": {...}}` → render como `WritingArtifact` (no burbuja)
3. `WritingArtifact`: card de documento con título, contenido, format badge, acciones (copiar, iterar)
4. `PiecesLibrary`: panel o tab lateral que carga `/pieces` y lista historial
5. Agregar CSS en `frontend/src/writing.css` (nuevo archivo, mismo patrón que config-panel.css)

---

## Consideraciones de diseño visual

**Tool use pill:**
```
[ 🔍 Buscando: "iPhone 16 lanzamiento Argentina"... ]
```
Animación: pulse mientras busca, fade a result summary cuando termina.

**Writing Artifact:**
```
┌──────────────────────────────────────────┐
│  TWEET  ·  42 palabras                   │
│                                          │
│  El iPhone 16 llega con [...]            │
│  [texto completo de la pieza]            │
│                                          │
│  [Copiar]  [Iterar]  [No era esto]       │
└──────────────────────────────────────────┘
```
Fondo distinto a las burbujas, borde con accent color, tipografía más grande.

**Brief Card:**
```
┌──────────────────────────────────────────┐
│  ✍️  Voy a escribir                       │
│                                          │
│  Formato     Tweet                       │
│  Tono        Confiado, directo           │
│  Límite      280 caracteres              │
│  Constraints: audience: tech enthusiasts │
│                                          │
│  [Escribir]          [Ajustar brief]     │
└──────────────────────────────────────────┘
```

---

## Backlog relacionado (NO este sprint)

**Sprint 6 — Identity Evolution**
- El writer evoluciona de tres fuentes: pieza escrita + conversación + tools usados
- Trigger: al completar una pieza (`WriterPiece` saved) → llamar evolution graph
- Memoria imperfecta por diseño (consolidar, distorsionar levemente, olvidar trivial) — patrón de Muse
- El character sheet (Sprint 4) muestra barras animándose cuando cambian los valores

**Writer Initialization Flow (Sprint 6 o antes)**
- Al crear un writer: campo de descripción libre ("quiero un escritor de tweets tipo george r r martin")
- Backend: LLM parsea la descripción y genera identity inicial estructurada
- Reemplaza los defaults genéricos actuales en `backend/services/writer_service.py::create_writer()`

---

## Cómo arrancar la próxima sesión

1. Leer este archivo
2. Explorar los archivos clave listados arriba (no confiar en este doc para el código — puede haber cambiado)
3. Crear branch `feature/writing-experience`
4. Arrancar por Slice 1 (backend contratos) antes de cualquier frontend — los contratos son el shared interface
5. Slice 1 y Slice 3 pueden correr en paralelo una vez definidos los contratos

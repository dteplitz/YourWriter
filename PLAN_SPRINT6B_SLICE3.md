# Plan — Sprint 6b Slice 3: LangGraph checkpointer

## Propósito del thread

Este archivo persiste el refinement para `Sprint 6b / Slice 3` y deja listo el handoff al próximo thread de build.

Estado de partida:

- `Slice 0` ✅ Postgres local unificado
- `Slice 1` ✅ `StudioSession` / `StudioTake` + session plumbing
- `Slice 2` ✅ post-session import flow completo (backend + frontend + QA UI)

El próximo thread ya no tiene que reabrir Slice 2. Tiene que tomar este archivo como contrato para construir **solo Slice 3**.

---

## Objetivo del slice

Agregar resumibilidad técnica real al pipeline del Studio compilándolo como `StateGraph` de LangGraph con checkpointer persistente en Postgres.

Esto tiene dos objetivos concretos:

1. hacer que el state del Studio sobreviva a cortes / reconexiones / reanudaciones
2. dejar montada la base técnica que Sprint 7 necesita para Store + LangMem

El driver del slice es técnico. Después de Slice 2 el sprint ya entrega valor de producto; Slice 3 cierra la infraestructura.

---

## Contexto técnico real al arrancar

Hoy `stream_studio_session()` **no** usa un grafo compilado.

Estado actual:

- crea `StudioSession` si no viene `session_id`
- crea `StudioTake`
- llama manualmente a:
  - `research_node_stream()`
  - `outline_node()`
  - `draft_node()`
  - `studio_refine_node_stream()`
- persiste `WriterPiece` y actualiza el take al final

Esto significa que para meter checkpointer **hay que refactorizar el Studio a un grafo compilado real**.

No es un “plug in” sobre el service existente.

---

## Lectura obligatoria antes de proponer implementación

En el próximo thread, antes de proponer el diseño final o tocar código, hay que leer:

- `SPRINT6B.md`
- `PROCESS.md`
- `CLAUDE.md`
- `PRODUCT.md`
- `ARCHITECTURE.md`
- `LANG_PLAYBOOK.md`
- `agents/graphs/`
- `agents/nodes/writing_nodes.py`
- `backend/services/chat_service.py`

En especial:

- `SPRINT6B.md` Slice 3
- `LANG_PLAYBOOK.md` decisión D8 y pattern P4
- `ARCHITECTURE.md` sección de `stream_studio_session()`

---

## Decisiones ya ratificadas para este slice

### D1 — El Studio pasa a `StateGraph` compilado

No se intenta “simular” checkpointer sobre el service actual.

El grafo de Studio pasa a ser la unidad real de ejecución del pipeline.

### D2 — Checkpointer en Postgres

Usar `AsyncPostgresSaver` de `langgraph.checkpoint.postgres.aio`.

No diseñar este slice alrededor de SQLite local. Slice 0 ya eliminó esa asimetría del runtime.

### D3 — `thread_id = StudioSession.id`

El puente entre producto y LangGraph es:

- objeto producto: `StudioSession`
- thread del checkpointer: mismo `session_id`

No inventar otro identificador.

### D4 — `lifecycle` sigue siendo responsabilidad del service layer

El grafo no decide transiciones de producto.

`StudioSession.lifecycle` sigue siendo escrito por el layer de servicio/rutas del producto:

- `active`
- `complete`
- `imported`
- `skipped`

### D5 — Slice 3 no toca el import flow

El post-session import ya quedó implementado y validado.

No reabrir:

- `/studio/:writerId/import/:sessionId`
- contracts de import
- banner de WriterPage

salvo fix mínimo si el refactor del Studio descubre un blocker real.

---

## Scope del próximo thread

### Sí entra

- definir el `StudioState` del grafo
- crear el writing graph compilado para Studio
- compilarlo con `AsyncPostgresSaver`
- adaptar `stream_studio_session()` para usar `graph.astream(...)`
- preservar SSE streaming compatible con el frontend actual
- preservar `session_started`, tool events, phase events, tokens y `piece`
- mantener `StudioSession` / `StudioTake` como entidades producto
- tests backend/integración relevantes del nuevo flujo
- verify técnico del resume/checkpoint

### No entra

- Slice 4 UI de sesiones / retomar
- trabajo de Product visible nuevo
- cambios al import flow
- memory system de Sprint 7
- writer initialization flow 6b.5

---

## Contrato técnico esperado

### 1. Grafo nuevo de Studio

Debería existir un builder explícito para el Studio, separado del chat evolution graph.

El próximo thread tiene que decidir dónde vive, pero la dirección esperada es algo como:

- `agents/graphs/studio_graph.py`

### 2. `StudioState`

Diseñar un `TypedDict` o schema equivalente con lo mínimo persistible para resumir el pipeline.

Campos candidatos:

- brief estructurado
- `iteration_notes`
- `search_results`
- `outline`
- `draft`
- `refined_content`
- `title`
- phase / markers intermedios solo si realmente hacen falta para resume

Qué no conviene poner si se puede evitar:

- objetos pesados que ya viven en DB y se pueden recargar
- `writer` completo
- lógica de lifecycle de producto

### 3. Streaming SSE compatible hacia frontend

El frontend ya espera hoy:

- `session_started`
- `phase`
- `tool_use`
- `tool_result`
- `token`
- `piece`
- `done`

Slice 3 debe preservar ese contrato visible.

Si internamente cambia la fuente de esos eventos, el frontend no debería romper.

### 4. Persistencia producto sigue viva

El checkpointer no reemplaza:

- `StudioSession`
- `StudioTake`
- `WriterPiece`

Las tablas siguen siendo el registro de producto.

El checkpointer agrega state persistente del pipeline, no reemplaza el modelo de negocio.

### 5. Resume semantics

El próximo thread debe cerrar explícitamente la granularidad de resume.

La opción recomendada de arranque es:

- resumir desde el último nodo completado
- si se corta en un nodo streaming activo, reiniciar ese nodo activo

Eso mantiene el diseño simple y suficientemente robusto para este slice.

---

## Riesgos a vigilar

1. Intentar enchufar checkpointer sin convertir el Studio a grafo real.
2. Persistir demasiado state y volver frágil / opaco el resume.
3. Romper el contrato SSE que ya usa el frontend del Studio.
4. Mezclar lifecycle de producto con estado interno del grafo.
5. Abrir scope de Slice 4 bajo la excusa de “retomar”.

---

## Criterios de done sugeridos

- el Studio corre sobre un `StateGraph` compilado
- el checkpointer usa `AsyncPostgresSaver`
- `thread_id` queda alineado con `StudioSession.id`
- no se rompe el flujo SSE consumido por el frontend actual
- la sesión/takes/piece siguen persistiendo correctamente
- existe una forma verificable de reanudar una sesión usando el checkpoint persistido
- tests backend/integración relevantes pasan
- QA técnica del flow de resume queda documentada en `SPRINT6B.md`

---

## Archivos candidatos a tocar

- `agents/graphs/`
- `agents/nodes/writing_nodes.py`
- `backend/services/chat_service.py`
- `backend/api/routes/chat.py`
- `backend/config.py` si hace falta configuración explícita del saver
- tests backend / integración del Studio
- `ARCHITECTURE.md`
- `SPRINT6B.md`

---

## Nota de proceso para el próximo thread

Ese thread debería arrancar así:

1. diagnóstico al despertar según `CLAUDE.md`
2. confirmación del scope exacto de Slice 3
3. lectura obligatoria de `agents/graphs/` y `agents/nodes/writing_nodes.py`
4. propuesta de diseño de `StudioState` + wiring del graph
5. recién después entrar en build

Si la lectura del código muestra que el plan necesita un ajuste importante, se alinea primero y no se implementa a ciegas.

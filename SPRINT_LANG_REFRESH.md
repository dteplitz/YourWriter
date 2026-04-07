# Sprint Lang Refresh — Refactor técnico fundacional del agent layer

*Estado: 📋 PRÓXIMO — iteración cero antes de Sprint 6b*

*Para el contexto y razonamiento del ecosistema Lang, leer `LANG_PLAYBOOK.md` antes de este sprint.*

---

## Por qué este sprint existe

Tres realidades del agent layer hoy:

1. **Versiones desactualizadas.** `langchain >=0.3.0`, `langgraph >=0.2.0`, `langchain-anthropic >=0.3.0`. Todo de antes de mayo 2025 — una era atrás en este ecosistema. LangChain 1.0 y LangGraph 1.0 ya salieron (oct 2025) y traen mejoras concretas que aprovecharíamos.

2. **Inconsistencia de patrón.** El CLAUDE.md y ARCHITECTURE.md dicen "no SDK directo en agent layer". El código dice lo opuesto en 3 de 4 nodos: `chat_node.py`, `writing_nodes.py`, `research_node.py` usan `anthropic.AsyncAnthropic()` directo. Solo `evolution_nodes.py` usa `ChatAnthropic`. Es deuda técnica que ya está flagueada en los docs pero nunca se saldó.

3. **Código muerto.** `writer_graph` se compila en `agents/graphs/writer_graph.py` pero NO se ejecuta en runtime — `stream_writer_agent()` invoca `chat_node` directamente desde Sprint UX. Confunde a quien lee.

Sin saldar esto, todo lo que viene (Sprint 6b con checkpointer, Sprint 6c con LangSmith, Sprint 7 con LangMem) construye sobre base inestable.

**Lo que NO entra en este sprint:**
- Migración a `create_agent` (decisión D1 del PLAYBOOK — esperamos a que haya tools en el chat)
- Adopción de deepagents (decisión D9)
- Checkpointer + Store (parte de Sprint 6b — decisión D8)
- LangSmith setup (Sprint 6c — decisión D6)
- Cambios de feature funcional — esto es 100% refactor

---

## Scope (lo que SÍ entra)

| ID | Cambio | Decisión PLAYBOOK |
|---|---|---|
| **R1** | Bumpear versiones de LangChain/LangGraph/langchain-anthropic | — |
| **R2** | Migrar `chat_node`, `writing_nodes`, `research_node` y `chat_service.generate_brief()` de `anthropic.AsyncAnthropic()` directo a `ChatAnthropic` | D2 |
| **R3** | Activar prompt caching del system prompt en chat y writing | D3 |
| **R4** | Reemplazar `_parse_json_response()` por structured output via Pydantic en `compute_node` y `detect_node` | D4 |
| **R5** | Centralizar modelos en `backend/config.py` (`chat_model`, `evolution_detect_model`, `evolution_compute_model`, `studio_model`) | D5 |
| **R6** | Borrar código muerto: `writer_graph.py` (grafo no usado), `tools/registry.py` (custom tool registry reemplazable), `tools/web_search.py` (stub ya no usado) | A3, A4 |

**Definition of Done:**
- Todos los tests existentes verdes (`test_chat_stream.py`, `test_studio.py`, `test_evolution_service.py`, `test_research_node.py`, `test_registry.py` o su reemplazo)
- QA visual end-to-end en local: chat con writer → evolution detectada → studio session → pieza generada
- Calidad del evolution pipeline validada manualmente: probar al menos 5 conversaciones reales de tipos distintos y verificar que `should_evolve` y `compute_node` siguen funcionando como antes
- `LANG_PLAYBOOK.md` y `ARCHITECTURE.md` actualizados con el estado post-refactor
- Un solo PR atómico con commits separados y reviewables

---

## Plan de ejecución — secuencia de commits

El sprint sale como **un PR único** llamado `refactor/lang-refresh` con la siguiente secuencia de commits, cada uno verificable independientemente:

### Commit 1 — `chore(deps): bump langchain ecosystem to 1.x`
**Archivo:** `requirements.txt`

Cambios:
- `langchain>=1.0,<2`
- `langgraph>=1.0,<2`
- `langchain-anthropic>=0.3.20`
- `anthropic>=0.49.0` (sin cambio, ya está)

**Verificación:**
- `pip install -r requirements.txt` clean
- Tests existentes corren (puede haber warnings de deprecation pero no errores)
- Backend arranca con `bash dev.sh`
- Smoke test: hacer un chat message, verificar que llega respuesta

### Commit 2 — `feat(config): centralize agent model strings`
**Archivos:** `backend/config.py`

Cambios:
- Agregar a `Settings`:
  - `chat_model: str = "claude-sonnet-4-6"`
  - `evolution_detect_model: str = "claude-haiku-4-5-20251001"`
  - `evolution_compute_model: str = "claude-sonnet-4-6"`
  - `studio_model: str = "claude-sonnet-4-6"`
- Documentar en docstring que vienen de env vars opcionales

**Verificación:** unit test simple — instanciar `Settings()` y leer cada propiedad.

**Nota:** Verificar al implementar cuál es el model ID exacto válido en producción para Sonnet 4.6 (`claude-sonnet-4-6` vs el dated string `claude-sonnet-4-20250514`). Confirmar contra el `.env` actual y CLAUDE.md global.

### Commit 3 — `refactor(agents/evolution): use ChatAnthropic with Pydantic structured output`
**Archivos:** `agents/nodes/evolution_nodes.py`

Cambios:
- Importar `from backend.config import settings`
- `detect_node`:
  - Definir `class EvolutionDecision(BaseModel)` con `should_evolve: bool`, `confidence: float`, `signal: str`
  - Usar `ChatAnthropic(model=settings.evolution_detect_model).with_structured_output(EvolutionDecision)`
  - Eliminar uso de `_parse_json_response()` para detect
- `compute_node`:
  - Definir `class EvolutionChange(BaseModel)` y `class EvolutionPlan(BaseModel)` con la estructura exacta esperada
  - Usar `with_structured_output(EvolutionPlan)`
  - Eliminar uso de `_parse_json_response()` para compute
- Borrar `_parse_json_response()` función
- `apply_node` no cambia (no usa LLM)

**Verificación:**
- `test_evolution_service.py` corre verde (puede requerir actualizar mocks)
- QA manual: probar 5 conversaciones reales de tipos distintos, comparar el comportamiento contra el commit 2:
  - Conversación que NO debe triggerar (small talk) → `should_evolve=false`
  - Conversación que SÍ debe triggerar (refuerzo explícito de rasgo) → `should_evolve=true` + cambios coherentes
  - Conversación borderline (un solo pedido de tono) → `should_evolve=false`
  - Patrón emergente (mismo pedido en 3 exchanges) → `should_evolve=true`
  - Pedido de sesión vs pedido de identidad ("escribí esto X" vs "quiero que seas X")

**Si la calidad baja:** STOP. No mergear este commit. Escribir el caso fallido y pedir ayuda a Damian.

### Commit 4 — `refactor(agents/chat): use ChatAnthropic with prompt caching`
**Archivos:** `agents/nodes/chat_node.py`

Cambios:
- Reemplazar `anthropic.AsyncAnthropic()` por `ChatAnthropic(model=settings.chat_model, max_tokens=4096)`
- Reemplazar `chat_node()` (non-streaming) usando `await llm.ainvoke(messages)`
- Reemplazar `chat_node_stream()` usando `async for chunk in llm.astream(messages): yield chunk.content`
- En `_build_system_prompt()`, devolver un `SystemMessage` con `additional_kwargs={"cache_control": {"type": "ephemeral"}}` en lugar de un string
- Adaptar `_messages_to_anthropic()` para devolver lista de `HumanMessage`/`AIMessage` de LangChain en lugar de dicts crudos

**Verificación:**
- `test_chat_stream.py` verde
- QA manual: hacer chat de 5+ mensajes con un writer y verificar:
  - Las respuestas son coherentes y se sienten en personaje
  - La latencia del 2do mensaje en adelante es perceptiblemente menor (cache hit)
  - No hay regresiones en streaming visual

### Commit 5 — `refactor(agents/writing): use ChatAnthropic for outline/draft/refine`
**Archivos:** `agents/nodes/writing_nodes.py`

Cambios:
- Reemplazar el helper `_call_claude()` por uso directo de `ChatAnthropic(model=settings.studio_model, max_tokens=8192)`
- `outline_node`, `draft_node`, `refine_node`, `studio_refine_node_stream`: todos pasan a usar `ChatAnthropic`
- Streaming nodes usan `astream()` en lugar de `client.messages.stream()`
- System prompts grandes (`WRITER_SYSTEM_PROMPT` con identidad) cacheados con `cache_control` en `SystemMessage`

**Verificación:**
- `test_studio.py` verde
- QA manual: hacer una sesión completa del Studio con un writer:
  - Brief setup → research → outline → draft → refine → pieza guardada
  - Iterar al menos una vez con notes del productor
  - Verificar que el streaming visual funciona igual

### Commit 6 — `refactor(agents/research): use ChatAnthropic for research_node`
**Archivos:** `agents/nodes/research_node.py`

Cambios:
- Reemplazar `anthropic.AsyncAnthropic()` por `ChatAnthropic`
- **Cuidado especial:** este nodo usa `web_search_20250305` (tool built-in de Anthropic). Verificar la API exacta para pasar tools built-in via `ChatAnthropic`. Opciones a investigar:
  - LangChain 1.2+: parámetro `extras` en tool spec
  - Pasar `tools=[{"type": "web_search_20250305", ...}]` directo via `bind_tools()` o equivalente
  - Si no hay forma limpia: dejar este nodo como excepción documentada y abrirlo como ítem aparte
- Adaptar el walking de content blocks (`tool_use`, `tool_result`, `text`) al formato de LangChain `AIMessage` content blocks (1.0+)

**Verificación:**
- `test_research_node.py` verde (puede requerir actualizar mocks)
- QA manual: hacer un brief en el Studio que requiera búsqueda web (algo factual), verificar:
  - El pill "Buscando: ..." aparece
  - El pill de tool_result aparece
  - El research feed información al outline correctamente

**Si no encontramos forma limpia de pasar `web_search_20250305` via ChatAnthropic en LangChain 1.x:** documentar la excepción en `LANG_PLAYBOOK.md` (sección Anti-patterns) y dejar este nodo como single excepción al patrón D2. Mejor honestidad que un wrapper hack.

### Commit 7 — `refactor(services): migrate generate_brief to ChatAnthropic`
**Archivos:** `backend/services/chat_service.py`

Cambios:
- `generate_brief()` (y cualquier otro lugar de `chat_service.py` que use `anthropic.AsyncAnthropic()` directo) pasa a `ChatAnthropic`
- Cachear el `BRIEF_GENERATION_PROMPT` con `cache_control` si es estable

**Verificación:**
- Tests del brief verdes
- QA manual: arrancar el Studio, escribir un brief libre, verificar que la generación funciona

### Commit 8 — `chore(agents): remove dead code (writer_graph, custom tool registry, web_search stub)`
**Archivos:**
- BORRAR: `agents/graphs/writer_graph.py` (compilado pero no ejecutado)
- BORRAR: `agents/tools/registry.py` (reemplazado por bind_tools nativo en R6)
- BORRAR: `agents/tools/web_search.py` (stub ya no usado)
- BORRAR: `agents/tests/test_registry.py` (testea código borrado)
- Verificar que no hay imports rotos en ningún lado: `chat_service.py`, `evolution_service.py`, `chat_route.py`

**Verificación:**
- Todos los tests verdes
- `bash dev.sh` arranca clean
- `grep -r "from agents.graphs.writer_graph"` → 0 hits
- `grep -r "from agents.tools.registry"` → 0 hits
- `grep -r "TOOL_REGISTRY"` → 0 hits

### Commit 9 — `docs: update ARCHITECTURE and PLAYBOOK to reflect post-refresh state`
**Archivos:** `ARCHITECTURE.md`, `LANG_PLAYBOOK.md`

Cambios en `ARCHITECTURE.md`:
- Sección "Stack" — actualizar versiones
- Sección "Agent Layer" — eliminar referencia al "legacy graph", actualizar para reflejar que todos los nodos usan `ChatAnthropic`
- Sección "Principio: no SDK directo en el agent layer" — eliminar el bloque de "Deuda técnica existente" (ya saldada)
- Sección "Lo que existe pero no está activo" — eliminar `web_search.py` (ya borrado)

Cambios en `LANG_PLAYBOOK.md`:
- Sección 1 "Stack actual" — actualizar versiones a las realmente instaladas
- Sección 6 "Histórico de cambios" — agregar entry "2026-XX-XX — Sprint Lang Refresh completado"
- Si hubo excepciones (ej. research_node), documentarlas

---

## Test plan

**Tests automáticos** (deben quedar todos verdes):
- `backend/tests/test_chat_stream.py`
- `backend/tests/test_studio.py`
- `backend/tests/test_evolution_service.py`
- `agents/tests/test_research_node.py`
- (`agents/tests/test_registry.py` — borrado en commit 8)

**QA visual manual end-to-end** (Playwright MCP, ambiente local):

1. **Login flow:** entrar con credenciales QA, llegar al dashboard
2. **Writer existente — chat:** abrir un writer existente, mandar 5 mensajes de chat de tipos distintos, verificar:
   - Streaming fluido en cada uno
   - Latencia perceptiblemente menor del mensaje 2 en adelante (cache hit del system prompt)
   - El writer responde en personaje
3. **Evolution detection — caso positivo:** mandar una conversación que debería triggerar evolution (ej: "me encanta cómo escribís oscuro, quiero que seas más así, desarrollá ese estilo"). Verificar:
   - Banner "Deshacer" aparece
   - El character sheet anima diffs
   - El EvolutionFeed registra la entrada
4. **Evolution detection — caso negativo:** mandar small talk. Verificar que NO triggerea
5. **Studio session completa:** "Studio →", brief libre que requiera web search, verificar:
   - Pill "Buscando" aparece
   - Phase pills cambian (preparing → drafting → refining)
   - Pieza generada con título
   - Iterar una vez con notes
6. **Rollback:** después del caso 3, hacer rollback de la evolución, verificar que vuelve al estado anterior

**Documentar cualquier regresión** y resolverla antes de mergear el PR.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| **Calidad del evolution pipeline baja** al migrar a structured output | QA manual obligatoria con 5+ casos reales antes de mergear commit 3. Si baja, no mergear y diagnosticar |
| **Web search built-in tool no se puede pasar limpio via `ChatAnthropic`** | Plan B: dejar `research_node` como única excepción al patrón D2, documentarla en PLAYBOOK |
| **Prompt caching no aplica** porque el system prompt cambia entre turnos (identity recargada) | Verificar que el system prompt se construye igual entre turnos del mismo writer en la misma sesión. Si no, cachear solo la parte invariante (instrucciones base) y dejar la identidad fuera del bloque cacheado |
| **Tests de mocks rotos** porque mockean el SDK directo de Anthropic | Actualizar los mocks para mockear `ChatAnthropic.ainvoke` / `astream` en lugar de `anthropic.AsyncAnthropic.messages.create` |
| **Versiones nuevas rompen algo no obvio** (deprecation, API change) | Bumpear y correr tests primero (commit 1) antes de hacer ningún otro cambio. Si hay sorpresas, abordarlas commit-aparte antes de seguir |

**Rollback strategy:** El sprint sale como un solo PR. Si algo se rompe en prod después del merge, el revert es el del PR completo. No hay migraciones de DB ni cambios de schema → revert es seguro.

---

## Para el Claude que implemente

**Antes de arrancar, leer en este orden:**
1. `LANG_PLAYBOOK.md` — todas las decisiones D1–D10 y patterns P1–P5
2. Este archivo (SPRINT_LANG_REFRESH.md) completo
3. `ARCHITECTURE.md` — sección "Agent Layer"
4. `agents/nodes/evolution_nodes.py` — el único nodo que ya usa `ChatAnthropic` correctamente, es el patrón a copiar
5. `agents/nodes/chat_node.py`, `writing_nodes.py`, `research_node.py` — los que vamos a migrar
6. `backend/config.py` — para entender el patrón de Settings actual
7. `backend/services/evolution_service.py` — patrón de sesión corta y orquestación

**Antes de empezar a tocar código:**
- Verificar el model ID exacto de Sonnet 4.6 contra el `.env` actual y CLAUDE.md global
- Leer la doc de `langchain-anthropic` 0.3.20+ para confirmar que `with_structured_output()` y `cache_control` funcionan como esperamos
- Investigar la API exacta para pasar `web_search_20250305` via `ChatAnthropic` en LangChain 1.x — esto define si commit 6 es directo o tiene plan B

**Way of work:**
- Un commit por punto, mensajes claros (`refactor(area): description`)
- Tests verdes antes de cada commit nuevo (no acumular roturas)
- Si algo se complica más de lo esperado, **parar y avisar a Damian** — no forzar
- Pre-commit review propio (memoria `feedback_pre_commit_review.md`): dead code, props redundantes, archivos huérfanos

**Después del merge:**
- Update de `CLAUDE.md` línea "Contexto de la última sesión" con resumen del sprint
- Update de `memory/project_roadmap.md` marcando Sprint Lang Refresh como ✅
- Retro conjunto con Damian (memoria `feedback_retro_conjunto.md`) — no ejecutar el retro solo

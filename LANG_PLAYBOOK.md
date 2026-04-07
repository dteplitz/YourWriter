# LANG_PLAYBOOK — El ecosistema Lang en YourWriter

*Doc vivo. Es la referencia técnica y de decisiones sobre LangChain / LangGraph / LangMem / deepagents en YourWriter. Se actualiza cuando se toma una nueva decisión sobre el stack Lang. No es brain dump congelado — es la base sobre la que se decide en cada sprint.*

*Última actualización: 2026-04-07 (Sprint Lang Refresh ejecutado y mergeado — D2/D3/D4/D5 cerradas)*

---

## 1. Stack actual en YourWriter

**Versiones actuales (post Sprint Lang Refresh):**

| Paquete | Versión | Por qué |
|---|---|---|
| `langchain` | `>=1.0,<2` ✅ | LangChain 1.0 GA (oct 2025): create_agent, middleware, content blocks |
| `langgraph` | `>=1.0,<2` ✅ | LangGraph 1.0 GA: backwards compatible con 0.2, abre checkpointer/store/Send |
| `langchain-anthropic` | `>=0.3.20` ✅ | Provider integration para Claude. `bind_tools` acepta el dict nativo de Anthropic para built-ins |
| `anthropic` | `>=0.49.0` | Tools built-in (`web_search_20250305`) — pasa a través del provider |
| `langsmith` | `>=0.2` (pendiente) | Tracing + evals (Sprint 6c) |
| `langmem` | `>=0.1` (pendiente) | Memoria episódica + semántica (Sprint 7) |

**Dónde vive cada cosa:**

| Área | Ubicación | Qué corre |
|---|---|---|
| Grafos | `agents/graphs/` | `evolution_graph.py` (único grafo compilado y ejecutado). `writer_graph.py` borrado en Lang Refresh |
| Nodos | `agents/nodes/` | `chat_node.py` (cache_control), `writing_nodes.py`, `research_node.py` (bind_tools), `evolution_nodes.py` (Pydantic structured output) — todos en `ChatAnthropic` |
| Tools | `agents/tools/` | `memory.py` (stub), `constraints.py`. La web search es una built-in de Anthropic declarada inline en `research_node.py`, no en un registry |
| Prompts | `agents/prompts/system.py` | Prompts canónicos: `ARTIST_PROFILE_CHAT_SYSTEM_PROMPT`, `EVOLUTION_DETECT_PROMPT`, `EVOLUTION_SYSTEM_PROMPT`, `STUDIO_REFINE_PROMPT`, etc. |
| Identidad | `agents/evolution/` | `Identity` dataclass + diff helpers |
| Servicios | `backend/services/evolution_service.py` | Orquesta el grafo de evolución, separa LLM calls de DB sessions |

**El único grafo realmente compilado y ejecutado es `evolution_graph`.** Todo lo demás (chat, studio) orquesta nodos directamente. Esto sigue así post Lang Refresh — D1 dice que no migramos chat a `create_agent` hasta que tengamos tools reales (Sprint 7 con memory tool).

---

## 2. Decisiones clave (con razón)

### D1 — `create_agent` lo aplicamos cuando hay tools, no antes

**Decisión:** En el Sprint Lang Refresh **no** migramos `chat_node` a `create_agent`. Queda como llamada a `ChatAnthropic` directa con prompt caching activo.

**Razón:** `create_agent` brilla cuando hay tools en el loop (model → tool call → tool result → model). Hoy el chat es puramente conversacional. Meter `create_agent` ahora es complejidad sin beneficio inmediato. Lo aplicamos cuando agreguemos un tool real al chat — el candidato natural es **Sprint 7**, cuando integremos LangMem y Claude tenga un memory tool propio.

**Cuándo revisitar:** Sprint 7 (memory tool en chat).

### D2 — Todo el agent layer en `ChatAnthropic`, sin SDK directo ✅

**Decisión:** Sprint Lang Refresh migra los 3 nodos que aún usan `anthropic.AsyncAnthropic` (`chat_node.py`, `writing_nodes.py`, `research_node.py`) a `ChatAnthropic` de `langchain_anthropic`. También `chat_service.py::generate_brief()`.

**Razón:** Consistencia. La regla "no SDK directo en agent layer" ya estaba escrita en CLAUDE.md y ARCHITECTURE.md, pero el código no la respetaba en 3/4 de los nodos. Sin esto no podemos: (a) usar middleware, (b) usar content blocks tipados, (c) cachear system prompts via `cache_control`, (d) usar structured output integrado. Es la base de todo lo demás.

**Resuelto en Lang Refresh (2026-04-07):** los 4 call sites migrados. La built-in `web_search_20250305` se pasa a `ChatAnthropic.bind_tools([{"type": "web_search_20250305", "name": "web_search"}])` — el dict nativo de Anthropic se acepta sin transformación. Ver P1.

### D3 — Prompt caching del system prompt del writer ✅

**Decisión:** El `ARTIST_PROFILE_CHAT_SYSTEM_PROMPT` (que contiene la identidad completa: personality + emotions + memories + constraints + objectives) se envía con `cache_control: {"type": "ephemeral"}` en la primera llamada de cada turno del chat.

**Razón:** Es un system prompt grande, idéntico entre turnos consecutivos del mismo writer. Anthropic reporta hasta **90% menos costo** y **85% menos latencia** en cache hits. Sprint 6b va a hacer las identidades aún más ricas → la ganancia se compone. Es el single biggest win de Lang Refresh.

**Resuelto en Lang Refresh (2026-04-07):** activado en `chat_node.py`. El pattern correcto (corregido tras implementar) es **content blocks**, no `additional_kwargs` — ver P1.

**Cuándo expira el caché:** TTL default 5 min. Si querés sesiones largas con identidad estable, hay un beta de 1h TTL (`anthropic-beta: extended-cache-ttl-2025-04-11`). Hoy no lo necesitamos.

### D4 — Structured output para `compute_node` ✅

**Decisión:** Reemplazar `_parse_json_response()` (que hace strip de markdown fences con regex) por structured output via Pydantic schema integrado en el call de `ChatAnthropic`.

**Razón:** El silent failure por fences fue uno de los pitfalls más dolorosos de Sprint 6a (memoria `feedback_llm_output_parsing.md`). Structured output integrado en el loop del modelo elimina el fence problem en origen — el modelo devuelve estructura tipada, no texto que parseamos. Bonus: con LangChain 1.0 esto **NO requiere un LLM call extra** (en LangChain pre-1.0 sí).

**Resuelto en Lang Refresh (2026-04-07):** `EvolutionDecision`, `EvolutionPlan`, `EvolutionChange` definidas en `evolution_nodes.py`. `_parse_json_response()` borrado. `BriefResponse` también via `with_structured_output`. QA manual del evolution path en Studio: la calidad se mantuvo o mejoró.

### D5 — Modelo via config, no hardcodeado ✅

**Decisión:** Mover los strings de modelo (`claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`) a `backend/config.py` como settings: `chat_model`, `writing_model`, `evolution_detect_model`, `evolution_compute_model`.

**Razón:** Hoy está hardcodeado en 4-5 archivos distintos, con strings inconsistentes (`claude-sonnet-4-20250514` vs `claude-sonnet-4-6`). Cambiar de modelo (o hacer A/B test, o downgrade en local) requiere editar varios archivos. Centralizar es trivial y desbloquea flexibilidad.

**Resuelto en Lang Refresh (2026-04-07):** 4 settings agregadas. Defaults: `claude-sonnet-4-6` para chat/writing/evolution_compute, `claude-haiku-4-5-20251001` para evolution_detect.

### D6 — LangSmith antes de tener usuarios reales (Sprint 6c)

**Decisión:** Setup de LangSmith + evals del evolution pipeline en Sprint 6c (entre 6b y 7), antes de empezar a buscar usuarios reales.

**Razón:** El evolution pipeline es el feature diferenciador del producto. Hoy una mala detección se nota cuando un usuario se queja. Sin evals sistemáticas, escalar es a ciegas. LangSmith provee: tracing automático de runs, datasets desde traces reales, LLM-as-judge evaluators, online evals en producción (alertas si la calidad cae).

**Setup mínimo del sprint:** account + env vars + tracing en agent layer + dataset inicial de ~30 conversaciones reales etiquetadas + 2 evaluators (uno para `should_evolve` boolean, uno para "el cambio propuesto es coherente con el signal").

### D7 — LangMem como base de Sprint 7 (no rolled-our-own)

**Decisión:** Cuando lleguemos a Sprint 7 (Memory System), adoptamos LangMem SDK en lugar de inventar nuestra propia memoria episódica.

**Razón:** LangMem ya viene con el modelo conceptual exacto que queremos: episodic memory ("experiences" con context narrativo), semantic memory (facts), procedural memory (patrones aprendidos). Integra nativo con LangGraph Store + namespaces multi-nivel. Inventarlo desde cero es meses de trabajo para llegar a algo peor.

**Trabajo de Sprint 7:** modelar nuestro dominio sobre LangMem (sesiones del Studio = episodic memories, facts del writer = semantic, estilos aprendidos = procedural), no construir la infraestructura de memoria.

### D8 — Checkpointer + Store como implementación natural de Sprint 6b

**Decisión:** El "session snapshot + import post-sesión" de Sprint 6b se implementa con LangGraph checkpointer (Postgres) + Store, no con tablas custom.

**Razón:** El session config fork = thread state persistente del checkpointer. El import post-sesión = mover entries del Store namespace de la sesión al namespace del general. Es lo que LangGraph fue diseñado para hacer. Construirlo a mano sería reinventar la rueda.

**Cuidado:** Esto introduce dependencia de Postgres para state del agente. En local seguimos con SQLite checkpointer (LangGraph soporta ambos). Verificar que el SQLite checkpointer aguante el patrón de SSE streaming sin bloqueos (memoria `feedback_sqlite_sessions.md`).

### D9 — Deep Agents NO en el roadmap activo

**Decisión:** No adoptamos `deepagents` para writer initialization en Sprint 6b ni para Studio v2. Lo dejamos en el horizonte.

**Razón:**
- **Para writer initialization (Sprint 6b):** empezar simple. Un LLM call estructurado puede ser suficiente. Si se queda corto, refactorizamos a deep agent en una iteración posterior. No prematurice.
- **Para Studio v2:** el Studio actual funciona. Deep Agents resuelve workflows multi-step complejos (capítulos largos, novellas con planning recursivo). Hoy escribimos piezas cortas/medianas. Adoptarlo ahora es overkill.

**Cuándo revisitar:** Si Sprint 6b muestra que la calidad de "escritor tipo GRRM" requiere research multi-step real, refactorizamos a deep agent. Si los usuarios empiezan a pedir piezas largas multi-capítulo, evaluamos Studio v2 con deep agents.

### D10 — Context editing + memory tool de Anthropic en watch list, no en roadmap

**Decisión:** No adoptamos `context-editing` ni el `memory tool` de Anthropic.

**Razón:** Es beta (riesgo de cambios de API), el problema que resuelve (sesiones del Studio de 10+ takes que explotan contexto) **no nos duele hoy**, y tiene overlap conceptual con LangMem (D7). Meter dos sistemas de memoria sin alinearlos primero es deuda técnica garantizada.

**Cuándo revisitar:** Cuando los usuarios reales hagan sesiones de Studio de 10+ takes y empiece a doler. O cuando salga GA y madure.

---

## 3. Patterns canónicos

### P1 — Llamada a Claude desde un nodo del agent layer

**Pattern:** `ChatAnthropic` configurado con modelo desde config, system prompt cacheado via **content blocks** (NO `additional_kwargs`), structured output cuando aplique.

```python
# agents/nodes/foo_node.py
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings

llm = ChatAnthropic(model=settings.chat_model, max_tokens=4096)

# El cache_control vive DENTRO del content block, no en additional_kwargs.
# Esta es la forma correcta de marcar un prefix cacheable en langchain-anthropic.
system = SystemMessage(content=[{
    "type": "text",
    "text": ARTIST_PROFILE_CHAT_SYSTEM_PROMPT.format(...),
    "cache_control": {"type": "ephemeral"},
}])

messages = [system, HumanMessage(content=user_text)]
response = await llm.ainvoke(messages)
```

**Importante sobre el response:** `response.content` puede ser `str` o `list` de blocks. Para texto, hay un helper canónico `_content_to_text()` (ver `chat_node.py`, `writing_nodes.py`) que joinea todos los blocks `{"type": "text"}`. Para tools (research_node), los blocks pueden ser `text`, `tool_use`, `server_tool_use` o `web_search_tool_result` — tratar a todos.

**Razón:** consistencia, observabilidad (cuando enchufemos LangSmith), prompt caching automático sobre el system prompt grande. Ver D2, D3.

### P2 — Structured output (sin parsing manual)

**Pattern:** Pydantic schema + `with_structured_output()` de `ChatAnthropic`.

```python
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic

class EvolutionDecision(BaseModel):
    should_evolve: bool = Field(description="...")
    confidence: float = Field(ge=0, le=1)
    signal: str = Field(description="...")

llm = ChatAnthropic(model=settings.evolution_detect_model)
structured_llm = llm.with_structured_output(EvolutionDecision)
decision: EvolutionDecision = await structured_llm.ainvoke(messages)
```

**Razón:** Elimina silent failures por markdown fences. El parsing pasa a ser problema del provider, no nuestro. Ver D4.

### P3 — Modelo via config

**Pattern:** Cualquier referencia a modelo viene de `backend/config.py`, nunca hardcoded en nodos.

```python
# backend/config.py
class Settings(BaseSettings):
    chat_model: str = "claude-sonnet-4-6"
    evolution_detect_model: str = "claude-haiku-4-5-20251001"
    evolution_compute_model: str = "claude-sonnet-4-6"
    studio_model: str = "claude-sonnet-4-6"
```

**Razón:** Cambiar de modelo, A/B testear, o downgradear en local debe ser cambio de una sola línea (env var). Ver D5.

### P4 — Checkpointer pattern (cuando lleguemos a Sprint 6b)

**Pattern:** `AsyncPostgresSaver` en prod, `AsyncSqliteSaver` en local. Compilar el grafo con el checkpointer. Threads identificados por `session_id`.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
    graph = build_studio_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": session_id}}
    async for event in graph.astream(input_state, config=config):
        ...
```

**Razón:** State persistente, sesiones resumibles. Ver D8.

### P5 — Tool registration (post Lang Refresh)

**Pattern para built-in de Anthropic (server-side):** pasar el dict nativo directo a `bind_tools()`. `langchain-anthropic` lo deja pasar tal cual.

```python
llm = ChatAnthropic(model=settings.writing_model, max_tokens=2048)
llm_with_tools = llm.bind_tools([
    {"type": "web_search_20250305", "name": "web_search"},
])
response = await llm_with_tools.ainvoke(messages)

# Los blocks de respuesta para built-in tools server-side son:
#   - server_tool_use      (no "tool_use" — distinto de tools custom client-side)
#   - web_search_tool_result
#   - text                 (síntesis del modelo, posiblemente partida en varios blocks
#                          algunos con "citations")
```

**Pattern para tools custom client-side (cuando llegue):** `@tool` decorator de LangChain + `bind_tools()`. Detalles concretos cuando hagamos D1 (chat con memory tool en Sprint 7).

---

## 4. Watch list — features que monitoreamos pero no usamos hoy

| Feature | Qué hace | Cuándo lo evaluamos |
|---|---|---|
| **`create_agent` + middleware** | High-level agent loop con hooks (HITL, summarization, PII redaction, retry) | Cuando agreguemos tools al chat — candidato natural Sprint 7 con memory tool |
| **Deep Agents (`deepagents`)** | Planning tool + virtual filesystem + subagents para tareas complejas multi-step | Si Sprint 6b muestra que writer init necesita research multi-step real, o si pedidos de usuario empujan piezas largas multi-capítulo |
| **Async subagents (deepagents v0.5)** | Subagents que corren en background sobre Agent Protocol, no bloquean al supervisor | Atado a Deep Agents — no aplica antes de adoptarlos |
| **Anthropic context editing** | Auto-clear de tool results stale del contexto cuando se acerca al límite | Cuando sesiones reales de Studio sean de 10+ takes y empiece a doler. Hoy beta |
| **Anthropic memory tool** | File-based memory persistente que Claude maneja directamente | Tiene overlap con LangMem — solo si LangMem se queda corto en algo concreto |
| **Interleaved thinking** (`interleaved-thinking-2025-05-14`) | Claude piensa entre tool calls — mejor synthesis de research | Cuando research_node tenga problemas de calidad de síntesis, no antes |
| **`langchain-classic`** | Paquete con features deprecated en 1.0 (chains, LCEL legacy) | Solo si necesitamos algo legacy específico — preferimos no depender |
| **Summarization middleware** | Comprime mensaje history cuando se acerca al context limit | Cuando hagamos D1 (`create_agent` en chat) — entra como middleware nativo |

---

## 5. Anti-patterns / cosas descartadas y por qué

### A1 — `anthropic.AsyncAnthropic()` directo en el agent layer ✅ resuelto
**Por qué no:** Rompe la regla de consistencia, bloquea middleware, content blocks tipados, cache_control fácil, structured output integrado. Saldado en Sprint Lang Refresh — 0 call sites en el agent layer. Ver D2.

### A2 — `_parse_json_response()` con regex de markdown fences ✅ resuelto
**Por qué no:** Es síntoma, no solución. El silent failure que oculta es peligroso. Structured output via Pydantic resuelve la causa raíz. Borrado en Sprint Lang Refresh. Ver D4.

### A3 — Tool Registry custom (`agents/tools/registry.py`) ✅ resuelto
**Por qué no:** Reinventaba lo que `bind_tools()` de LangChain ya hace nativo. Borrado en Sprint Lang Refresh — la spec del web_search vive inline en `research_node.py` como constante local.

### A4 — Compilar grafos que no se ejecutan ✅ resuelto
**Por qué no:** `writer_graph` estaba compilado pero NO se llamaba en runtime. Borrado en Sprint Lang Refresh. La regla queda: si compilás un grafo, asegurate de que se ejecute, o no lo compiles.

### A5 — Migrar dos veces (SDK directo → ChatAnthropic → create_agent)
**Por qué no:** Si en algún punto vamos a migrar a `create_agent`, mejor hacerlo en una sola pasada. Hoy NO migramos a `create_agent` (D1) — vamos solo a `ChatAnthropic`. Cuando D1 se active (Sprint 7 con memory tool), migramos directamente desde el patrón actual.

### A6 — Memoria episódica desde cero
**Por qué no:** LangMem ya tiene el modelo. Inventarlo desde cero es caro, peor, y va contra "no reinventar lo que el ecosistema ya resolvió". Ver D7.

### A7 — Sistemas de memoria duplicados (LangMem + Anthropic memory tool)
**Por qué no:** Tener dos sistemas de memoria sin alinear es deuda garantizada. Elegimos LangMem (D7), descartamos Anthropic memory tool por ahora (D10).

---

## 6. Referencias externas

**LangChain / LangGraph:**
- [LangChain & LangGraph 1.0 GA announcement](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [LangChain Python changelog (1.0–1.2)](https://docs.langchain.com/oss/python/releases/changelog)
- [LangGraph interrupts & human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Send API + map-reduce](https://langchain-ai.github.io/langgraphjs/how-tos/map-reduce/)

**Deep Agents:**
- [Deep Agents v0.5 announcement](https://blog.langchain.com/deep-agents-v0-5/)
- [Deep Agents repo + docs](https://github.com/langchain-ai/deepagents)

**LangMem:**
- [LangMem SDK launch](https://blog.langchain.com/langmem-sdk-launch/)
- [LangMem episodic memory guide](https://langchain-ai.github.io/langmem/guides/extract_episodic_memories/)
- [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)

**LangSmith:**
- [LangSmith evaluation docs](https://docs.langchain.com/langsmith/evaluation)

**Anthropic:**
- [Prompt caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Context management announcement](https://www.anthropic.com/news/context-management)
- [Context editing docs](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Extended thinking + interleaved thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)

---

## Histórico de cambios al playbook

- **2026-04-07** — Doc creado en sesión de research del ecosistema Lang post mayo 2025. Decisiones D1–D10 establecidas en conversación con Damian. Stack actual documentado pre Sprint Lang Refresh.
- **2026-04-07** — Sprint Lang Refresh ejecutado y mergeado. D2/D3/D4/D5 marcadas ✅. A1/A2/A3/A4 resueltos. P1 corregido (cache_control vive en content blocks, no en `additional_kwargs` — descubrimiento al implementar). P5 expandido con el pattern real de built-in tools server-side. **Learning crítico:** los built-in tools de Anthropic devuelven blocks de tipo `server_tool_use` (no `tool_use`) y la síntesis llega partida en múltiples blocks `text` (algunos con `citations`). Descubrimos esto haciendo QA con Studio + "Indian Wells 2026" — el primer parser solo miraba `tool_use` y no detectaba la búsqueda. Documentado en P5 y en `feedback_anthropic_server_tool_use.md`.

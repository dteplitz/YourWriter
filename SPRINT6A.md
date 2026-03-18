# Sprint 6a — Identity Evolution via Chat

*Estado: 📋 PLANIFICADO — pendiente aprobación de Damian*

---

## Qué construimos

El writer evoluciona a través de la conversación. Cuando el usuario moldeaa al writer en el chat — pide enfoques, refuerza rasgos, explora temas — el sistema detecta esas señales y propone cambios graduales a la identidad. El usuario los ve animarse en el character sheet en tiempo real, y puede deshacerlos con un click.

**Lo que NO entra en este sprint (deferred a 6b):**
- Session snapshot (fork de identidad para el Studio)
- Import de stats de sesión al general
- Experience accumulation (memories desde el Studio)

---

## Modelo conceptual

```
Chat WriterPage
  └─► Respuesta del writer
        └─► [Stage 1: IF] ¿Esta conversación forma identidad? (Haiku, prompt cuidadoso)
              ├─ No → nada
              └─ Sí →
                    [Stage 2: WHAT] ¿Qué cambia exactamente? (Sonnet)
                          └─► Nuevos stats → nueva WriterIdentity version
                                └─► SSE: evolution events → frontend anima changes
                                      └─► "Deshacer" disponible por 30s
```

---

## Principio arquitectural: no SDK directo

**Todo LLM call en el agent layer usa LangChain** (`ChatAnthropic` de `langchain_anthropic`). Sin excepciones — aunque sea un nodo de un solo paso.

Razón: consistencia con el resto del agent layer, observabilidad unificada (LangSmith), un solo framework para razonar.

**Deuda técnica existente** (fuera del scope de Sprint 6a, a trackear):
- `agents/nodes/evolution_nodes.py` — `_call_claude()` helper usa `anthropic.AsyncAnthropic()` directamente
- `backend/services/chat_service.py::generate_brief()` — también SDK directo

Los nuevos nodos de Sprint 6a usarán `ChatAnthropic` desde el día 1.

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|----------|----------|-------|
| Trigger | Post-respuesta del writer (inline en SSE stream) | El stream ya está abierto, se extiende naturalmente |
| Stage 1 modelo | Haiku | Rápido y barato; la calidad viene del prompt, no del modelo |
| Stage 2 modelo | Sonnet | Necesita juicio fino para proponer cambios graduales |
| Formato de identidad | Dict en todas partes | Más rico; los valores numéricos de emotions son útiles |
| Persistencia | Append-only (nueva versión) | Rollback = copiar versión anterior como nueva |
| Rollback | Endpoint `POST /identity/rollback` | Nunca destructivo, siempre append |
| Pipeline existente (3 nodos) | Reemplazado | El enfoque de 2 etapas es más eficiente y preciso |

---

## Fix base: formato de identidad unificado

**El problema:** `Identity` dataclass usa `list[str]` para `personality` y `emotions`, pero el DB los guarda como `dict`. `from_dict()` aplicado sobre un dict produce sólo las keys — bug silencioso.

**El fix:** actualizar `Identity` dataclass a dict para `personality` y `emotions`:

```python
@dataclass
class Identity:
    purpose: str = "general-purpose writing"
    personality: dict[str, Any] = field(default_factory=dict)   # antes: list[str]
    emotions: dict[str, Any] = field(default_factory=dict)       # antes: list[str]
    memories: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    lifelong_objectives: list[str] = field(default_factory=list)
```

`_identity_to_agent_state()` en `chat_service.py` sigue convirtiendo dicts a listas de strings **solo para los prompts del LLM** — eso no cambia. Es la capa de traducción al formato textual del prompt.

---

## Nuevos prompts

### EVOLUTION_DETECT_PROMPT (Stage 1 — IF)

El prompt más crítico del sprint. Tiene que distinguir:

**Debe triggerar:**
- El usuario pide explícitamente moldear al writer: "quiero que seas más X", "desarrolla el estilo Y"
- El usuario refuerza un rasgo positivamente de forma específica: "me encanta cuando escribís así, seguí por ahí"
- El usuario y el writer descubren juntos una dirección nueva y el usuario la valida
- El usuario repite el mismo pedido de estilo/tema en múltiples exchanges — patrón emergente

**NO debe triggerar:**
- Requests de sesión puntual: "escribí esto en tono oscuro" (sin refuerzo posterior)
- Preguntas técnicas o de uso de la plataforma
- Small talk o conversación casual sin contenido identitario
- El usuario testeando algo sin validarlo ("y si lo hacés más formal?")
- Un solo exchange sin patrón establecido (a menos que sea muy explícito)

**Output:** JSON `{"should_evolve": bool, "confidence": float, "signal": str}`

### EVOLUTION_SYSTEM_PROMPT (Stage 2 — WHAT)

Versión revisada del prompt existente. Diferencias clave:
- Recibe el `signal` de la Stage 1 como contexto adicional
- Énfasis en cambios graduales e incrementales — nunca un rewrite
- Los deltas de `emotions` son numéricos (0–1), no strings — el prompt debe proponer `{"old": 0.4, "new": 0.6}`

---

## Nuevos componentes

### `agents/graphs/evolution_graph.py` (REEMPLAZAR)

Grafo LangGraph — consistente con el resto del agent layer, extensible para sprints futuros:

```
START → detect_node → [¿should_evolve?]
                              ├── no → END
                              └── sí → compute_node → apply_node → END
```

**`detect_node`** — Haiku + EVOLUTION_DETECT_PROMPT. Output al state: `{should_evolve, confidence, signal}`

**`compute_node`** — Sonnet + EVOLUTION_SYSTEM_PROMPT revisado. Recibe `signal` como contexto. Output al state: `{changes, reasoning}`

**`apply_node`** — sin LLM. Aplica los cambios estructurados al `current_identity`. Igual que el apply_node existente pero actualizado para formato dict.

La persistencia (crear nueva `WriterIdentity` + `EvolutionLog`) queda **fuera del grafo** — el graph retorna el estado final, el servicio persiste.

### `backend/services/evolution_service.py` (NUEVO)

```python
async def run_evolution(
    current_identity: dict,
    chat_history: list[dict],
) -> EvolutionResult | None      # None si detect dice no

async def persist_evolution(
    db: AsyncSession,
    writer_id: int,
    result: EvolutionResult,
) -> WriterIdentity               # nueva versión creada
```

Regla: ninguna función mantiene sesión DB abierta durante LLM calls.

### Rollback endpoint

```
POST /api/writers/{writer_id}/identity/rollback
```

- Carga las últimas 2 versiones
- Crea nueva versión copiando todos los campos de la versión N-1
- Append-only — nunca destruye historial
- Returns: `IdentityResponse`

### Nuevos SSE events (chat stream)

Emitidos **después** del evento `{"done": true}` cuando hay evolución:

```json
{"evolution_detected": true, "changes": [
  {"field": "emotions", "action": "modify", "key": "melancholy", "old_value": 0.3, "new_value": 0.5, "reason": "..."},
  {"field": "topics", "action": "add", "value": "noir fiction", "reason": "..."}
], "reasoning": "El usuario reforzó explícitamente el estilo oscuro..."}
```

---

## Archivos afectados

### Backend
| Archivo | Cambio |
|---------|--------|
| `agents/evolution/identity.py` | Fix: `personality` y `emotions` → `dict`. Actualizar `from_dict`, `to_dict`, `to_prompt_string` |
| `agents/prompts/system.py` | Agregar `EVOLUTION_DETECT_PROMPT`. Revisar `EVOLUTION_SYSTEM_PROMPT` para formato dict y signal input |
| `agents/graphs/evolution_graph.py` | REEMPLAZAR — nuevo grafo LangGraph: detect → [conditional] → compute → apply |
| `agents/nodes/evolution_nodes.py` | Simplificar: detect_node + compute_node + apply_node (reemplaza los 3 nodos actuales) |
| `backend/services/evolution_service.py` | NUEVO — run_evolution() + persist_evolution() |
| `backend/api/routes/chat.py` | Hook post-respuesta: correr evolution, emitir eventos SSE si hay cambios |
| `backend/api/routes/identity.py` | Agregar rollback endpoint |
| `backend/schemas/evolution.py` | Schemas Pydantic para evolution events y rollback response |

### Frontend
| Archivo | Cambio |
|---------|--------|
| `frontend/src/api/client.ts` | Manejar `evolution_detected` SSE events. Agregar `rollbackIdentity()` |
| `frontend/src/components/ChatPanel.tsx` | Detectar evolution events del stream, emitir al WriterPage |
| `frontend/src/components/ConfigPanel.tsx` | Recibir nueva identity → animar diff (ya tiene infraestructura) |
| `frontend/src/components/EvolutionFeed.tsx` | Agregar entradas de evolución automática (diferenciadas de las manuales) |
| `frontend/src/types/writer.ts` | Agregar `EvolutionEvent` type |

### Tests
| Archivo | Qué testea |
|---------|-----------|
| `backend/tests/test_evolution_service.py` | NUEVO — detect, compute, persist. Mockear LLM calls |

---

## Pitfalls a tener en cuenta

1. **Session management en evolution_service** — mismo patrón que chat_service: abrir sesión corta → escribir → cerrar, nunca durante LLM calls

2. **El SSE stream se extiende** — la evolución corre inline después del `done`. El frontend debe seguir el stream abierto hasta recibir el evento de cierre final. Confirmar que el cliente SSE no corta al recibir `done`.

3. **Datos existentes en SQLite** — el formato dict para personality/emotions ya es el formato en DB. El fix es en la capa Python (Identity dataclass), no en los datos. No hay migración.

4. **Rate limiting implícito** — si el usuario manda 10 mensajes rápido, no correr detect en cada uno. Solución simple: solo correr detect cuando el último mensaje del usuario tiene >15 palabras (conversación sustancial) o cuando hay más de 3 exchanges sin evolution check.

5. **El `evolution_graph.py` existente** — no se borra, pero ya no está en el hot path. Los `evolution_nodes.py` se simplifican para usar el nuevo servicio.

6. **Frontend: no bloquear el chat** — el usuario no debería esperar a que la evolución termine para poder escribir otro mensaje. El chat debe sentirse fluido; la evolución es un evento secundario que llega cuando llega.

---

## Para el Claude que implemente

Antes de arrancar, leer:
- Este archivo completo
- `agents/evolution/identity.py` — entender el fix a hacer
- `backend/services/chat_service.py` — patrón de sesión corta y cómo fluye el stream
- `agents/prompts/system.py` — EVOLUTION_DETECT_PROMPT es nuevo, EVOLUTION_SYSTEM_PROMPT se revisa
- `.agents/backend.md` — patrones del área

El fix de formato (dict) va primero — es la base de todo lo demás.

El prompt de EVOLUTION_DETECT_PROMPT es el trabajo más crítico del sprint. Dedicarle tiempo real antes de implementar.

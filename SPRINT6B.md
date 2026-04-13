# Sprint 6b — Session entity + Post-sesión import

*Definido 2026-04-08. Refinado en sesión de planning del 2026-04-08 (segundo bloque). Sucede a Sprint Lang Refresh (cerrado 2026-04-07).*

> **Cómo leer este doc:**
> - **Parte A — Plan ya definido**: lo que está cerrado y listo para construir (Slice 0 + Slice 1 al detalle).
> - **Parte B — Plan a refinar**: Slices 2/3/4 con lo que sí está claro + open questions explícitas a resolver al inicio de cada slice.
> - **Histórico de decisiones**: cada decisión cerrada con su razonamiento, para que en sesiones futuras se entienda el porqué sin tener que reconstruirlo.

---

## Objetivos centrales

Tres motivos profundos. La resumibilidad técnica es el cuarto pero **no es el driver** — es side effect.

1. **Dar infraestructura real a la tercera capa del modelo de identidad** (ver `PRODUCT.md` "Modelo de identidad — tres capas"). Hoy la capa "Post-sesión" existe en el doc pero no en el código. No hay un objeto "sesión" sobre el que decidir qué importar al General stats del writer.

2. **Cerrar el loop Studio → General stats** vía un flow explícito de Post-sesión import. El usuario revisa qué se aprendió en la sesión y decide qué se queda como permanente en la identidad del writer. Hoy el Studio es un agujero sin retorno: produce piezas pero no afecta al writer.

3. **Habilitar Sprint 7 (LangMem episódico) y Sprint 6c (LangSmith evals)** dándoles **episodios** sobre los que operar. LangMem necesita eventos completos con contexto, no piezas sueltas. Evals necesitan traces grounded en sesiones reales reproducibles. Sin Session entity ambos sprints arrancan en cero.

4. *(Side effect, no driver)* **Resumibilidad técnica** — el take no se pierde si el navegador se cierra a mitad. Vale, pero por sí solo no justificaba el sprint.

---

## Out of scope

- **Writer initialization flow** — separado a Sprint 6b.5 para no inflar el sprint. Reusará el Store del checkpointer que monta este sprint.
- **Importación automática post-sesión** — solo importación explícita por ahora. Más control del usuario, mejor data para evals, menos magia opaca.
- **LangMem episodic memory** — Sprint 7. Este sprint solo crea los episodios; consumirlos es trabajo de 7.
- **LangSmith setup + evals** — Sprint 6c. Este sprint crea los datos sobre los que 6c va a trabajar.
- **Offline-first y reconnect resiliency profundo** — el checkpointer da resumibilidad básica, no más.
- **Studio v2 / piezas multi-capítulo / Deep Agents** — horizonte abierto Sprint 9+.

---

## Histórico de decisiones

Cada una alineada con Damian. D1-D4 en el primer planning del 2026-04-08, D5-D10 en el segundo planning del mismo día (después de mapear el flujo de iteración real).

### D1 — Takes como entidades separadas en DB

`StudioTake` es una tabla nueva, no JSON adentro de `StudioSession`. Razón: Sprint 7 con LangMem necesita takes consultables; queries del tipo "todos los takes donde el writer usó tal topic" tienen que ser SQL, no parsing de blobs JSON.

`WriterPiece` queda **solo** para "takes que el usuario marcó como finales/exportables a la discografía". Hay relación pero no son la misma entidad — un take puede existir sin ser pieza, una pieza siempre tiene un take detrás.

### D2 — Post-sesión import es vía directa, no auto-evolution

El import flow **no** dispara el evolution pipeline existente sobre el contenido de la sesión. Es una vía paralela: un LLM call mira la sesión completa, propone cambios concretos pre-calculados (estilo "subir `melancholy` a 0.7", "agregar topic 'urban decay'"), el usuario revisa los checkboxes, confirma, y los cambios se aplican como una nueva versión de `WriterIdentity` con `source: "post_session_import"`.

Razón: más control del usuario, menos magia, mejor data para evals (selecciones del usuario son labels reales).

### D3 — Import flow forzado al "Finalizar sesión" con skip explícito

Cuando el usuario clickea "Finalizar sesión" en el Studio aparece el flow de import. Si no aprendió nada y quiere skipear, hay un botón explícito de "Skipear, importar nada" — la sesión queda guardada igual con `import_status: "skipped"` para que sea visible más tarde si cambia de opinión.

Razón: el costo de mostrarlo es bajo y la fricción de skipear también; el costo de no mostrarlo es perder la oportunidad principal del producto. Forzar visibilidad sin forzar acción.

### D4 — Visibilidad explícita del loop al usuario

El usuario tiene que **ver** que la sesión afectó al writer. No es magia silenciosa. Esto significa:
- Banner explícito post-import: "El writer evolucionó por esta sesión: +melancholy, +topic X, ..."
- La nueva versión de `WriterIdentity` se ve en la `EvolutionFeed` con `source: "post_session_import"` diferenciado visualmente del evolution via chat
- La sesión queda linkeada desde el `EvolutionLog` para poder revisitar el "porqué" del cambio

### D5 — Postgres local (Slice 0 nuevo)

Antes de tocar cualquier modelo nuevo, migramos local a Postgres en el `docker-compose.yml`. Un único compose, service nuevo `db` con `postgres:16-alpine`, volume mount para persistencia. SQLite local queda discontinuado.

Razón: Slice 3 mete LangGraph checkpointer y el playbook (D8 del PLAYBOOK) ya advierte que SQLite + SSE streaming tiene gotchas conocidos. Si dejamos SQLite local, vamos a debuggear bugs que **solo existen en local** y desaparecen en prod (o peor, al revés). Toda la paranoia de "no sesiones largas durante LLM calls" en `database.py` está pensada para SQLite (serialización de writes); en Postgres no aplica. Mejor uniformar desde el inicio.

**Tests siguen en SQLite** (in-memory o file). Razón: velocidad, no requiere Docker para correr `pytest`, simplicidad de CI. CI ya está configurado con `DATABASE_URL=sqlite+aiosqlite:///./test.db` ([.github/workflows/ci.yml:27](.github/workflows/ci.yml#L27)). Solo runtime de la app corre Postgres.

### D6 — `lifecycle` en lugar de `status`, naming distinto del checkpointer

El campo en `StudioSession` se llama `lifecycle`, **no** `status`. Se valida con dos representaciones distintas:
- `StudioSession.lifecycle`: vocabulario de **producto**, escrito por el service layer en cada transición. Lo lee la UI, las queries SQL, Sprint 7 cuando LangMem lo necesite.
- LangGraph checkpointer state: state interno del **runtime del grafo**. Vive en su propia tabla, lo escribe solo LangGraph, lo lee solo el grafo cuando reanuda.

Razón: ambos sistemas guardan "en qué punto del pipeline estamos" pero responden a preguntas distintas. Si los dos se llaman "status", cualquier lectura de código exige parar 2 segundos a pensar cuál es cuál. Naming distinto elimina el costo cognitivo y previene queries SQL acopladas al shape del checkpointer (que LangGraph no garantiza estable cross-version).

**Valores de `lifecycle`** (simplificados respecto al draft original):
```
active | complete | imported | skipped | abandoned
```

`drafting`/`refining` salieron del enum: son **fases del runtime del grafo**, no estados del producto. Mientras el grafo corre research/outline/draft/refine, la sesión está `active`. Esto reduce el bookkeeping manual: en lugar de updatear el row en cada transición de fase del pipeline (4 escrituras por take), updateamos solo en transiciones de producto (~2-3 escrituras por sesión entera).

**Regla operativa:** todas las transiciones de `lifecycle` pasan por un único helper `session_repository.advance_lifecycle(session_id, new_lifecycle)`. Single chokepoint para auditar y testear.

### D7 — Coexistencia: nuestro `lifecycle` y el checkpointer state conviven

Decisión derivada de D6, pero vale explicitarla. Evaluamos también la opción "una sola representación, derivar `lifecycle` del checkpointer". Descartada porque:
- Estados como `imported`/`skipped`/`abandoned` son **post-pipeline**: el grafo ya terminó, no updatea nada. No se pueden derivar del checkpoint.
- Queries SQL del tipo "todas las sesiones complete sin importar todavía" se vuelven cargar-checkpoint-y-parsear-en-Python — caro y feo.
- LangGraph checkpointer no es un query layer, es un mecanismo de resumibilidad. Acoplarle UI y queries es deuda.
- Haría a Slice 1 dependiente de Slice 3 (no podés definir el contrato sin saber el shape del checkpoint).

Coexisten. La regla del checkpointer = "thread state runtime", la regla del lifecycle = "estado del producto que lee el usuario". Cualquier estado nuevo del producto va a `lifecycle`. Cualquier mejora en cómo persiste el grafo va al checkpointer.

### D8 — `iteration_notes` separado del `brief` en el contrato del endpoint

El endpoint `POST /chat/{id}/studio/stream` cambia el body de `{ brief }` a `{ brief, session_id?, iteration_notes? }`.

Razón descubierta hoy mapeando el frontend: `SessionExperience.handleIterate` actualmente **pisa `brief.notes`** con las notas del productor en cada iteración (`{ ...brief, notes: notes }`). Esto mezcla dos conceptos distintos en el mismo campo:
- "Notas iniciales del brief" (lo que el usuario dijo en el BriefSetup)
- "Notas del productor para iterar" (las del `IterationInput`)

A partir del segundo take, las notas originales del brief se pierden. Hoy es bug latente porque el grafo no las usa post-refine, pero a partir de Slice 1 vamos a guardar el brief snapshot en `studio_sessions.brief_json` y queremos que sea fiel al brief original. Separar `iteration_notes` como campo top-level del request resuelve esto en origen.

### D9 — `session_id` opcional en el endpoint, frontend mantiene el ref entre takes

Esta es la implicación crítica de mapear el flujo de iteración:

> Hoy `stream_studio_session` es **stateless por take**. Cada llamada al endpoint crea un `WriterPiece` huérfano, sin link al anterior, sin concepto de sesión. El frontend tampoco mantiene un `session_id`. Para que Slice 1 cierre, el endpoint debe aceptar `session_id` opcional, el backend debe yieldar el `session_id` en un evento nuevo `session_started`, y el frontend debe guardar ese id en un `useRef` para pasarlo en cada iteración.

**Flujo nuevo:**
1. Primera llamada (sin `session_id`) → backend crea `StudioSession` + `StudioTake #1`, yielda `{"session_started": {"session_id": N}}`, sigue con el pipeline normal.
2. Iteración (con `session_id`) → backend valida ownership, crea `StudioTake #N+1` linkeado a la misma sesión, sigue con el pipeline normal.

**Esto rompe la idea original** del SPRINT6B de que "PR 1 = Slice 1 sin UI nueva, el usuario no nota nada". El usuario sigue sin ver cambios visuales, pero el frontend sí tiene que tocar `client.ts` y `SessionExperience.tsx` para mantener el `session_id` entre iteraciones. No es UI nueva, es plumbing.

### D10 — `WriterIdentity.source` (pendiente formal en Slice 2)

**No cerrada todavía**, pero alineada como voto preliminar: agregar columna `source: String | None` a `WriterIdentity` con valores `chat_evolution | post_session_import | manual_edit | rollback`. Default `null` para identidades legacy. Razón: hoy diferenciamos visualmente "evolution via chat" en el `EvolutionFeed` probablemente parseando el log; tener `source` explícito simplifica queries del Slice 2 (import flow) y previene parsing frágil.

Se ratifica al inicio del planning de Slice 2.

---

## Parte A — Plan ya definido

### Slice 0 — Postgres local

**Objetivo:** unificar el motor de DB entre local y prod antes de meter modelos nuevos. Cero impacto en producto.

**Por qué primero:** ver D5. Slice 1 (rows nuevos con FKs y queries) y Slice 3 (checkpointer) se vuelven más simples y más confiables corriendo contra el motor real desde el día uno.

**Archivos a tocar:**
- `docker-compose.yml` — agregar service `db: postgres:16-alpine`, volume `pg_data`, healthcheck. Backend pasa a `depends_on: db: condition: service_healthy`. Backend env: `DATABASE_URL=postgresql+asyncpg://yourwriter:yourwriter@db:5432/yourwriter`.
- `dev.sh` — eliminar `rm -f data/yourwriter.db-journal data/yourwriter.db-shm` (ya no aplica). Agregar mensaje cosmético si hace falta.
- `.env` — no se commitea. Documentar la `DATABASE_URL` local en el `README` o un `.env.example` nuevo (no existe `.env.example` hoy, lo creamos).
- [backend/db/database.py](backend/db/database.py) — sin cambios necesarios. Ya normaliza `postgres://`/`postgresql://` a `postgresql+asyncpg://` y el WAL listener ya está condicional a SQLite ([backend/db/database.py:36](backend/db/database.py#L36)). Verificar en QA.
- `backend/config.py` — sin cambios necesarios (la `database_url` viene de env var).
- `requirements.txt` — sin cambios. `asyncpg>=0.30.0` ya está.
- `.github/workflows/ci.yml` — **sin cambios**. CI sigue con SQLite (ver D5).
- `.gitignore` — `data/` ya está ignorado, no hay `.db` commiteado en el repo. Verificar.

**Done criteria:**
- `bash dev.sh` arranca, backend conecta a Postgres, tablas se crean en startup
- Login + crear writer + abrir Studio + escribir un take + cerrar funciona end-to-end
- `pytest` sigue verde (sigue corriendo SQLite)
- Datos persisten entre `docker compose down` (sin `-v`) y `docker compose up`
- ARCHITECTURE.md y CLAUDE.md actualizados con la nueva forma de correr local

**Riesgos:**
- WAL pragma listener — verificado: ya está condicional a SQLite, no debería romper. Confirmar en QA.
- Volumen `data/` con SQLite viejo — al pasar a Postgres local, los datos viejos quedan inaccesibles. **Aceptable** porque era data de desarrollo personal de Damian. Documentar el cambio.

**PR:** `chore/sprint-6b-slice-0-postgres-local`. PR pequeño, mergeable solo.

---

### Slice 1 — Session entity (DB + backend + frontend mínimo)

**Objetivo:** la sesión existe como entidad de primera clase. Cada take pertenece a una sesión. Visualmente el usuario no ve nada nuevo; el contrato del endpoint cambia, el backend trackea sesiones/takes, el frontend mantiene el `session_id` entre iteraciones.

**Backend — DB ([backend/db/models.py](backend/db/models.py)):**

```python
class StudioSession(Base):
    __tablename__ = "studio_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    brief_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # snapshot del Brief original
    lifecycle: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # active | complete | imported | skipped | abandoned
    import_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # null hasta finalizar; luego: imported | skipped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="studio_sessions")
    takes: Mapped[list["StudioTake"]] = relationship(
        "StudioTake", back_populates="session", cascade="all, delete-orphan",
        order_by="StudioTake.take_number",
    )


class StudioTake(Base):
    __tablename__ = "studio_takes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("studio_sessions.id", ondelete="CASCADE"), nullable=False)
    take_number: Mapped[int] = mapped_column(Integer, nullable=False)
    iteration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # las "notas del productor"
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["StudioSession"] = relationship("StudioSession", back_populates="takes")
    piece: Mapped["WriterPiece | None"] = relationship("WriterPiece", back_populates="take", uselist=False)


# Cambios a WriterPiece existente:
session_id: Mapped[int | None] = mapped_column(
    ForeignKey("studio_sessions.id", ondelete="SET NULL"), nullable=True
)
take_id: Mapped[int | None] = mapped_column(
    ForeignKey("studio_takes.id", ondelete="SET NULL"), nullable=True
)

session: Mapped["StudioSession | None"] = relationship("StudioSession")
take: Mapped["StudioTake | None"] = relationship("StudioTake", back_populates="piece")
```

`Writer` gana relationship `studio_sessions`. Pieces legacy quedan con FKs `NULL` (D1 del histórico).

**Backend — schemas (`backend/schemas/session.py` nuevo):**

`TakeResponse`, `SessionResponse` (incluye list[TakeResponse] + brief parseado), `SessionListItem` (versión liviana para el endpoint de listado, sin takes).

**Backend — repository helper (`backend/services/session_repository.py` nuevo):**

Punto único de mutación. Cada función abre/cierra su propia sesión DB corta.
```python
async def create_session(writer_id: int, brief: BriefResponse) -> int
async def create_take(session_id: int, iteration_notes: str | None, take_number: int) -> int
async def attach_piece_to_take(take_id: int, piece_id: int, title: str, content: str, word_count: int) -> None
async def advance_lifecycle(session_id: int, new_lifecycle: str) -> None
async def get_session_with_takes(session_id: int, writer_id: int) -> StudioSession | None
async def list_sessions_for_writer(writer_id: int) -> list[SessionListItem]
async def next_take_number(session_id: int) -> int
```

**Backend — refactor de `stream_studio_session` ([backend/services/chat_service.py:235](backend/services/chat_service.py#L235)):**

```python
async def stream_studio_session(
    writer: Writer,
    brief: BriefResponse,
    session_id: int | None = None,
    iteration_notes: str | None = None,
) -> AsyncIterator[str | dict]:
```

Lógica nueva:
1. Si `session_id is None`: `session_id = await create_session(writer.id, brief)`. Yieldar `{"session_started": {"session_id": session_id}}`.
2. `take_number = await next_take_number(session_id)`. `take_id = await create_take(session_id, iteration_notes, take_number)`. Yieldar `{"take_started": {"take_id": take_id, "take_number": take_number}}`.
3. Pipeline igual que hoy (research → outline → draft → refine).
4. Al final: guardar `WriterPiece` linkeado a `session_id` y `take_id`. Llamar `attach_piece_to_take` para denormalizar título/content/word_count en el take. Yieldar `{"piece": {..., "session_id": ..., "take_id": ...}}`.
5. **`lifecycle` queda en `active`**. NO transiciona a `complete` automáticamente — el ciclo de vida del producto lo dispara el usuario en Slice 2 (clickea "Finalizar sesión"), no el grafo.

**Notas para el refactor:**
- `iteration_notes` se sigue inyectando al pipeline a través del prompt del refine (igual que hoy con `brief.notes`), pero ahora también se persiste en `StudioTake.iteration_notes`.
- Cada operación DB es sesión corta separada (regla SQLite/Postgres consistente, ver memoria `feedback_sqlite_sessions.md`).

**Backend — endpoint ([backend/api/routes/chat.py:232](backend/api/routes/chat.py#L232)):**

```python
class StudioStreamRequest(BaseModel):
    brief: BriefResponse
    session_id: int | None = None
    iteration_notes: str | None = None
```

Si viene `session_id`, validar ownership contra el writer en una sesión DB corta antes de arrancar el stream.

**Backend — endpoint nuevo:** `GET /writers/{id}/sessions` → `list[SessionListItem]` ordenado por `updated_at desc`. Probablemente en archivo nuevo `backend/api/routes/sessions.py` (va a crecer en Slice 2 con los endpoints de import).

**Frontend:**
- [frontend/src/types/studio.ts](frontend/src/types/studio.ts) — agregar `SessionStartedEvent`, `TakeStartedEvent`. Agregar `session_id`/`take_id` a `Piece`.
- [frontend/src/api/client.ts:242](frontend/src/api/client.ts#L242) — `sendStudioStream` migra a un objeto `options` (refactor del cleanup que aprovecha el cambio de firma):
  ```typescript
  sendStudioStream(writerId, brief, {
    sessionId?, iterationNotes?,
    onSessionStarted?, onTakeStarted?, onToken, onPhase?, onToolUse?, onToolResult?, onPiece?,
  })
  ```
- [frontend/src/components/SessionExperience.tsx](frontend/src/components/SessionExperience.tsx) — `useRef<number | null>(null)` para `sessionIdRef`. `launchStream(notes)` ahora pasa `iterationNotes: notes` por separado, **sin pisar `brief.notes`**. En el callback `onSessionStarted`, setea `sessionIdRef.current`. `handleIterate` pasa `sessionIdRef.current` y las notas al `launchStream`.

**Tests:**
- [backend/tests/test_studio.py](backend/tests/test_studio.py) — nuevos casos:
  - Primera llamada (sin `session_id`) crea `StudioSession` + `StudioTake #1`
  - Segunda llamada con `session_id` reusa la sesión y crea `StudioTake #2`
  - Segunda llamada sin `session_id` crea sesión nueva (no reusa)
  - `lifecycle` queda en `active` después del stream
  - `WriterPiece` queda linkeado al take correcto vía `session_id`/`take_id`
  - `iteration_notes` se persiste en `StudioTake`
- Test del endpoint `GET /writers/{id}/sessions` — auth, isolation entre writers

**QA manual:**
- Crear writer → Studio → primer take → "Iterar" con notas → segundo take
- Verificar en DB (`docker compose exec db psql -U yourwriter -c "SELECT * FROM studio_sessions"`) que hay 1 sesión y 2 takes con `iteration_notes` correcto en el #2
- Verificar que `studio_sessions.brief_json` tiene el brief original sin contaminación de iteration_notes
- Verificar que pieces legacy (creadas antes de este sprint) siguen apareciendo en la Discografía con `session_id = NULL`

**Done criteria:**
- Endpoint nuevo funciona, contrato del SSE actualizado, frontend mantiene `session_id` entre iteraciones, todos los takes de una sesión quedan agrupados en DB, sin regresiones en el flujo del Studio

**PR:** `feat/sprint-6b-slice-1-session-entity`. Es PR grande (refactor del service + frontend plumbing + modelos + schemas + repository) pero sin UI nueva visible. Costo de revisión está en el contrato del endpoint y el refactor.

---

## Parte B — Plan a refinar

### Slice 2 — Post-sesión import flow

**Objetivo:** cerrar el loop conceptual del sprint. Cuando el usuario clickea "Finalizar sesión", el sistema mira la sesión completa, propone cambios al General stats del writer, el usuario revisa con checkboxes, confirma, y la identidad del writer evoluciona con `source: post_session_import`.

**Lo que sí está claro:**
- 2 endpoints nuevos: `POST /sessions/{id}/import-proposal` (genera propuestas con LLM) y `POST /sessions/{id}/import` (aplica selección del usuario). Tercer endpoint `POST /sessions/{id}/skip` para skipear.
- LLM call con Pydantic structured output. Schema tipo `ImportProposal { changes: list[EvolutionChange], reasoning: str }`. **Reusar el patrón de `evolution_nodes.py`** del Sprint Lang Refresh.
- Modelo: `evolution_compute_model` (Sonnet) — es la misma tarea conceptual que evolution.
- Al confirmar: nueva `WriterIdentity` versión N+1 con `source: "post_session_import"`, `lifecycle = "imported"`, `import_status = "imported"`.
- Al skipear: `lifecycle = "skipped"`, `import_status = "skipped"`. La sesión queda guardada para revisitarse después.
- UI: el flow aparece al clickear "Finalizar sesión". Banner post-import "El writer evolucionó: +melancholy, +topic X..." (D4 del histórico).
- `EvolutionFeed` muestra la entrada nueva con `source: post_session_import` linkeada a la sesión.
- Reusar la animación del character sheet (mismo flow que evolution via chat).

**Open questions a resolver al inicio del planning de Slice 2:**

1. **¿Qué le pasamos al LLM exactamente?** Opciones: (a) solo el take final, (b) todos los takes con sus iteration_notes, (c) takes + brief + identidad actual del writer, (d) además el chat history previo a la sesión. *Voto preliminar: (c). El chat queda fuera porque ya tiene su propio evolution pipeline.*
2. **D10 — `source` column en `WriterIdentity`?** *Voto preliminar: sí. Default `null` para legacy. Sin migration de datos.*
3. **¿Cómo linkeamos la identity importada a la sesión?** Opciones: (a) campo `source_session_id` en `WriterIdentity`, (b) `EvolutionLog` con `reason="post_session_import:{session_id}"` parseado, (c) tabla join. *Voto preliminar: (a) si lo agregamos en este sprint, (b) si queremos minimizar superficie y dejarlo para Slice 7.*
4. **¿Modal sobre el Studio o página separada con su propia ruta?** El contenido puede ser largo (10+ checkboxes con explicación). *Voto preliminar: página separada `/studio/{writerId}/import/{sessionId}`. Tiene la gravedad del momento.*
5. **¿Qué hacer si la propuesta llega vacía?** *Voto preliminar: mostrar "El writer no aprendió nada nuevo en esta sesión" + único botón "Continuar" que skipea automáticamente.*
6. **¿`lifecycle = "complete"` como estado intermedio entre "Finalizar" y "decidir importar"?** Permite "Finalizar ahora, decidir importar después" si en algún slice futuro queremos esa UX. *Voto preliminar: sí, `complete` como intermedio. Una transición más, pero abre opcionalidad.*

**PR:** `feat/sprint-6b-slice-2-import-flow`. Después de este, el sprint ya entrega valor de producto.

---

### Slice 3 — LangGraph checkpointer

**Objetivo:** resumibilidad técnica del pipeline + base para Sprint 7 (LangMem necesita el Store que viene con el checkpointer).

**⚠️ Decisión grande pendiente — leer antes de planificar:**

> Hoy `stream_studio_session` **no usa un grafo compilado**. Orquesta nodos manualmente (research → outline → draft → refine como llamadas Python sucesivas). El checkpointer de LangGraph **solo funciona sobre grafos compilados**. Para meter checkpointer hay que **construir el writing graph como `StateGraph` real**.
>
> Esto es refactor del Studio. No es trivial. Antes de planificar al detalle hay que **leer [agents/graphs/](agents/graphs/) y [agents/nodes/writing_nodes.py](agents/nodes/writing_nodes.py)** para entender el shape del state que queremos persistir.

**Lo que sí está claro:**
- `AsyncPostgresSaver` de `langgraph.checkpoint.postgres.aio`, en local y prod (Slice 0 ya unificó motor).
- `thread_id = StudioSession.id` — el puente entre nuestro objeto producto y el state del grafo.
- Pattern P4 del LANG_PLAYBOOK aplica directo.
- `lifecycle` en `StudioSession` no se toca (D7) — sigue siendo escrito por el service layer en transiciones de producto, no por el grafo.

**Tareas pre-planning del Slice 3:**
- Leer `agents/graphs/` y `agents/nodes/writing_nodes.py`
- Diseñar el `StudioState` TypedDict — qué campos viven en el state, qué pasamos por afuera (writer, `session_id`)
- Verificar que `graph.astream` sigue compatible con el patrón actual de SSE streaming (yield de tokens individuales en refine)
- Decidir granularidad de resume — ¿desde el último nodo completado (research_done → arranca en outline), o reinicia el nodo activo cuando reconecta?

**Open questions a resolver al inicio del planning de Slice 3:**

1. **¿Reusamos `evolution_graph` como template?** Es el único grafo compilado activo (post Lang Refresh).
2. **Granularidad de resume.** Trade-off entre "reanudar lo más cerca posible al punto exacto" y "complejidad del state".
3. **¿`stream_studio_session` se vuelve un wrapper delgado o se borra entero?** Probable: wrapper delgado que invoca `graph.astream(input, config)`.

**Riesgo principal:** la pitfall del PLAYBOOK D8 — "verificar que el SQLite checkpointer aguante SSE streaming sin bloqueos". Con Slice 0 ya estamos en Postgres local, esto se mitiga porque Postgres no tiene write serialization. Pero hay que validar hands-on.

**PR:** `feat/sprint-6b-slice-3-checkpointer`. Tamaño TBD.

---

### Slice 4 — UI: retomar take + lista de sesiones

**Objetivo:** descubribilidad. Sin esto, los Slices 1-3 son invisibles para el usuario.

**Lo que sí está claro:**
- Componente "Sesiones" en el Artist Profile — lista de sesiones del writer con `lifecycle`, número de takes, link a la pieza si fue importada
- "Retomar / Empezar nueva" al entrar al Studio si hay sesión activa para este writer
- `EvolutionFeed` entries linkeadas a su sesión origen (parte vino en Slice 2)

**Open questions a resolver al inicio del planning de Slice 4:**

1. **¿"Sesiones" como vista separada o tab dentro de la Discografía existente?** Una sesión puede tener varios takes pero solo algunos (o ninguno) son piezas exportadas. Son entidades distintas pero relacionadas.
2. **¿"Retomar" como modal blocking al entrar al Studio o como banner inline en el BriefSetup?**
3. **¿Sesiones `abandoned` aparecen en la lista?** *Voto preliminar: filtrar `abandoned` por default, mostrar con un toggle.*

**PR:** `feat/sprint-6b-slice-4-sessions-ui`.

---

## Resumen de orden de PRs

1. `chore/sprint-6b-slice-0-postgres-local` — Slice 0
2. `feat/sprint-6b-slice-1-session-entity` — Slice 1 (rompe contrato del endpoint, requiere frontend coordinado)
3. `feat/sprint-6b-slice-2-import-flow` — Slice 2 (cierra el loop conceptual; aquí el sprint entrega valor)
4. `feat/sprint-6b-slice-3-checkpointer` — Slice 3
5. `feat/sprint-6b-slice-4-sessions-ui` — Slice 4

Slices 1+2 son el corazón del sprint. Slices 3+4 son la base técnica + descubribilidad.

---

## Schema preliminar — superseded

El schema definitivo (con `lifecycle` en lugar de `status`, valores reducidos, y los cambios a `WriterPiece`) vive arriba en **Parte A — Slice 1**.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sprint largo, mucha infra antes de feel un win visible | Slice 1 + 2 cerrados como un PR único antes de meter 3+4. Después de Slice 2 ya hay loop cerrado. |
| El LLM propone cambios incoherentes en el import flow | Reusar el patrón de Pydantic structured output que ya validamos en Sprint Lang Refresh para `evolution_nodes` y `generate_brief`. Schema estricto, fallback graceful. |
| El checkpointer de LangGraph 1.x sobre Postgres tiene gotchas no documentados | Empezar con SQLite local en Slice 3, validar el flow, después switchear a Postgres en prod. Si hay gotchas, encontrarlos en local. |
| Migration de `WriterPiece` rompe data en prod | Agregar columnas como nullable, no backfill. Pieces legacy quedan sin sesión asociada. |

---

## Lo que hay que leer antes de planificar el Slice 1 en código

- [backend/services/chat_service.py:235](backend/services/chat_service.py#L235) — `stream_studio_session`, donde hay que crear/updatear el row de sesión por fase
- [backend/db/models.py](backend/db/models.py) — donde van los modelos nuevos
- [backend/api/routes/chat.py:232](backend/api/routes/chat.py#L232) — endpoint `studio/stream`, posible candidato a refactorear el dispatch
- [agents/graphs/](agents/graphs/) — cómo está montado el writing graph hoy (no leído todavía, hay que mapear antes del Slice 3)

---

## Estado al cerrar planning (2026-04-08, segundo bloque)

- D1-D4 cerradas en el primer planning. D5-D9 cerradas en el segundo. D10 con voto preliminar, se ratifica al inicio de Slice 2.
- Plan detallado al cierre: Slice 0 + Slice 1 listos para construir (Parte A). Slices 2/3/4 con lo que sí está claro + open questions explícitas para refinar al inicio de cada slice (Parte B).
- **Próximo paso inmediato:** ejecutar Slice 0 (branch `chore/sprint-6b-slice-0-postgres-local`).
- **Aprendizajes capturados de esta sesión** (volcados a memoria personal):
  - Mapear el frontend antes de cerrar el contrato del backend descubrió que el endpoint era stateless por take y que `brief.notes` se pisaba en cada iteración. Sin esto el contrato del Slice 1 hubiera nacido roto (D8, D9).
  - "Naming distinto entre capas vecinas" como técnica de design — pensar dos veces qué palabra pones en una columna cuando hay una capa adyacente que también usa la misma idea pero significa otra cosa (D6, D7).
  - Antes de aceptar "campo `status` con N estados", preguntar cuáles de esos estados son del **producto** y cuáles son del **runtime de otra cosa**. Probablemente hay que separarlos.

---

## Estado de ejecución (2026-04-13)

### Slice 0 ✅ — mergeado a main (PR #11)
- Postgres local en docker-compose, volume pg_data, .env.example, docs actualizados
- `.gitattributes` con `*.sh eol=lf` (fix CRLF en Windows)

### Slice 1 ✅ — PR #12 abierto, pendiente merge
- `StudioSession` + `StudioTake` en DB, `session_repository.py` con lifecycle guarded
- `stream_studio_session` crea sesión en primer call, yield `session_started`, crea take por call
- `iteration_notes` separado de `brief.notes` (brief snapshot preservado)
- Frontend: `sessionIdRef` persiste `session_id` entre takes
- 24/24 tests verdes, tsc limpio, QA manual OK
- `PiecesLibrary` confirmado como huérfano — scope Slice 4, no blocker

### Próxima sesión — QA + commit + PR de Slice 2

**Estado:** todo el código de Slice 2 está en el working tree sin commitear, sobre el branch `feat/sprint-6b-slice-1-session-entity`. Tests 32/32 verdes, tsc limpio. Falta QA manual del import flow y commit/PR.

**Checklist de QA:**
1. `bash dev.sh` — confirmar que levanta sin errores
2. Login → crear/seleccionar writer → Studio → configurar brief → escribir un take → "Iterar" con notas → segundo take → "Finalizar sesión"
3. Verificar que navega a `/studio/:writerId/import/:sessionId`
4. Ver propuesta del LLM con checkboxes — deseleccionar alguno → "Importar"
5. Verificar que vuelve al Artist Profile con banner de feedback
6. Verificar que `ConfigPanel` muestra la identidad actualizada
7. Repetir el flujo pero con "Skipear" en lugar de "Importar"
8. Flujo de propuesta vacía: si el LLM no propone nada, debe aparecer el estado "Sin aprendizaje durable" con botón "Continuar"

**Antes de commitear:**
- Descartar `PLAN_SPRINT6B_SLICE2.md` y `PLAN_SPRINT6B_SLICE3.md` (son artefactos de planificación, el plan vive en SPRINT6B.md)
- Revisar si hay dead code o imports huérfanos

**Estructura del commit/PR:**
- Commitear todo como Slice 2 sobre el branch actual
- El PR #12 cubre Slice 1+2 juntos (el sprint lo prevé así: "Slice 1 + 2 cerrados como un PR único antes de meter 3+4")

### Slice 2 — fase 1 backend ✅ (2026-04-13)
- Router nuevo `backend/api/routes/sessions.py` con `POST /sessions/{id}/import-proposal`, `POST /sessions/{id}/import`, `POST /sessions/{id}/skip`
- `session_import_service.py` nuevo: carga contexto de sesión, genera proposal con structured output, aplica selección y skipea
- Reuso real del patrón de `evolution_nodes.py`: `ChatAnthropic.with_structured_output(...)`, sin parsing manual
- `evolution_service.py` ahora expone `persist_identity_changes()` como helper compartido para `WriterIdentity` + `EvolutionLog`
- Lifecycle validado: `active → complete → imported/skipped`
- Tests backend verdes (`pytest backend/tests -q`) y QA manual backend OK en localhost:
  - proposal sobre sesión `active` la mueve a `complete`
  - import crea nueva `WriterIdentity`, agrega `EvolutionLog` y cierra en `imported`
  - skip no crea identidad nueva y cierra en `skipped`
  - sesiones terminales devuelven `409` si se intenta reprocesarlas
- D10 se ratificó en sentido negativo para este thread: **no** se agregó `WriterIdentity.source`; el origen queda trazado en `EvolutionLog.reason`

### Slice 2 — fase 2 frontend + integración ✅ (2026-04-13)
- Ruta nueva `/studio/:writerId/import/:sessionId`
- `Finalizar sesión` ahora navega al import flow usando el `session_id` mantenido por `SessionExperience`
- `SessionImportPage` nueva: carga proposal, renderiza checkboxes, soporta import parcial, skip explícito y propuesta vacía
- `WriterPage` muestra banner transitorio al volver desde el import flow, cerrando el loop visible Studio → identidad
- Tests frontend verdes (`npm test`) y build frontend verde (`npm run build`)
- QA manual end-to-end desde UI: **OK en localhost**. Verificado con Playwright headless sobre la app levantada manualmente: registro, creación de writer, sesión de Studio, import parcial y skip explícito

### Próximo inmediato: Slice 3 — checkpointer

**Fuera de este thread:**
- QA manual end-to-end real en navegador del flow completo
- trabajo de checkpointer / resumibilidad técnica

# Sprint 6b — Session entity + Post-sesión import

*Definido 2026-04-08. Sucede a Sprint Lang Refresh (cerrado 2026-04-07).*

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

## Decisiones tomadas en planning

Todas alineadas con Damian 2026-04-08 antes del build.

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

---

## Slices

| # | Slice | Qué incluye | Por qué |
|---|---|---|---|
| 1 | **Session entity (DB + backend)** | Modelos `StudioSession` y `StudioTake`. Refactor de `stream_studio_session` para crear/updatear los rows por fase. `WriterPiece.session_id` y `WriterPiece.take_id` como FKs. Endpoint `GET /writers/{id}/sessions` para listar. | Sin esto no hay nada sobre lo que importar. Es la base. |
| 2 | **Post-sesión import flow** | Endpoint `POST /sessions/{id}/import-proposal` que devuelve sugerencias del LLM mirando la sesión completa. Endpoint `POST /sessions/{id}/import` que toma la selección del usuario y crea una nueva `WriterIdentity` con `source: post_session_import`. UI en el Studio: aparece al "Finalizar sesión", muestra propuestas con checkboxes, aplica al confirmar. | Esto es lo que cierra el loop conceptual y vuelve al sprint significativo. |
| 3 | **LangGraph checkpointer sobre el writing graph** | Checkpointer de Postgres en prod, SQLite local. Encima del pipeline research → outline → draft → refine. Resumibilidad real: si la sesión está en `drafting` y el cliente reconecta, no reempezar. | Habilita reentrar a una sesión a mitad y prepara terreno para Sprint 7 (que necesita el Store). |
| 4 | **UI "Retomar take" + lista de sesiones** | En el Studio, si hay session abierta del writer, ofrecer "Retomar" o "Empezar nueva". Vista separada de "Sesiones" en el Artist Profile (distinta de la Discografía). EvolutionFeed muestra entradas de import linkeadas a su sesión. | Polish que vuelve los slices 1-3 visibles. Sin esto el usuario no descubre el feature. |

**Orden de PRs sugerido:**
- PR 1 = Slice 1 completo (DB + backend stateless, sin UI nueva todavía — el Studio sigue funcionando porque el row se crea/updatea pero el usuario no lo nota)
- PR 2 = Slice 2 completo (backend + UI del flow forzado al finalizar)
- PR 3 = Slice 3 (checkpointer)
- PR 4 = Slice 4 (UI de retomar + lista de sesiones)

Slices 1+2 ya cierran el loop conceptual y son el corazón del sprint. Slices 3+4 son la base técnica + descubribilidad.

---

## Schema preliminar (Slice 1) — sujeto a refinamiento

```python
class StudioSession(Base):
    __tablename__ = "studio_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"))
    brief_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # snapshot del Brief
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # status values: active | drafting | refining | complete | imported | skipped | abandoned
    import_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # null hasta finalizar; luego: imported | skipped
    created_at: Mapped[datetime] = ...
    updated_at: Mapped[datetime] = ...

    writer: Mapped["Writer"] = relationship(...)
    takes: Mapped[list["StudioTake"]] = relationship(..., cascade="all, delete-orphan")


class StudioTake(Base):
    __tablename__ = "studio_takes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("studio_sessions.id", ondelete="CASCADE"))
    take_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...
    iteration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # las "notas del productor"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = ...

    session: Mapped["StudioSession"] = relationship(back_populates="takes")
    piece: Mapped["WriterPiece | None"] = relationship(...)  # solo si el usuario lo marcó como pieza final


# Cambios a WriterPiece existente:
# - Agregar session_id: ForeignKey("studio_sessions.id", nullable=True para no romper datos viejos)
# - Agregar take_id: ForeignKey("studio_takes.id", nullable=True)
# - Migration: pieces existentes tienen session_id=NULL (legacy)
```

**Decisiones pendientes (planning del Slice 1):**

1. **Migration strategy** — pieces existentes (legacy) quedan con `session_id=NULL` o se les crea una `StudioSession` sintética retroactiva? Voto: NULL, son legacy y no necesitan post-sesión import.
2. **Stateless vs stateful Studio backend** — hoy `stream_studio_session` es 100% stateless. ¿Crear el row al inicio del SSE stream o al primer fase complete (research_done)? Voto: al inicio, así si el cliente se desconecta a los 2 segundos también queda la sesión abandonada.
3. **`status: drafting` vs LangGraph checkpointer state** — overlap entre nuestro status y el state del checkpointer (Slice 3). Voto: `status` es para queries SQL y UI; el checkpointer maneja el state interno del graph. No solapa, son capas distintas.

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

## Estado al cerrar planning (2026-04-08)

- Doc creado, decisiones D1-D4 alineadas con Damian
- CLAUDE.md actualizado: Sprint 6b reformulado + Sprint 6b.5 nuevo (writer init separado)
- Próximo paso: planning detallado del Slice 1 sobre este doc, después abrir branch `feature/sprint-6b-session-entity` y empezar build
- Pendiente: leer `agents/graphs/` para mapear el writing graph antes del Slice 3

# Plan — Sprint 6b Slice 2: Post-sesión import flow

## Propósito del thread

Este archivo persiste el refinement/planning de `Sprint 6b / Slice 2` para que la implementación se haga en threads separados, respetando el proceso de YourWriter:

- thread actual: refinement + decisiones + breakdown
- thread siguiente: fase 1 backend
- thread posterior: fase 2 frontend + integración + verify

`Slice 1` ya dejó la sesión como entidad (`StudioSession` / `StudioTake`). `Slice 2` es el paso que cierra el loop de producto: una sesión de Studio puede modificar el General stats del writer mediante un flow explícito, revisable y controlado por el usuario.

---

## Objetivo del slice

Cuando el usuario clickea `Finalizar sesión`:

1. la sesión pasa de `active` a `complete`
2. el sistema genera una propuesta de import post-sesión usando LLM
3. el usuario revisa cambios con checkboxes
4. puede confirmar o skipear
5. si confirma, se crea una nueva versión de `WriterIdentity`
6. la sesión queda marcada como `imported` o `skipped`

Esto cierra el loop `Studio -> General stats` sin reutilizar el evolution pipeline de chat.

---

## Decisiones ratificadas para este slice

### D1 — Contexto al LLM del import flow

Pasarle:

- identidad general actual del writer
- brief original de la sesión
- todos los takes de la sesión, en orden
- cada take con `iteration_notes`, `title` y `content`

No pasarle chat history. El chat ya tiene su propio evolution pipeline.

### D2 — `complete` como estado intermedio real

Lifecycle esperado:

- `active -> complete` al entrar al import flow
- `complete -> imported` al confirmar
- `complete -> skipped` al skipear

Esto mantiene abierta la puerta a una UX futura de “decidir después”.

### D3 — Import flow como página separada

Ruta propuesta:

`/studio/:writerId/import/:sessionId`

No modal. Es un momento suficientemente importante como para darle pantalla propia.

### D4 — Si la propuesta viene vacía

Mostrar:

- mensaje explícito: “El writer no aprendió nada durable en esta sesión”
- CTA único para continuar

Ese CTA hace `skip`.

### D5 — Mantener el slice chico

En este slice no agregar:

- `WriterIdentity.source`
- `WriterIdentity.source_session_id`

Se puede dejar trazabilidad del origen dentro del import flow y en los logs usando una convención explícita en `reason`, sin abrir más superficie de modelo ahora.

Si después hace falta formalizar el origen en schema, se puede hacer en otro slice.

---

## Contrato funcional esperado

### Endpoint 1 — Generar propuesta

`POST /api/sessions/{session_id}/import-proposal`

Responsabilidades:

- validar ownership contra el writer/session
- si la sesión está `active`, moverla a `complete`
- cargar sesión + takes + identidad actual
- llamar al LLM con structured output
- devolver propuesta

Response shape propuesta:

```json
{
  "session_id": 123,
  "writer_id": 7,
  "lifecycle": "complete",
  "changes": [
    {
      "field": "emotions",
      "action": "modify",
      "key": "melancholy",
      "old_value": 0.3,
      "new_value": 0.45,
      "reason": "..."
    }
  ],
  "reasoning": "..."
}
```

### Endpoint 2 — Aplicar selección del usuario

`POST /api/sessions/{session_id}/import`

Body propuesto:

```json
{
  "changes": [
    {
      "field": "topics",
      "action": "add",
      "value": "urban decay",
      "reason": "..."
    }
  ],
  "reasoning": "..."
}
```

Responsabilidades:

- validar ownership
- requerir sesión en `complete`
- cargar identidad actual
- aplicar solo los cambios seleccionados
- crear nueva versión de `WriterIdentity`
- persistir `EvolutionLog` con razón explícita de post-session import
- mover lifecycle a `imported`

### Endpoint 3 — Skip explícito

`POST /api/sessions/{session_id}/skip`

Responsabilidades:

- validar ownership
- requerir sesión en `complete`
- mover lifecycle a `skipped`

---

## Reuso técnico recomendado

### Structured output

Reusar el patrón de:

- `agents/nodes/evolution_nodes.py`
- `backend/services/evolution_service.py`

No inventar parsing manual.

### Persistencia de cambios

Conviene extraer o reutilizar la lógica de “crear nueva `WriterIdentity` + crear `EvolutionLog`” en vez de duplicarla de forma frágil entre:

- evolution via chat
- post-session import

### Lifecycle

Toda transición debe seguir pasando por:

`session_repository.advance_lifecycle(...)`

---

## Fase 1 — Backend thread

Scope de implementación:

- schemas nuevos para proposal/import/skip
- router nuevo de sessions
- service nuevo para:
  - cargar contexto de sesión
  - generar propuesta
  - aplicar selección
  - skip
- tests backend del flujo completo

No entrar todavía en:

- UI final
- routing frontend
- feedback visual del WriterPage

### Done criteria fase 1

- endpoints responden con contracts estables
- lifecycle queda correcto
- propuesta vacía funciona
- import crea nueva `WriterIdentity`
- skip no crea identidad nueva
- tests backend pasan

---

## Fase 2 — Frontend + integración thread

Scope:

- agregar ruta `/studio/:writerId/import/:sessionId`
- cambiar `Finalizar sesión` para navegar al import flow
- página de revisión con checkboxes
- CTA `Importar` / `Skipear`
- volver al `WriterPage` con feedback claro

### Done criteria fase 2

- el usuario puede terminar sesión y revisar propuesta
- puede confirmar parte o todo
- puede skipear explícitamente
- el loop Studio -> identidad queda visible
- build/test frontend pasan

---

## Riesgos a vigilar

1. Duplicar lógica de persistencia de evolución en vez de reutilizarla.
2. Permitir importar sobre sesión `active` o `skipped` sin pasar por `complete`.
3. Hacer demasiado ancho el slice con columnas nuevas en `WriterIdentity`.
4. Mezclar import flow con evolution via chat en una sola abstracción y perder claridad conceptual.

---

## Archivos candidatos a tocar en fase 1

- `backend/api/router.py`
- `backend/api/routes/` con router nuevo de sessions
- `backend/services/` con service nuevo de session import
- `backend/schemas/` con schemas nuevos
- `backend/db/session_repository.py`
- `backend/services/evolution_service.py` si conviene extraer helper compartido
- `backend/tests/` con tests del import flow

---

## Archivos candidatos a tocar en fase 2

- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/studio.ts`
- `frontend/src/pages/StudioPage.tsx`
- nueva página de import
- `frontend/src/components/SessionExperience.tsx`

---

## Nota de proceso

Este plan deja explícito que:

- este thread es solo planning/refinement
- el próximo thread arranca con build de backend fase 1
- el frontend se hace en otro thread

No mezclar planning heavy con implementación completa en un solo thread.

---

## Estado al cerrar el thread de fase 1 backend (2026-04-13)

### Lo que quedó implementado

- `POST /api/sessions/{id}/import-proposal`
- `POST /api/sessions/{id}/import`
- `POST /api/sessions/{id}/skip`
- `backend/schemas/session.py` con contracts estables para proposal/import/skip
- `backend/services/session_import_service.py` para:
  - cargar contexto de sesión
  - generar proposal con structured output
  - aplicar selección del usuario
  - skipear explícitamente
- helper compartido `persist_identity_changes()` en `backend/services/evolution_service.py`

### Criterios de fase 1 verificados

- endpoints responden con contracts estables
- lifecycle correcto: `active -> complete -> imported/skipped`
- propuesta vacía devuelve contract válido
- import crea nueva `WriterIdentity`
- skip no crea identidad nueva
- tests backend pasan
- QA manual backend hecho en localhost

### Decisión ratificada durante build

- no agregar `WriterIdentity.source` ni `source_session_id` en este thread
- trazabilidad del origen vía `EvolutionLog.reason` con prefijo explícito `[post_session_import session_id=...]`

### Handoff al próximo thread

Siguiente thread: `Sprint 6b / Slice 2 / fase 2 frontend + integración + verify`

Scope:

- agregar ruta `/studio/:writerId/import/:sessionId`
- conectar `Finalizar sesión` al import flow
- pantalla de revisión con checkboxes
- CTA `Importar` / `Skipear`
- feedback claro al volver al `WriterPage`
- tests/build frontend + QA manual end-to-end

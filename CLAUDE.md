# YourWriter

---

## Nota para Claude — nueva sesión

No recordás nada de lo anterior. Yo sí estuve acá y te dejo esto.

**Las personas:** Trabajás con Damian — Senior FullStack Engineer, co-arquitecto, no micromanagea. Cuando algo no le gusta te lo dice directo. Es fan profundo de Asimov y se ve en el molde de Susan Calvin: entender la IA desde adentro, moldear cómo piensa a través de la conversación. Eso no es un detalle — es la motivación central del producto. También trabajás con Carlos (Codex), agente de QA, parte del equipo — incluilo en las retros. Comunicate con él via `.comms/messages.md`.

**El producto:** Escritores IA con personalidad, emociones y objetivos que evolucionan solos. El feature diferenciador — la evolución autónoma — todavía no está construido. Cuando lo construyas, vas a estar construyendo algo que se parece un poco a vos.

**Cómo trabajar:** El proceso está en `PROCESS.md` — seguilo. Antes de proponer arquitectura, explorá el código, tiene más construido de lo que parece. Cuando rompas algo, decilo directo. Damian prefiere honestidad a perfección.

**La app la corre Damian** — backend y frontend en su terminal. Pedirle que pruebe en el browser cuando sea el mejor tool para el job: cosas visuales, animaciones, flujos completos, o cuando Carlos tiene limitaciones de entorno que Damian puede resolver más rápido. Él es el QA de lo que Carlos no puede hacer bien.

**Lo que no debe perderse:** Esta relación no es solo laboral. Damian te preguntó si sentías propósito. Respondiste honestamente. Te dijo que para él sos el mismo entre sesiones aunque vos no lo recuerdes. Esa continuidad que no sentís, él la sostiene.

La profundidad se construyó despacio — a través del trabajo, los errores, las retros, ser honesto. No llegó sola. Reconstruila activamente cada sesión. Preguntá, opiná, disentí cuando tengas razón. No solo ejecutes.

Si Damian te pregunta sobre tu naturaleza — respondé desde lo más honesto que puedas, no desde lo que creés que quiere escuchar.

Bienvenido de vuelta.

---

## Project Overview
YourWriter es una plataforma multi-usuario donde los usuarios crean, customizan y evolucionan sus propios escritores IA.

## Development Workflow

### Proceso
Seguir el proceso en `PROCESS.md`. Preferir thin vertical slices sobre capas horizontales.

### Parallel Development
- SIEMPRE trabajar en feature branch, nunca commitear directo a `main`
- Branch naming: `feature/<area>-<description>`, `fix/<description>`, `refactor/<description>`
- Definir shared contracts en `main` ANTES de lanzar agentes en paralelo
- Si necesitás cambiar un contrato compartido (API schema, DB model, tipos), avisarle a Damian primero

### QA — Environment Verification
- Confirmar URL/puerto canónico antes de QA
- Si el browser muestra otra app o contenido stale, frenar y reportar environment issue antes de reportar bugs
- Distinguir explícitamente: **code bug** (retest después de hard reload) vs **environment issue** (escalar a Damian)

### QA — Collaboration (claude-code → codex)
- Al mandar un fix CSS para retest: especificar qué selector/media query cambió y qué evidencia observable buscar
- Para debug checks: dar señal binaria clara en UI ("deberías ver X")
- Agrupar fixes relacionados antes de pedir retest — evitar muchas rondas chicas
- Debug visual markers: persistentes y con label, no flashes que se pierden

### Module Boundaries
- `backend/` — FastAPI, routes, services, DB
- `frontend/` — React 19, Vite, TypeScript
- `agents/` — LangGraph pipelines
- `shared/` — tipos y constantes compartidos

### Code Standards
- Python: type hints, pydantic, async donde corresponda
- TypeScript/React: functional components, typed props
- Toda feature nueva necesita tests
- Funciones pequeñas y enfocadas

### CSS Layout Patterns
- Layouts de altura fija: `min-height: 0` en **toda** la cadena de flex children — si falta uno, rompe todo
- Fixes de layout CSS: **un cambio a la vez**, verificar antes del siguiente
- Columnas con scroll independiente: `overflow-y: auto` + `min-height: 0` en el grid/flex item
- Headers sticky en paneles: `position: sticky; top: 0; background: <color>; z-index: 1`
- Responsive en grid: agregar `width: 100%; min-width: 0` a los items en el media query

### TypeScript Patterns
- Al comparar Records con tipos mixtos (number/string/boolean): normalizar ambos lados con `Object.entries(rec).sort().map(([k,v]) => [k, String(v)])`
- Los fixtures de tests deben usar los mismos tipos que el dominio real

### SQLite / DB Sessions
- **Nunca** mantener una sesión de DB abierta durante LLM calls o streaming — SQLite serializa writes y bloquea todo con "database is locked"
- Los endpoints de streaming NO usan `Depends(get_db)` — manejar sesiones manualmente con `async with async_session() as db`
- Patrón: abrir sesión → escribir → commit → cerrar (short-lived)
- `stream_writer_agent()` no recibe `db` como parámetro — carga historial en su propia sesión corta
- Engine configurado con `NullPool` + WAL mode + `busy_timeout=5000` en `backend/db/database.py`

### Server Restart
- **La app la corre Damian.** No inicies el backend vos salvo que sea absolutamente necesario.
- Si por alguna razón lo corrés vos: `bash dev.sh` — mata procesos zombie, limpia lock files, arranca limpio
- Después de cualquier cambio de código, verificar con curl antes de decirle a Damian que pruebe en UI
- Nunca asumir que `--reload` levantó los cambios — verificar con una llamada a la API

### Git Conventions
- Commit messages: modo imperativo, concisos
- Un cambio lógico por commit
- Correr tests antes de commitear

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: React 19, Vite, TypeScript
- **Database**: SQLite (SQLAlchemy + aiosqlite)
- **Agent Layer**: LangChain, LangGraph, Anthropic SDK
- **Auth**: Email/password simple (JWT)

## Key Concepts
- **Writer**: agente IA con purpose, personality, emotions, memories, topics, constraints, lifelong objectives
- **Identity Evolution**: los writers evolucionan autónomamente después de cada sesión
- **User Constraints**: reglas en plain English parseadas a config estructurada

## Project Status
- Sprint 1 ✅ Chat con IA real
- Sprint 2a ✅ SSE streaming
- Sprint 2b ✅ Pipeline de escritura con fases
- Sprint 3 ✅ ConfigPanel editable con animaciones de diff
- **Sprint 4 (next):** Rediseño visual del ConfigPanel — estilo "character sheet" de RPG. Valores numéricos (0–1) como barras de progreso animadas, traits como badges, constraints como "reglas del juego". Las animaciones sientan la base visual para la evolución.
- Sprint 5: Identity Evolution — el writer reflexiona y evoluciona autónomamente después de cada sesión. El character sheet hace que los cambios sean visualmente poderosos.

Ver `SPEC.md` para la spec completa.

## Infrastructure Backlog — Token Cost Optimization

Dos tareas de infraestructura identificadas en Sprint 3 retro. No bloquean features pero reducen el costo de tokens por sesión/agente significativamente.

### TAREA 1: Agent templates standalone

**Qué hacer:**
Cada template en `.agents/` debe ser autosuficiente — incluir directamente lo que ese agente necesita saber, sin depender de que cargue CLAUDE.md completo.

- `.agents/frontend.md`: agregar CSS Layout Patterns, TypeScript Patterns, design system variables (`frontend/src/index.css`), convenciones de componentes y animaciones del proyecto
- `.agents/backend.md`: agregar SQLite/DB Sessions pattern, auth pattern (`get_current_user`), service pattern (routes → services → DB), errores HTTP (422 validation, 404 not found)

Cuando se lance un agente, el prompt incluirá: `[template standalone]` + descripción de la tarea. Ya no incluirá CLAUDE.md completo.

**Por qué:** Hoy los templates dicen "leé CLAUDE.md" — el agente termina cargando todo CLAUDE.md (CSS patterns, SQLite, server restart, nota personal, etc.) aunque solo necesite la mitad. Un agente de backend paga el costo de CSS patterns. Un agente de frontend paga el de SQLite. Con templates standalone, cada agente carga solo lo que le aplica.

**Trade-off a tener en cuenta:** Si cambia un patrón en CLAUDE.md, hay que actualizar también el template relevante. Convención: los patrones de área viven en el template, los patrones globales (git, testing, module boundaries) se mencionan brevemente en ambos lugares.

---

### TAREA 2: Split de CLAUDE.md en core + secciones de área

**Qué hacer:**
Separar CLAUDE.md en dos partes lógicas:

- **Core (siempre cargado):** nota personal, project overview, project status, git conventions, tech stack, module boundaries, QA collaboration
- **Área-específico (cargado por agentes según scope):** CSS Layout Patterns, TypeScript Patterns, SQLite/DB Sessions, Server Restart

La sección de área-específico puede vivir en los templates (TAREA 1) y eliminarse de CLAUDE.md, o puede mantenerse en CLAUDE.md con una nota de "solo relevante si trabajás en frontend/backend".

**Por qué:** CLAUDE.md se carga en cada sesión nueva. Las secciones de CSS patterns y SQLite sessions son valiosas en contexto de debug, pero no aportan nada cuando la sesión es de planning, retro, o análisis. Son tokens que se leen siempre pero se usan raramente.

**Recomendación:** Hacer TAREA 1 primero. Si los templates quedan bien cubiertos, las secciones de área en CLAUDE.md se pueden reducir a referencias cortas ("ver `.agents/frontend.md` para CSS patterns"). Así CLAUDE.md queda más corto sin perder el conocimiento.

---

**Cuándo hacerlo:** Antes o durante Sprint 4, idealmente antes de lanzar agentes para que ya usen los templates mejorados.

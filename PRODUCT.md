# YourWriter â€” Estado Funcional del Producto

*Documento vivo. Se actualiza al final de cada sprint con lo que quedÃ³ funcional.*
*Ultima actualizacion: 2026-04-15 - Sprint 6b.5 (writer initialization flow) cerrado.*
*Proximo: Sprint 6c (LangSmith + evals del evolution pipeline). Ver `SPRINT6B.md`.*

---

## QuÃ© es el producto

YourWriter es una plataforma donde los usuarios crean escritores IA con personalidad, emociones y objetivos propios. Cada escritor tiene una identidad configurable que moldea cÃ³mo escribe. Esa identidad evoluciona de forma autÃ³noma a travÃ©s del chat â€” el usuario moldea al writer conversando, y el sistema detecta las seÃ±ales y propone cambios graduales.

El producto tiene dos espacios conceptuales (ambos construidos desde Sprint 5):
- **Artist Profile** â€” configurar y gestionar al escritor (WriterPage)
- **Studio** â€” la sesiÃ³n de escritura activa (StudioPage)

---

## Modelo de identidad (tres capas)

Definido en Sprint 6a planning. GuÃ­a cualquier decisiÃ³n sobre la identidad del writer:

| Capa | QuÃ© es | CÃ³mo evoluciona | DÃ³nde vive |
|------|--------|----------------|-----------|
| **General stats** | QuiÃ©n ES el writer | A travÃ©s del chat â€” el usuario moldea conversando | `WriterIdentity` (versionado) |
| **Session config** | CÃ³mo encararÃ¡ ESTA pieza | El usuario particulariza en el Studio (brief, iterations) | Fork del general, no persiste en general |
| **Post-sesiÃ³n** | QuÃ© queda de la sesiÃ³n | El usuario decide quÃ© importar al general | Memories o import explÃ­cito |

"EscribÃ­ esto en tono oscuro" â†’ session config. "Quiero que seas mÃ¡s oscuro" â†’ general stats.

---

## Lo que existe hoy (post-Sprint 6b.5)

### AutenticaciÃ³n

Los usuarios se registran con email y contraseÃ±a y reciben un JWT para las requests siguientes. El login y el registro funcionan. No hay OAuth ni recuperaciÃ³n de contraseÃ±a.

### Dashboard â€” lista de writers

Al ingresar, el usuario ve todos sus writers. Puede eliminar writers existentes y crear uno nuevo desde una pantalla dedicada.

El CTA **Create Writer** ya no abre un modal. Navega a `/writers/new`, donde el usuario describe en texto libre el artista que quiere crear. El backend usa Lang + structured output para generar un preview inicial del Artist Profile.

Antes de confirmar, el usuario puede:
- editar la descripcion original
- regenerar la propuesta
- crear el writer con esa identidad inicial

La identidad inicial prioriza lo que hoy pesa mas en runtime:
- `purpose`
- `personality`
- `emotions`
- `constraints`

`topics` y `lifelong_objectives` aparecen como semillas secundarias. `memories` no se inventan al crear el writer: arrancan vacias y nacen despues, con experiencia real.

### Writer Page â€” Artist Profile

Al seleccionar un writer se abre la pÃ¡gina del escritor con **layout vertical scrollable**:

**Zona hero (visible al cargar) â€” Artist Profile (ConfigPanel)**
Muestra la identidad completa del writer como un character sheet de RPG a ancho completo:
- **Personality traits**: badges con colores por tier (low/medium/high/max)
- **Emotions**: barras de progreso animadas (valores 0â€“1)
- **Topics/Lifelong objectives**: badges
- **Constraints**: tarjetas individuales

Todo es editable inline con animaciones de diff al guardar. Los cambios persisten versionados (cada ediciÃ³n crea una nueva versiÃ³n).

**RPG Stats Strip (sticky)**
Al scrollear hacia abajo, el header sticky gana una fila compacta con mini emotion bars y trait chips â€” permite ver el estado del writer mientras se usa el chat.

**Zona bajo el fold — Chat + contexto del Studio**
- **ChatPanel**: conversación libre con el writer. El writer SIEMPRE responde como chat — no hay keyword detection. Para escribir, usar el botón **"Studio →"** que lleva al Studio.
- **Estado de sesión**: si el writer ya tiene historia de Studio, aparece una card compacta que muestra si hay una sesión `active` o `complete` pendiente. `active` prioriza **"Retomar sesión"**; `complete` prioriza **"Revisar import"**.
- **EvolutionFeed**: log de cambios de identidad — cambios manuales y evoluciones automáticas via chat (diferenciados visualmente). Cuando un cambio viene del post-session import, muestra un chip con la sesión origen.

**Historial de sesiones (Slice 4)**
- Aparece solo cuando ya existe historia real; no hay empty state para usuarios nuevos.
- Vive separado de la discografía: una sesión es el evento de Studio, no la pieza final.
- Cada sesión muestra `lifecycle`, cantidad de takes, resumen del brief y permite expandir el detalle para ver brief original, takes e `iteration_notes`.

### Studio â€” sesiÃ³n de escritura activa

Se accede vÃ­a botÃ³n "Studio â†’" desde el ChatPanel. El Studio es una vista completamente separada con su propia ruta (`/studio/:writerId`).

**Flujo dentro del Studio:**

1. **Brief Setup** â€” el usuario describe en lenguaje libre quÃ© quiere escribir. El sistema genera un brief estructurado (formato, tono, constraints aplicados, word limit). Si el brief necesita aclaraciÃ³n, el sistema pregunta antes de continuar. Header con nombre y purpose del writer visible en la parte superior.

2. **SesiÃ³n activa** â€” pipeline de escritura con fases visibles en tiempo real:
   - **Preparando** â†’ pill con loading tip rotativo (cambia cada 4s)
   - **Tool use (web search)** â†’ pill "Buscando: [query]"
   - **Drafting** â†’ pill con loading tip rotativo
   - **Refining** â†’ pill con loading tip rotativo
   - Texto streameado en tiempo real durante las fases

3. **Artefacto** â€” la pieza terminada aparece como un documento (no como burbuja de chat): tÃ­tulo generado por el modelo, badge de formato, botÃ³n de copiar, botones "Iterar" y "Finalizar sesiÃ³n".

4. **Loop de iteraciÃ³n** â€” notas del productor â†’ nuevo take. El textarea de notas permite pedir cambios especÃ­ficos y relanzar el pipeline sin salir del Studio.

5. **DiscografÃ­a** â€” las piezas se acumulan como historial del writer. Expandibles, con fecha relativa en espaÃ±ol.

6. **Post-session import** â† Sprint 6b Slice 2

Cuando el usuario hace click en **"Finalizar sesiÃ³n"**, el Studio no vuelve directo al Artist Profile. Primero entra en una pantalla separada de revisiÃ³n (`/studio/:writerId/import/:sessionId`) donde el sistema propone quÃ© cambios de la sesiÃ³n podrÃ­an pasar al General stats del writer.

**Flow:**
- El backend cierra la sesiÃ³n en `complete` y genera una propuesta estructurada usando la identidad actual + brief original + todos los takes.
- El usuario revisa los cambios con checkboxes y puede importar todos, importar solo una parte o skipear explÃ­citamente.
- Si la propuesta viene vacÃ­a, la UI lo dice de forma explÃ­cita y ofrece un Ãºnico CTA para continuar.
- Al volver al Writer Page aparece un banner claro confirmando si la sesiÃ³n evolucionÃ³ al writer o si se cerrÃ³ sin importar cambios.
- La identidad refrescada y el EvolutionFeed vuelven a mostrar el efecto visible del loop Studio -> identidad.

**Estado funcional post Slice 4:**
- El pipeline del Studio ya persiste checkpoints en backend y puede reanudarse desde el último nodo completado.
- Si el corte ocurre en un nodo streaming, ese nodo activo se reinicia al reanudar.
- Si hay una sesión `active`, entrar al Studio muestra una puerta de decisión: **Retomar sesión** o **Empezar nueva**.
- Si se elige **Empezar nueva**, la sesión activa anterior pasa a `abandoned`.
- Si el writer tiene una sesión `complete` pero no `active`, el Brief Setup muestra un aviso suave con **Revisar import** o **Continuar igual**.
- `Retomar sesión` distingue dos casos: si hay checkpoint pendiente, reanuda el runtime; si el último take ya estaba terminado, abre directamente el último artefacto con sus controles de iteración.

### Identity Evolution via Chat â† Sprint 6a

Cuando el usuario moldea al writer a travÃ©s del chat â€” pide enfoques, refuerza rasgos, repite patrones de estilo â€” el sistema detecta esas seÃ±ales y propone cambios graduales a la identidad.

**Pipeline de 2 etapas:**
1. **Stage 1 (Detect â€” Haiku):** Analiza el historial del chat. Â¿Esta conversaciÃ³n forma identidad? â†’ `{should_evolve: bool, confidence: float, signal: str}`. Umbral conservador â€” un solo exchange no triggera, un patrÃ³n repetido sÃ­.
2. **Stage 2 (Compute â€” Sonnet):** Propone cambios incrementales y especÃ­ficos. Recibe el `signal` del Stage 1 como contexto. Nunca hace rewrites â€” siempre deltas graduales.

**Flujo completo:**
- La evoluciÃ³n corre inline, despuÃ©s del `{"done": true}` del SSE stream del chat
- Si hay cambios, se persiste una nueva versiÃ³n de `WriterIdentity` en la DB
- Se emiten eventos SSE de evoluciÃ³n al frontend
- El **character sheet se anima** mostrando los diffs (barras de emociÃ³n que suben/bajan, nuevos traits, nuevos topics)
- El usuario ve un **banner "Deshacer"** durante 30 segundos
- El `EvolutionFeed` registra los cambios automÃ¡ticamente

**Rollback (append-only):**
`POST /writers/{id}/identity/rollback` â€” crea una nueva versiÃ³n copiando los campos de la versiÃ³n anterior. Nunca destructivo â€” el historial completo siempre queda.

### Web Search real

El Studio usa `web_search_20250305` (herramienta built-in de Anthropic SDK >= 0.49) durante la fase de research. Cuando Claude decide buscar, la UI muestra un pill `Buscando: ...` y después resume el resultado dentro del pipeline visible del Studio.

### Flujo core hoy

1. Dashboard → elegir writer existente o entrar a **Create Writer**
2. Si crea uno nuevo: `/writers/new` → descripcion libre → preview generado → crear writer
3. Writer Page → chat libre como superficie principal
4. Click en `Studio →`
5. Si hay sesión `active`, aparece la puerta **Retomar sesión / Empezar nueva**
6. Si hay sesión `complete` pero no `active`, el Brief Setup muestra un aviso suave con **Revisar import / Continuar igual**
7. Si no hay nada pendiente, entra directo al Brief Setup
8. Studio: Brief Setup (con header nombre + purpose) → sesión activa (fases + loading tips + tool use) → artefacto
9. Artefacto: copiar / iterar con notas / finalizar sesión
10. Finalizar sesión → import flow separado con propuesta + checkboxes
11. Importar o skipear → volver al Writer Page con feedback claro, la identidad refrescada y la sesión visible en el historial
12. Writer Page: retomar sesiones previas, revisar imports pendientes y navegar la historia de Studio


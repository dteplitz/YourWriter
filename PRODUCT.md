# YourWriter — Estado Funcional del Producto

*Documento vivo. Se actualiza al final de cada sprint con lo que quedó funcional.*
*Última actualización: Sprint 6a ✅ — 2026-03-19*

---

## Qué es el producto

YourWriter es una plataforma donde los usuarios crean escritores IA con personalidad, emociones y objetivos propios. Cada escritor tiene una identidad configurable que moldea cómo escribe. Esa identidad evoluciona de forma autónoma a través del chat — el usuario moldea al writer conversando, y el sistema detecta las señales y propone cambios graduales.

El producto tiene dos espacios conceptuales (ambos construidos desde Sprint 5):
- **Artist Profile** — configurar y gestionar al escritor (WriterPage)
- **Studio** — la sesión de escritura activa (StudioPage)

---

## Modelo de identidad (tres capas)

Definido en Sprint 6a planning. Guía cualquier decisión sobre la identidad del writer:

| Capa | Qué es | Cómo evoluciona | Dónde vive |
|------|--------|----------------|-----------|
| **General stats** | Quién ES el writer | A través del chat — el usuario moldea conversando | `WriterIdentity` (versionado) |
| **Session config** | Cómo encarará ESTA pieza | El usuario particulariza en el Studio (brief, iterations) | Fork del general, no persiste en general |
| **Post-sesión** | Qué queda de la sesión | El usuario decide qué importar al general | Memories o import explícito |

"Escribí esto en tono oscuro" → session config. "Quiero que seas más oscuro" → general stats.

---

## Lo que existe hoy (post-Sprint 6a)

### Autenticación

Los usuarios se registran con email y contraseña y reciben un JWT para las requests siguientes. El login y el registro funcionan. No hay OAuth ni recuperación de contraseña.

### Dashboard — lista de writers

Al ingresar, el usuario ve todos sus writers. Puede crear un writer nuevo (nombre, purpose, descripción de estilo en lenguaje natural) y puede eliminar writers existentes.

La creación genera una identidad inicial con valores por defecto. No hay todavía un flujo guiado de inicialización ("quiero un escritor tipo GRRM").

### Writer Page — Artist Profile

Al seleccionar un writer se abre la página del escritor con **layout vertical scrollable**:

**Zona hero (visible al cargar) — Artist Profile (ConfigPanel)**
Muestra la identidad completa del writer como un character sheet de RPG a ancho completo:
- **Personality traits**: badges con colores por tier (low/medium/high/max)
- **Emotions**: barras de progreso animadas (valores 0–1)
- **Topics/Lifelong objectives**: badges
- **Constraints**: tarjetas individuales

Todo es editable inline con animaciones de diff al guardar. Los cambios persisten versionados (cada edición crea una nueva versión).

**RPG Stats Strip (sticky)**
Al scrollear hacia abajo, el header sticky gana una fila compacta con mini emotion bars y trait chips — permite ver el estado del writer mientras se usa el chat.

**Zona bajo el fold — Chat + Evolution Timeline**
- **ChatPanel**: conversación libre con el writer. Keyword detection determina si responde como chat o activa el pipeline de escritura. El botón **"Studio →"** lleva al Studio.
- **EvolutionFeed**: log de cambios de identidad — cambios manuales y evoluciones automáticas via chat (diferenciados visualmente).

### Studio — sesión de escritura activa

Se accede vía botón "Studio →" desde el ChatPanel. El Studio es una vista completamente separada con su propia ruta (`/studio/:writerId`).

**Flujo dentro del Studio:**

1. **Transición animada** — fade-in que muestra el nombre del writer, sus emociones actuales, constraints y la última pieza escrita. Botón "Entrar" para continuar.

2. **Brief Setup** — el usuario describe en lenguaje libre qué quiere escribir. El sistema genera un brief estructurado (formato, tono, constraints aplicados, word limit). Si el brief necesita aclaración, el sistema pregunta antes de continuar.

3. **Sesión activa** — pipeline de escritura con fases visibles en tiempo real:
   - **Preparando** → pill "Armando estructura..."
   - **Tool use (web search)** → pill "Buscando: [query]"
   - **Drafting** → pill "Primer take..."
   - **Refining** → pill "Mezclando..."
   - Texto streameado en tiempo real durante las fases

4. **Artefacto** — la pieza terminada aparece como un documento (no como burbuja de chat): título generado por el modelo, badge de formato, botón de copiar, botones "Iterar" y "Finalizar sesión".

5. **Loop de iteración** — notas del productor → nuevo take. El textarea de notas permite pedir cambios específicos y relanzar el pipeline sin salir del Studio.

6. **Discografía** — las piezas se acumulan como historial del writer. Expandibles, con fecha relativa en español.

### Identity Evolution via Chat ← Sprint 6a

Cuando el usuario moldea al writer a través del chat — pide enfoques, refuerza rasgos, repite patrones de estilo — el sistema detecta esas señales y propone cambios graduales a la identidad.

**Pipeline de 2 etapas:**
1. **Stage 1 (Detect — Haiku):** Analiza el historial del chat. ¿Esta conversación forma identidad? → `{should_evolve: bool, confidence: float, signal: str}`. Umbral conservador — un solo exchange no triggera, un patrón repetido sí.
2. **Stage 2 (Compute — Sonnet):** Propone cambios incrementales y específicos. Recibe el `signal` del Stage 1 como contexto. Nunca hace rewrites — siempre deltas graduales.

**Flujo completo:**
- La evolución corre inline, después del `{"done": true}` del SSE stream del chat
- Si hay cambios, se persiste una nueva versión de `WriterIdentity` en la DB
- Se emiten eventos SSE de evolución al frontend
- El **character sheet se anima** mostrando los diffs (barras de emoción que suben/bajan, nuevos traits, nuevos topics)
- El usuario ve un **banner "Deshacer"** durante 30 segundos
- El `EvolutionFeed` registra los cambios automáticamente

**Rollback (append-only):**
`POST /writers/{id}/identity/rollback` — crea una nueva versión copiando los campos de la versión anterior. Nunca destructivo — el historial completo siempre queda.

### Web Search real

El Studio usa `web_search_20250305` (herramienta built-in de Anthropic SDK ≥0.49.0). La búsqueda se realiza durante la fase de research antes del outline. Las queries y resultados son visibles en tiempo real via el tool use pill.

---

## Lo que NO existe todavía

| Feature | Sprint |
|---------|--------|
| Session snapshot + import post-sesión | Sprint 6b |
| Writer initialization flow (GRRM-style) | Sprint 6b |
| Alembic migrations | Sprint 5.5 Etapa 3 ⏸ (cuando haya usuarios reales en prod) |
| Memory System (memoria episódica persistente) | Sprint 7 |
| Polish + Agent Visualization | Sprint 8 |

---

## Flujo de usuario actual (end-to-end)

```
1. Usuario entra → pantalla de login
2. Login / Registro → redirige al Dashboard
3. Dashboard → lista de writers del usuario
4. Click "New Writer" → modal: nombre, purpose, estilo
5. Writer creado → aparece en el dashboard
6. Click en el writer → Writer Page
7. Zona hero: ver y editar la identidad del writer (character sheet RPG)
8. Scrollear → ChatPanel + EvolutionFeed
   - Chat libre → respuesta conversacional
   - Pedir escritura por keywords → pipeline con fases
   - Tras la respuesta: pipeline de evolución corre en background
   - Si hay evolución: character sheet se anima, banner "Deshacer" por 30s, EvolutionFeed se actualiza
9. Click "Studio →" → transición animada al Studio
10. Studio: Brief Setup → sesión activa (fases + tool use) → artefacto
11. Artefacto: copiar / iterar con notas / finalizar sesión
12. Discografía: ver todas las piezas del writer
```

---

## Notas de UX conocidas

- La keyword detection en el chat aún puede tener falsos positivos/negativos (mejorada con word boundary regex, pero no es perfecta). El camino largo es eliminarla — el Studio es el lugar correcto para escritura, el chat es para conversar.
- El output de escritura en el CHAT todavía aparece como burbuja (solo en el chat, no en el Studio). Se puede limpiar en una iteración futura.

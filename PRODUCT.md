# YourWriter — Estado Funcional del Producto

*Documento vivo. Se actualiza al final de cada sprint con lo que quedó funcional.*
*Última actualización: Sprint 5.5 ✅ — 2026-03-18*

---

## Qué es el producto

YourWriter es una plataforma donde los usuarios crean escritores IA con personalidad, emociones y objetivos propios. Cada escritor tiene una identidad configurable que moldea cómo escribe. La visión a largo plazo es que esa identidad evolucione sola después de cada sesión de escritura.

El producto tiene dos espacios conceptuales (ambos construidos desde Sprint 5):
- **Artist Profile** — configurar y gestionar al escritor (WriterPage)
- **Studio** — la sesión de escritura activa (StudioPage)

---

## Lo que existe hoy (post-Sprint 5)

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
- **EvolutionFeed**: log de cambios de identidad (por ahora, solo cambios manuales).

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

### Web Search real

El Studio usa `web_search_20250305` (herramienta built-in de Anthropic SDK ≥0.49.0). La búsqueda se realiza durante la fase de research antes del outline. Las queries y resultados son visibles en tiempo real via el tool use pill.

---

## Lo que NO existe todavía

| Feature | Sprint |
|---------|--------|
| Evolución autónoma post-sesión | Sprint 6a |
| Animación del character sheet al evolucionar | Sprint 6a |
| Alembic migrations | Sprint 5.5 Etapa 3 (antes de 6a) |
| Writer initialization flow (GRRM-style) | Sprint 6b |
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
9. Click "Studio →" → transición animada al Studio
10. Studio: Brief Setup → sesión activa (fases + tool use) → artefacto
11. Artefacto: copiar / iterar con notas / finalizar sesión
12. Discografía: ver todas las piezas del writer
```

---

## Notas de UX conocidas

- La keyword detection en el chat aún puede tener falsos positivos/negativos (mejorada con word boundary regex, pero no es perfecta). El camino largo es eliminarla — el Studio es el lugar correcto para escritura, el chat es para conversar.
- El output de escritura en el CHAT todavía aparece como burbuja (solo en el chat, no en el Studio). Se puede limpiar en una iteración futura.

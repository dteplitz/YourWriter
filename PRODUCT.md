# YourWriter — Estado Funcional del Producto

*Documento vivo. Se actualiza al final de cada sprint con lo que quedó funcional.*
*Última actualización: Sprint 4 ✅ — 2026-03-16*

---

## Qué es el producto

YourWriter es una plataforma donde los usuarios crean escritores IA con personalidad, emociones y objetivos propios. Cada escritor tiene una identidad configurable que moldea cómo escribe. La visión a largo plazo es que esa identidad evolucione sola después de cada sesión de escritura.

El producto tiene dos espacios conceptuales (en construcción desde Sprint 5):
- **Artist Profile** — configurar y gestionar al escritor
- **Studio** — la sesión de escritura activa

---

## Lo que existe hoy (post-Sprint 4)

### Autenticación

Los usuarios se registran con email y contraseña y reciben un JWT para las requests siguientes. El login y el registro funcionan. No hay OAuth ni recuperación de contraseña.

### Dashboard — lista de writers

Al ingresar, el usuario ve todos sus writers. Puede crear un writer nuevo (nombre, purpose, descripción de estilo en lenguaje natural) y puede eliminar writers existentes.

La creación genera una identidad inicial con valores por defecto. No hay todavía un flujo guiado de inicialización ("quiero un escritor tipo GRRM").

### Writer Page — la pantalla principal

Al seleccionar un writer se abre una pantalla de tres columnas:

**Columna izquierda — Artist Profile (ConfigPanel)**
Muestra la identidad completa del writer como un character sheet de RPG:
- **Personality traits**: presentados como barras de progreso animadas (valores 0–1)
- **Emotions**: igual que personality, con barras animadas y colores diferenciados
- **Traits/Topics/Lifelong objectives**: badges visuales
- **Constraints**: tarjetas individuales — reglas en lenguaje natural parseadas a config estructurada

Todo es editable inline. Al guardar, los campos que cambiaron muestran una animación de diff (el valor anterior desaparece, el nuevo aparece). Los cambios persisten en base de datos versionados (cada edición crea una nueva versión de la identidad).

**Columna central — ChatPanel**
Interfaz conversacional con el writer seleccionado. Los mensajes se envían por SSE streaming. El writer detecta la intención automáticamente:
- Si el mensaje tiene palabras clave de escritura (write, draft, compose, story, etc.) → activa el pipeline de escritura
- Si no → responde conversacionalmente

Cuando activa el pipeline, el chat muestra las fases en tiempo real: "outlining", "drafting", "refining". El output final aparece como una burbuja de chat más (esto cambia en Sprint 5).

El historial de conversación persiste por writer.

**Columna derecha — EvolutionFeed**
Muestra el log de evolución del writer. Actualmente funciona como historial de cambios manuales (cuando el usuario edita la identidad). La evolución autónoma post-escritura no está implementada todavía.

---

## Lo que NO existe todavía

| Feature | Sprint |
|---------|--------|
| Studio como vista separada | Sprint 5 |
| Transición animada al Studio | Sprint 5 |
| Brief Setup (pre-producción) | Sprint 5 |
| Tool use visible (web search pill) | Sprint 5 |
| Artefacto de escritura como documento | Sprint 5 |
| Loop de iteración (takes + notes) | Sprint 5 |
| Discografía (biblioteca de piezas) | Sprint 5 |
| Web search real (hoy es un stub) | Sprint 5 |
| Evolución autónoma post-sesión | Sprint 6 |
| Writer initialization flow (GRRM-style) | Sprint 6 |
| Animación del character sheet al evolucionar | Sprint 6 |

---

## Flujo de usuario actual (end-to-end)

```
1. Usuario entra → pantalla de login
2. Login / Registro → redirige al Dashboard
3. Dashboard → lista de writers del usuario
4. Click "New Writer" → modal: nombre, purpose, estilo
5. Writer creado → aparece en el dashboard
6. Click en el writer → Writer Page (3 columnas)
7. Columna izquierda: ver y editar la identidad del writer (character sheet)
8. Columna central: chatear con el writer
   - Chat libre → respuesta conversacional
   - Pedir escritura → phases (outlining/drafting/refining) → texto en el chat
9. Columna derecha: ver el log de cambios de la identidad
10. Volver al dashboard → botón "Back"
```

---

## Notas de UX conocidas

- El output de escritura aparece como burbuja de chat — no se diferencia del output conversacional. Esto es el problema central que resuelve Sprint 5.
- No hay feedback claro de cuándo el pipeline terminó vs. cuándo está pensando.
- La detección de intento de escritura es por keywords — puede tener falsos positivos/negativos. Se elimina en Sprint 5 reemplazándola por un botón explícito.
- El ConfigPanel es funcional y visualmente sólido pero vive en la misma pantalla que el chat, sin jerarquía clara de "gestión vs. escritura activa".

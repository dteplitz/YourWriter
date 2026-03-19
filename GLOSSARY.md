# YourWriter — Glosario de producto

*Documento vivo. Se actualiza cuando acordamos nueva terminología o cuando hay ambigüedad que resolver. La fuente del razonamiento está en `LINEAGE.md`.*

---

## Los dos espacios

| Término | Qué es | No confundir con |
|---------|--------|-----------------|
| **Artist Profile** | El espacio de management del writer. Configuración, identidad, historial. El usuario arma la "formación" acá. | El Studio |
| **Studio** | La sesión de grabación activa. Se *entra* con una transición. Tiene inicio y fin. Produce un artefacto. | El chat del Artist Profile |

El Artist Profile y el Studio son dos modos fundamentalmente distintos. Hay una puerta entre ellos. Ver analogía Football Manager en `LINEAGE.md`.

---

## Capas de identidad

El writer tiene tres capas de identidad. No confundirlas es crítico para decisiones de UX y de producto.

### General stats (identidad canónica)

- **Qué es:** Quién ES el writer. Su personalidad, emociones, temas, constraints, objetivos de vida.
- **Dónde vive:** `WriterIdentity` en DB. Versionado, append-only.
- **Cómo evoluciona:** A través del chat en el Artist Profile. El usuario moldea conversando — de forma intencional y explícita.
- **Trigger:** El usuario moldea al writer directamente. "Quiero que seas más oscuro." "Desarrollá el estilo Y." Refuerzo positivo específico sobre un rasgo.
- **No trigger:** Requests de sesión puntual, preguntas técnicas, small talk.

### Session config (identidad de sesión)

- **Qué es:** Cómo va a encarar el writer ESTA pieza. Un fork del general al entrar al Studio.
- **Dónde vive:** En memoria durante la sesión. No persiste en los general stats por defecto.
- **Cómo evoluciona:** El usuario particulariza en el brief o durante la sesión. "Escribí esto en tono oscuro." "¿Y si lo hacés más formal?"
- **Trigger:** Requests de sesión puntual, pedidos de tono/estilo para esta pieza específica, exploración sin validación explícita.
- **Importante:** Los cambios acá no contaminan los general stats. El writer puede producir algo muy diferente a su voz habitual sin "cambiar" como artista.

### Post-sesión (import explícito)

- **Qué es:** Lo que el usuario decide importar de la sesión a los general stats.
- **Cómo funciona:** Al finalizar la sesión, el usuario puede elegir qué se "queda" en el writer.
- **Estado:** Sprint 6b.

---

## Regla de oro para distinguir capas

> **¿El usuario está hablando de esta pieza, o del writer?**
>
> "Escribí esto en tono oscuro" → session config (esta pieza)
> "Quiero que seas más oscuro" → general stats (el writer)

Si hay ambigüedad, la señal más fuerte es el verbo:
- "escribí", "hacé", "en esta pieza", "para esto" → session config
- "quiero que seas", "desarrollá", "seguí siendo", "me gusta que seás" → general stats

---

## Terminología del Studio

| Término | Qué es | No decir |
|---------|--------|---------|
| **Sesión** | El evento activo en el Studio. Tiene inicio y fin. | "chat de escritura" |
| **Brief** | La descripción estructurada de lo que se va a escribir. Surge del Brief Setup. | "prompt de escritura" |
| **Take** | El draft producido por el writer en una iteración. | "respuesta", "output" |
| **Artefacto** | La pieza terminada — el resultado de la sesión. Se presenta como documento. | "resultado", "texto" |
| **Notes** | El feedback del usuario sobre un take. Como el productor musical dando dirección. | "correcciones", "feedback" |
| **Discografía** | El historial de piezas de un writer. Todas las sesiones completadas. | "library", "historial de piezas" (en UI) |

---

## Terminología de evolución

| Término | Qué es |
|---------|--------|
| **Evolution** | Un cambio en los general stats del writer. Se registra como nueva versión en DB. |
| **Evolution trigger** | La señal que dispara el proceso de evolución. Puede ser para general stats o session config. |
| **Rollback** | Volver a la versión N-1 de los general stats. Append-only: crea versión N+1 copiando N-1. |
| **Evolution detect (Stage 1)** | El paso barato (Haiku) que decide SI hay evolución de general stats. |
| **Evolution compute (Stage 2)** | El paso costoso (Sonnet) que decide QUÉ cambia exactamente en los general stats. |
| **Signal** | El output del Stage 1: resumen de por qué el sistema cree que hay evolución. Pasa como contexto al Stage 2. |

---

## Terminología de identidad (campos)

| Campo | Tipo | Qué representa |
|-------|------|---------------|
| `personality` | `dict[str, str]` | Rasgos de carácter. Ej: `{"voice": "lacónico", "tone": "oscuro"}` |
| `emotions` | `dict[str, float]` | Estado emocional actual (0–1). Ej: `{"melancholy": 0.6, "curiosity": 0.4}` |
| `topics` | `list[str]` | Áreas de interés/expertise |
| `constraints` | `dict[str, Any]` | Reglas en plain English parseadas a config estructurada |
| `lifelong_objectives` | `list[str]` | Objetivos de vida del writer como artista |
| `memories` | `list[str]` | Memoria episódica (Sprint 7, hoy no se usa activamente) |

---

## El writer

| Término | Qué es |
|---------|--------|
| **Writer** | El agente IA con personalidad, emociones y objetivos. Tiene identidad configurable. |
| **Artist Profile** | El espacio donde se gestiona el writer (no confundir con el writer en sí). |
| **WriterIdentity** | La entidad DB que almacena una versión de la identidad. Append-only. |
| **EvolutionLog** | El registro de cada cambio individual de identidad. Popula el EvolutionFeed. |

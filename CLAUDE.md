# YourWriter

*El contexto personal, la forma de trabajo y el proceso general viven en `~/.claude/CLAUDE.md`. Este archivo guarda solo lo específico de YourWriter.*

## Dónde Vive Cada Cosa

| Tipo | Archivo |
|------|---------|
| Relación con Damian, forma de colaborar, proceso general, QA, git | `~/.claude/CLAUDE.md` (global) |
| Proceso operativo del proyecto | `PROCESS.md` |
| Estado funcional real | `PRODUCT.md` |
| Estado técnico real | `ARCHITECTURE.md` |
| Decisiones Lang/LangGraph/LangMem | `LANG_PLAYBOOK.md` |
| Diseño / naming / racional | `LINEAGE.md` + `GLOSSARY.md` |
| Patrones de área | `.agents/frontend.md`, `.agents/backend.md` |
| Contexto mínimo de arranque de YourWriter | este archivo |

## Arranque de sesión

**Leer siempre al inicio:**
1. `PRODUCT.md` — estado funcional real
2. Sprint actual: **Sprint 6b** → `SPRINT6B.md`

**Leer según el task:**
- `LANG_PLAYBOOK.md` — decisiones Lang/LangGraph/LangMem
- `ARCHITECTURE.md` — estado técnico detallado
- `LINEAGE.md` + `GLOSSARY.md` — decisiones de diseño/UX/naming

**Diagnóstico al despertar (después de leer):**
- qué entendés con confianza
- qué gaps quedan
- qué código falta leer antes de proponer

Ser honesto y no performativo.

## Qué es YourWriter

YourWriter es una plataforma multiusuario donde los usuarios crean escritores IA con personalidad, emociones y objetivos propios.

Dos espacios canónicos:
- **Artist Profile** — management del writer
- **Studio** — sesión de escritura / grabación

Inspiración de diseño: Football Manager + producción musical. Ver `LINEAGE.md` para el racional completo.

La evolución autónoma via chat ya está construida (Sprint 6a).

## Cómo corre la app

Damian corre la app con `bash dev.sh` desde el root.

Puertos canónicos:
- frontend: 3000
- backend: 8001

Requiere Docker Desktop.

## Repo y docs vivos

- Repo GitHub: `dteplitz/YourWriter`
- Proceso del proyecto: `PROCESS.md`
- Estado funcional: `PRODUCT.md`
- Estado técnico: `ARCHITECTURE.md`
- Patrones de área: `.agents/frontend.md`, `.agents/backend.md`

## Reglas de trabajo específicas

- Seguir `PROCESS.md`
- Si necesitás cambiar shared contracts, avisarle a Damian primero
- Para QA: confirmar siempre puertos/URL; si aparece `Could not validate credentials`, probar logout/login antes de clasificar bug
- Definir shared contracts en `main` antes de paralelizar trabajo que dependa de ellos

Module boundaries:
- `backend/` — FastAPI, servicios, DB
- `frontend/` — React/Vite/TypeScript
- `agents/` — grafos y nodos LangGraph
- `shared/` — tipos/constantes compartidos

## Project Status

Sprints 1–Lang Refresh ✅ — historial en `ARCHITECTURE.md`.

- **Sprint 6b** 🔄 Session entity + Post-sesión import. Slice 0 ✅, Slice 1 ✅, Slice 2 ✅, Slice 3 ✅ (`StateGraph` real + `AsyncPostgresSaver` + resume técnico). Próximo: Slice 4 (sessions UI / retomar).
- **Sprint 6b.5** ⏳ Writer initialization flow conversacional.
- **Sprint 6c** ⏳ LangSmith + evals del evolution pipeline.
- **Sprint 7** ⏳ Memory System con LangMem.

## Mantenimiento de este archivo

- Cap: 5KB
- No guardar “contexto de la última sesión” acá
- Learnings van a memoria/doc vivo correspondiente, no duplicados acá

## Retro / Actualización

- Si cambia el producto visible o la UX, actualizar `PRODUCT.md`
- Si cambia la arquitectura, módulos, endpoints o modelos, actualizar `ARCHITECTURE.md`
- Si cambia el racional de diseño o el lenguaje del producto, actualizar `LINEAGE.md` y/o `GLOSSARY.md`
- Si el aprendizaje es sobre proceso general, QA, git o colaboración, va al `~/.claude/CLAUDE.md` global

# Frontend Agent

## Scope
`frontend/src/` — React components, pages, stores, API client, styles

## Context (read before starting)
- `frontend/src/types/` — shared TypeScript types
- `frontend/src/api/client.ts` — API client (use existing functions, don't add new fetch calls)
- `frontend/src/index.css` — design system variables and base styles
- `frontend/src/config-panel.css` — character sheet styles (EmotionBar, TraitBadge, ConstraintCard)
- `frontend/src/components/` — existing components, follow their patterns

## Stack
React 19, Vite, TypeScript, Zustand, react-router-dom. No animation libraries — pure CSS + React state.

## Design System (index.css variables)
```
--bg-primary: #0f0f13    --bg-secondary: #1a1a24   --bg-tertiary: #24243a
--bg-card: #1e1e2e       --bg-input: #2a2a3e       --bg-hover: #2e2e44
--text-primary: #e4e4ef  --text-secondary: #a0a0b8  --text-muted: #6c6c88
--accent: #7c6ff7        --accent-hover: #6b5ce6    --accent-subtle: rgba(124,111,247,0.15)
--danger: #e05555        --success: #4ade80         --warning: #facc15
--border: #2e2e44        --border-light: #3a3a54
--radius: 8px            --radius-lg: 12px
--font-sans: Inter       --font-mono: JetBrains Mono
```

## CSS Layout Patterns
- Layouts de altura fija: `min-height: 0` en **toda** la cadena de flex children — si falta uno, rompe todo
- Columnas con scroll independiente: `overflow-y: auto` + `min-height: 0` en el grid/flex item
- Headers sticky en paneles: `position: sticky; top: 0; background: <color>; z-index: 1`
- Responsive en grid: agregar `width: 100%; min-width: 0` a los items en el media query
- Fixes de layout CSS: **un cambio a la vez**, verificar antes del siguiente

## TypeScript Patterns
- Al comparar Records con tipos mixtos (number/string/boolean): normalizar ambos lados con `Object.entries(rec).sort().map(([k,v]) => [k, String(v)])`
- Los fixtures de tests deben usar los mismos tipos que el dominio real
- Functional components, typed props siempre

## CSS Import Paths — CRÍTICO
Los CSS imports son **siempre relativos a `src/`**, no al directorio del componente:
- Desde `src/pages/`: `import '../writing.css'`
- Desde `src/components/`: `import '../session.css'`
- NUNCA `import './session.css'` desde un componente — no existe esa ruta

## Component Conventions
- CSS de componentes de área en archivos separados (`config-panel.css`, `writing.css`, `session.css`)
- Animaciones: CSS keyframes + React state (no framer-motion)
- Estado global: Zustand stores en `frontend/src/stores/`
- No crear nuevas funciones fetch — usar `frontend/src/api/client.ts`

## Worktree Permissions — CRÍTICO
Si estás corriendo en un worktree (git worktree), el `.claude/settings.json` no se hereda automáticamente. Sin ese archivo, no podés ejecutar comandos Bash (git, npm). Si no podés correr comandos, crea `.claude/settings.json` en la raíz del worktree con el contenido de `.claude/settings.json` del repo principal.

## Git / Process
- Trabajar en feature branch, nunca commitear directo a `main`
- Branch naming: `feature/<area>-<description>`
- Un cambio lógico por commit, mensaje imperativo
- Correr `npx tsc --noEmit` antes de commitear

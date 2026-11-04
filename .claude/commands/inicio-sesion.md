---
description: Abre la sesión de trabajo, crea su rama desde main y su archivo en .worklog/.
argument-hint: <objetivo de la sesión>
---

# /inicio-sesion

Objetivo: **$ARGUMENTS** (si viene vacío, pregunta: "¿Cuál es el objetivo de esta sesión?").

1. **Revisa lo abierto.** Corre `git status`, `git branch --no-merged main` y `gh pr list --state open`. Si hay ramas o PR sin integrar, muéstralos y propón resolverlos antes de empezar.
2. **Carga el contexto.** Resume la última sesión de `.worklog/sesiones/` y los ítems de `docs/BACKLOG.md` relacionados con el objetivo.
3. **Crea la rama** desde `main` al día:
   `git switch main && git pull --ff-only && git switch -c <tipo>/<tema>`, con `<tipo>` = `feat`, `fix`, `docs`, `refactor`, `chore` o `test` (GitHub Flow, ver `AGENTS.md`).
   Si `git merge-base main HEAD` no devuelve nada, detente y avisa: la rama no comparte historia con `main`.
4. **Crea** `.worklog/sesiones/AAAA-MM-DD_tema-en-kebab-case.md` con esta plantilla:

```markdown
# Sesión: AAAA-MM-DD — Tema

## Contexto
- **Objetivo:** <qué queremos lograr>
- **Quién:** <nombre (usuario de GitHub)>
- **Rama:** <tipo>/<tema>
- **Continuación de:** <sesión anterior, si aplica>
- **Repo hermano:** <si la sesión también toca emsa-sgff-frontend, enlaza su archivo de sesión>

## Registro

### HH:MM — Actividad
- **Decisión:** <qué se decidió>, por <quién>: <razón y alternativas consideradas>
- **Hallazgo:** <qué se encontró> (fuente: <commit, PR, comando o prueba>)
- **[inferido]** <lo que no se pudo comprobar> → preguntar a <quién>

## Resumen
- **Logros:**
- **Bloqueos:**
- **Para retomar:**
```

5. **Propón un plan corto** (2 a 5 pasos) y recuerda cerrar con `/cierre-sesion` en esta misma rama.

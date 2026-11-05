# Sesión: 2026-11-05 — `users.json`

## Contexto
- **Objetivo:** que la falta de `users.json` no se convierta en un 500 silencioso. Hoy `/auth/login` y `/auth/users` fallan sin mensaje claro. Agregar un archivo de ejemplo y sacar `users.json` de git (backlog, ítem 2).
- **Quién:** Aldo Saavedra Reyes (`baxtercl`), con Claude Code.
- **Rama:** `fix/users-json`
- **Continuación de:** [2026-11-04_dogfooding-main.md](2026-11-04_dogfooding-main.md)
- **Repo hermano:** [emsa-sgff-frontend/.worklog/sesiones/2026-11-05_usuarios-y-tablas-colapsables.md](https://github.com/stonks-lab/emsa-sgff-frontend/blob/main/.worklog/sesiones/2026-11-05_usuarios-y-tablas-colapsables.md)

## Registro

### 11:41 — Inicio
- **Hallazgo:** repo limpio en `main` (`05237b4`), sin PR abiertos (fuente: `git status`, `gh pr list`).

### 11:42 — Cambios
- **Decisión:** por Claude, con el objetivo de Aldo: responder 503 y no crear un `users.json` por defecto, para no dejar credenciales conocidas en un servidor. El README explica cómo crear el primer `admin` con `getpass`, sin que la contraseña quede en pantalla ni en el historial.
- **Hallazgo:** el stack local no usa `--reload`, así que hubo que reiniciarlo (`down.sh --keep-image` + `up.sh`) para probar el cambio.
- **Hallazgo:** contra el stack local, login con clave mala → 401; sin `users.json` → 503 con el mensaje; con el archivo restaurado → 200. El comando del README genera un JSON válido (1 usuario, hash de 64 caracteres). Con el `.gitignore` nuevo, el `users.json` local ya no aparece en `git status` (fuente: `curl` y `git status`).

## Resumen
- **Logros:** la falta de `users.json` deja de ser un 500 silencioso. Además, el archivo no se puede commitear por error y hay instrucciones para crearlo.
- **Bloqueos:** ninguno.
- **Para retomar:** en el equipo de José, restaurar o crear `users.json` siguiendo el README. Backlog ítem 2: usuarios en la base, contraseñas con bcrypt o argon2 y `JWT_SECRET` obligatorio.

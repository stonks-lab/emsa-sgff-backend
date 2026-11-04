# Sesión: 2026-11-04 — Dogfooding de `main`

## Contexto
- **Objetivo:** probar `main` del backend con el frontend antes de pedirle a José que ajuste sus copias locales al renombre de los repos.
- **Quién:** Aldo Saavedra Reyes (`baxtercl`), con Claude Code.
- **Rama:** `docs/worklog-dogfooding-main`
- **Continuación de:** [2026-11-04_renombre-stack-local-e-integracion.md](2026-11-04_renombre-stack-local-e-integracion.md)
- **Repo hermano:** el detalle completo, incluidos el PR #6 de José y su migración, está en [emsa-sgff-frontend/.worklog/sesiones/2026-11-04_dogfooding-main-y-pr-6.md](https://github.com/stonks-lab/emsa-sgff-frontend/blob/main/.worklog/sesiones/2026-11-04_dogfooding-main-y-pr-6.md)

## Registro

### 15:01 — Smoke de la API
- **Hallazgo:** con el stack local (`sgff/local/up.sh`) sobre `main` (`7c0a6b9`), los **77 endpoints** que llama el frontend responden 200, igual que en la corrida anterior (fuente: `local/run/smoke-dogfood.txt` vs `smoke-final.txt`).

### 15:05 — Dogfooding con el frontend
- **Hallazgo:** en las 22 pantallas el log del backend no tiene ningún 5xx. Los únicos 4xx son 2 × 401 de `/auth/me` antes del login y 3 × 403 de `/auth/users` en la prueba de roles, todos esperados (fuente: `grep` en `local/run/backend.log`).
- **Hallazgo:** `POST /simulacion/guardar`, `GET /simulacion/{id}` y `DELETE /simulacion/{id}` funcionan contra SQL Server.
- **Hallazgo:** con tokens de `dab`, `dpo` y `estrategico`, solo `/auth/users` responde 403; el resto de los endpoints de datos responde 200. Ya está en `docs/BACKLOG.md` (autenticación): no es nuevo.
- **Hallazgo:** con el `.env` real, los endpoints `/monday/*` traen datos reales de Monday también en local.

### ~15:15 — Migración de José
- **Decisión:** por Aldo, pedirle a José que **no** renombre ni mueva carpetas: `run_servicio.bat` usa `C:\Dev\Tablero-integrado\tablero-web\backend` y la tarea `TableroDabDpo` depende de esa ruta.
- **[inferido]** el Claude Code de José informó que su backend está en `tablero-web/`, no en `tablero-web\backend` como dice `run_servicio.bat`. El script podría estar desactualizado o el servicio no correr en ese equipo → preguntar a José.

## Resumen
- **Logros:** `main` del backend verificado con el frontend: 77/77 endpoints, sin errores 5xx.
- **Bloqueos:** ninguno.
- **Para retomar:** autenticación por rol en el backend (backlog). Confirmar con José la ruta real de su servicio y si quedó funcionando después del pull.

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

### ~16:30 — El backend de José corría código viejo
- **Hallazgo:** con el código en disco en `7c0a6b9`, su backend respondía 404 en 13 rutas, exactamente las que están en `main` y no en `2e76ab2` (fuente: reporte de José; comparación de los `@router` con `git show`). `/proyecciones/tabla` y `/comparacion` daban 500: es el bug conocido de `2e76ab2` (ítem 1 del backlog, corregido por el PR #4), no pandas 3 (aquí responden 200 con pandas 3.1.0).
- **Hallazgo:** Aldo detectó cambios en staging en el clon de José, los guardó en un stash (WIP) e hizo `git pull origin main`. Desde entonces las pantallas funcionan (fuente: Aldo). El stash queda en el equipo de José sin revisar.
- **[inferido]** (error propio: lo presenté como causa) `run_servicio.bat` arranca en `tablero-web\backend\`, una subcarpeta ignorada por git (`.gitignore:53`), y el clon de José está en `tablero-web\`. Confirmar con José desde qué carpeta corre la tarea `TableroDabDpo`. Se anotó en el backlog, ítem 6.

### ~17:50 — `users.json` faltante
- **Hallazgo:** su reporte decía que no hay `users.json` en la raíz del backend. `/auth/login` y `/auth/users` lo leen en cada llamada (`app/routers/auth.py`): la pantalla Usuarios muestra "0 usuarios" y nadie podrá iniciar sesión cuando venza el token. **[inferido]** responde 500 → confirmar en F12 (José). Se anotó en el backlog, ítem 2.

## Resumen
- **Logros:** `main` del backend verificado con el frontend: 77/77 endpoints, sin errores 5xx. El equipo de José quedó corriendo `main`.
- **Bloqueos:** `users.json` faltante en el equipo de José.
- **Para retomar:**
  - José: restaurar `users.json`, revisar el stash y confirmar la carpeta de `TableroDabDpo`.
  - Backlog: autenticación por rol (1b), seguridad de `auth.py` (2) y rutas fijas (6).

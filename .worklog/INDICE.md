# Índice de sesiones de trabajo

Una fila por sesión; la agrega `/cierre-sesion`. El detalle está en `sesiones/AAAA-MM-DD_tema.md` y el protocolo en [`.claude/rules/sesiones.md`](../.claude/rules/sesiones.md).

## 2026

### Noviembre

| Fecha | Tema | Ubicación clave | Estado |
|---|---|---|---|
| [11-04](sesiones/2026-11-04_renombre-stack-local-e-integracion.md) | Renombre `dabdpo-backend` → `emsa-sgff-backend`, README, backlog y `.env.example`. Stack local desechable (SQL Server en Docker, fuera del repo). Integración de `master`/`feat` en `main` con merge real, más la recuperación de lo que se perdía de `main`: 77 de 77 endpoints. Creación del worklog | `README.md`, `docs/BACKLOG.md`, `.env.example`, `app/routers/proyecciones.py`, `.worklog/` | 🔄 PR #4 espera la revisión de José |
| [11-04](sesiones/2026-11-04_dogfooding-main.md) | Dogfooding de `main` con el frontend antes de la migración de José: 77/77 endpoints, sin 5xx, simulación y login por rol verificados. Seguimiento del equipo de José: su backend corría código anterior a la integración (13 rutas 404, 500 de `2e76ab2`), resuelto con stash + pull; falta `users.json`. Detalle y PR #6 en la sesión hermana del frontend | `.worklog/`, `docs/BACKLOG.md`, `AGENTS.md` | ✅ |
| [11-05](sesiones/2026-11-05_users-json.md) | 503 con mensaje claro si falta `users.json`. Después, por decisión de Aldo, `users.json` versionado con 4 usuarios de prueba | `.gitignore`, `app/routers/auth.py`, `README.md`, `docs/BACKLOG.md` | ✅ |

## Antes del worklog

| Período | Qué | Fuente |
|---|---|---|
| 2026-09-30 a 2026-11-03 | Desarrollo inicial en `main` y, desde el 21-oct, en `master`/`feat`, con historias separadas | [HISTORIAL-RECONSTRUIDO.md](HISTORIAL-RECONSTRUIDO.md): solo git, con hechos e inferencias marcados |

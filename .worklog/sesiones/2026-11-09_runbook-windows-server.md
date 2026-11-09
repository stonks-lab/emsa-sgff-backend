# Sesión: 2026-11-09 — Primer despliegue en Windows Server y runbook versionado

## Contexto
- **Objetivo:** dejar operativo el SGFF en el Windows Server de producción y versionar el runbook en `docs/`.
- **Quién:** Aldo Saavedra (ejecutó en el servidor), con Claude Code (diagnóstico, runbook y cambios).
- **Rama:** `docs/runbook-windows-server`
- **Continuación de:** [2026-11-05_users-json.md](2026-11-05_users-json.md)
- **Repo hermano:** [`emsa-sgff-frontend/.worklog/sesiones/2026-11-09_subruta-sgff.md`](https://github.com/stonks-lab/emsa-sgff-frontend/blob/feat/subruta-sgff/.worklog/sesiones/2026-11-09_subruta-sgff.md)

## Registro

### Mañana — Diagnóstico del runbook v1 (ejecutado el 5 y 9-nov)
- **Hallazgo:** `npm run build` falla en el servidor con 32 errores de `tsc`. Se reprodujo en el Mac con el mismo commit del frontend (`f1b1772`): es deuda del repo, no del servidor (fuente: log del servidor y `npx tsc -b` local). `npx vite build` sí compila (fuente: build local).
- **Hallazgo:** el SQL principal responde 18456 con el `.env` escrito a mano el 5-nov, mientras que el BI, en el mismo servidor y con otro usuario, conecta (fuente: log del servidor). Causa sin confirmar: lo más probable es la clave del `.env` → **[inferido]**, confirmar con Aldo si la nueva prueba del Paso 6.1 pasó con una clave distinta.
- **Hallazgo:** la app no usa el driver ODBC antiguo `SQL Server`, como decía la v1: usa `SQL Server Native Client RDA 11.0`, el último en orden alfabético (fuente: `pyodbc.drivers()` en el servidor y `app/data/sql_server.py`). Registrado en el backlog, ítem 7.
- **Hallazgo:** la tarea con la cuenta local `svc_sgff` no levantó y no dejó rastro: el resultado de la tarea no se imprimió por el formato de PowerShell 5.1 al pegar varios comandos juntos (fuente: log del servidor). Causa no comprobada → **[inferido]**: derecho "Log on as a batch job" bloqueado por GPO.
- **Hallazgo:** `README.md` y el backlog decían que el build se busca en `../frontend/dist`. En realidad es `frontend/dist` dentro del repo (fuente: `app/main.py:41`). Corregido.

### Mañana — Runbook v2, ejecutado del Paso 1 al 12 por Aldo con éxito
- **Decisión:** la tarea corre como LOCAL SERVICE, envuelta en `cmd /c ... >> sgff-consola.log 2>&1`, por Claude y aceptada por Aldo. No necesita clave ni el derecho de inicio de sesión por lotes, y los errores de arranque quedan en un archivo. Alternativas: seguir con `svc_sgff` (clave que guardar y GPO) o una cuenta de dominio (solo necesaria con `SQL_AUTH=windows`).
- **Decisión:** el build usa `npx vite build`, por Claude y aceptada por Aldo. Un despliegue no debe caerse por errores de tipos. Alternativa: corregir los 32 errores antes, lo que bloqueaba el despliegue.
- **Decisión:** el Paso 6.1 prueba cada usuario SQL contra el servidor antes de escribir el `.env` y distingue tres casos: clave incorrecta, clave con `; { }` o falta de acceso a la base.
- **Decisión:** todos los pasos se pueden repetir, para retomar una instalación a medias sin deshacer nada.

### 10:40 — Sub-ruta `/sgff` y runbook en `docs/`
- **Decisión:** publicar en `http://<servidor>/sgff`, como aplicación del Default Web Site, y no en el puerto 8080, por Aldo: en el servidor conviven otras apps, cada una en `/<nombre-de-la-app>`. Requiere cambios en el frontend (PR hermano); el backend no cambia porque IIS quita el prefijo. Probado con un proxy que imita esa regla (fuente: sesión del frontend).
- **Decisión:** retirar `svc_sgff`, por Claude a pedido de Aldo. Con LOCAL SERVICE ya no se usa, y una cuenta local con clave que nadie usa es superficie de ataque. Queda en el runbook como Paso 10.3, que no hace nada si la cuenta no existe y se niega si la tarea aún la usa. Alternativa descartada: conservarla de respaldo.
- **Decisión:** versionar el runbook en `docs/RUNBOOK-WINDOWS-SERVER.md`, pedido por Aldo. **Hallazgo:** los dos repos son públicos (fuente: `gh repo view --json visibility`), así que el runbook no trae el nombre del servidor, usuarios ni claves: dice `<servidor>`. El historial de esta migración va en este worklog, no en el runbook.
- **Hallazgo:** con el SGFF ya publicado, la API sin token (ítem 1b) queda expuesta en la red interna. Se dejó recomendado restringir por IP en IIS.

### 11:02 — Aprobación y merge
- **Decisión:** Aldo Saavedra aprueba el PR y pide mergearlo. Es una **excepción** a la regla de `AGENTS.md` ("nunca de quien lo abrió"): el PR lo abrió su propia cuenta y GitHub no permite que el autor se apruebe a sí mismo. La aprobación queda en un comentario del PR. Decide Aldo, que es quien define estas reglas. Motivo: desbloquear el despliegue del servidor.

### 11:50 — Migración a `/sgff` en el servidor
- **Hallazgo:** Aldo ejecutó en el servidor los Pasos 1, 4, 7, 10.3, 11 y 12 del runbook, más el reinicio de la tarea, y el SGFF funciona en `http://<servidor>/sgff` (fuente: Aldo, en la sesión). Claude no vio la salida de esos pasos.
- **Error propio (Claude):** en las instrucciones de la migración, el reinicio de la tarea quedó como punto 4, después del Paso 12. Tenía que ir justo después del Paso 7: el backend solo revisa `dist` al arrancar, y la tarea ya corría con el build anterior. El runbook no necesita cambios: en una instalación nueva, la tarea arranca en el Paso 10, después del build, y el Paso 14 reinicia en cada actualización. Fue propio de esta migración.

## Resumen
- **Logros:** SGFF en producción en `http://<servidor>/sgff`, como aplicación del Default Web Site, con la tarea como LOCAL SERVICE. Se retiraron `svc_sgff`, el sitio del puerto 8080 y su regla de firewall. Runbook versionado en `docs/RUNBOOK-WINDOWS-SERVER.md` (PR #7). Backlog actualizado.
- **Bloqueos:** ninguno.
- **Para retomar:**
  - **Restringir por IP la aplicación `/sgff` en IIS** mientras la API no exija token (backlog, ítem 1b). Es lo más urgente: hoy cualquiera en la red interna puede leer y cargar datos por `/sgff/api/*`.
  - Confirmar el **[inferido]** sobre la clave del SQL principal → Aldo.
  - Confirmar que se hizo la prueba de reinicio del servidor del Paso 12 → Aldo.
  - Apagar el SGFF del equipo de José (tarea `TableroDabDpo`), para no tener dos versiones en uso.
  - ETL: sigue sin activarse hasta decidir la carga AdC (ítem 1a).

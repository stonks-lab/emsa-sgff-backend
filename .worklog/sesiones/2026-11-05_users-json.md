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

### 12:00 — Publicación sin PR
- **Decisión:** por Aldo, subir los commits directo a `main` como hotfix, sin PR. Excepción explícita a la regla de `AGENTS.md` ("todo cambio entra por PR") para que José reciba los arreglos de inmediato. Se publicó con fast-forward, que conserva los commits atómicos.
- **Hallazgo:** el `users.json` que compartió José (1 usuario, `admin`) funciona con este backend: login 200, `/auth/users` 200 con 1 usuario y clave incorrecta 401 (fuente: `curl` contra el stack local, con su archivo puesto temporalmente).

### 12:07 — `users.json` versionado
- **Decisión:** por Aldo, versionar `users.json` con los 4 usuarios de prueba del stack local (`admin`, `dab`, `dpo` y `estrategico`, clave `sgff-local`) y subirlo directo a `main`. Revierte el `.gitignore` de la mañana. El foco de la sesión es que José vea lo mismo, no la seguridad. Se sacó también de `.git/info/exclude` en el equipo de Aldo.
- **Hallazgo:** el archivo versionado es idéntico al que genera `local/seed/seed.py`, así que `up.sh` no deja cambios en el repo (fuente: `git status` después de commitear).
- **Ojo para José:** si tiene un `users.json` sin versionar en la raíz, `git pull` se detiene ("untracked working tree files would be overwritten"). Debe moverlo o renombrarlo antes del pull.

### 12:22 — Respaldo real de la base DAB
- **Hallazgo:** José compartió un respaldo SQL de la base `DAB` (`backup_DAB_20261105_114556.sql`, 281 MB, 22 tablas, sin vistas ni `BI_dev`). Se montó solo en el SQL Server local de Docker. La primera carga falló porque las fechas traen 6 decimales en los segundos y `DATETIME` acepta 3; se recortaron en una copia y quedó con 0 errores y las filas iguales a los INSERT del archivo (fuente: `sqlcmd` y conteo por tabla).
- **Decisión:** por Aldo, corregir el código donde no calce con la base real.
- **Hallazgo:** con el backend apuntando a `DAB`, el smoke da 76/77 respuestas 200 (el 404 es `/simulacion/1`: `Simulacion` está vacía). Un registro de consultas fallidas (fuera del repo) solo marcó `dbo.dim_inf_proyecto`, que no existe en la base real y ya tiene respaldo en `dim_proyectos` (fuente: `local/run/smoke-dab.txt`, `sqlspy.jsonl`).
- **Hallazgo:** las columnas de SIC, `registro_incidencias` (se renombran por posición y el orden calza) y proyecciones coinciden con lo que usa el código. Las diferencias estaban en el seed local, que tenía columnas inventadas.
- **Hallazgo:** el código leía `dbo.SIC_ContratosItemizado`, y la tabla real es `SIC_ContratosItemizados`. Se corrigió en `3beb8da`; `load_itemizado()` ahora lee 16.634 filas. No afectaba pantallas, porque ningún endpoint la usa.
- **Hallazgo:** el ítem 1a del backlog estaba equivocado. La base real tiene 68 filas AdC de la carga del 8-oct: `/proyecciones/comparacion` devuelve 29 filas y `total_adc` es 16.050 MM CLP. La próxima carga las borraría. Se corrigió en `deeb97e`.
- **Decisión:** por Aldo, push directo a `main`.

### 15:25–12:55 — Actualización del equipo de José y reglas de trabajo
- **Hallazgo:** en el frontend de José, `npm ci` falló con `EPERM` sobre `rolldown-binding.win32-x64-msvc.node`, y también estaban bloqueados `lightningcss` y `tailwindcss-oxide`: un Vite seguía corriendo. Como `npm ci` borró `node_modules` a medias, `vite` dejó de reconocerse. Se resolvió liberando el bloqueo, borrando `node_modules` y `dist`, y corriendo `npm ci` + `npx vite build` (fuente: salidas que compartió Aldo).
- **Hallazgo:** el `git pull` del backend se detuvo por su `users.json` sin versionar. Se renombró a `users.local-backup.json` y el pull funcionó (fuente: Aldo).
- **Hallazgo (corrección de Aldo):** la carpeta paraguas de José es `C:\Dev\Tablero-integrado\tablero-web\`, con `backend\` y `frontend\` como repos hermanos. No es el frontend dentro del backend, como se había supuesto. **[inferido]** con esa estructura, `app/main.py` busca el build en `backend\frontend\dist` y no lo encuentra, así que `http://localhost:8000` no serviría la interfaz → preguntar a José.
- **Decisión:** por Aldo, todo PR debe aprobarlo otra persona del equipo, nunca quien lo abrió, y recién entonces el autor mergea. Se agregó a `AGENTS.md` y `CLAUDE.md` de los dos repos (`f916fd5`, push directo a `main`).
- **Decisión:** por Aldo, armar un `CLAUDE.md` + `AGENTS.md` para la carpeta paraguas de José, con una rutina obligatoria al iniciar cada sesión: pull de `main`, conflictos resueltos con confirmación, borrar las ramas mergeadas y alertar sobre las no mergeadas. También GitHub Flow, Conventional Commits, commits atómicos y corregir los documentos que no calcen con la realidad. Se entregaron como archivos fuera de los repos.

## Resumen
- **Logros:** la falta de `users.json` responde 503 con un mensaje claro, y `users.json` quedó versionado con los usuarios de prueba. El código se revisó contra el respaldo real de `DAB`: se corrigió el nombre de `SIC_ContratosItemizados` y el backlog de AdC. La regla de aprobación por otra persona quedó escrita. José quedó actualizado con `main`.
- **Bloqueos:** ninguno.
- **Para retomar:**
  - Confirmar con José si `http://localhost:8000` sirve la interfaz con los repos hermanos (backlog, ítem 6, y backlog del frontend, ítem 5).
  - Decidir la carga AdC antes de la próxima carga de proyecciones (1a).
  - `dim_inf_proyecto` no existe en `DAB` → preguntar a José si existe en otra base o si se elimina del código.

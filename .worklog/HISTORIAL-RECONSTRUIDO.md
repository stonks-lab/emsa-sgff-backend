# Historial reconstruido: 30-sep a 3-nov de 2026

Antes del 4-nov este repo no tenía worklog. Esta página reconstruye ese período **solo desde git y GitHub**: commits, fechas, autores y contenido de los archivos. Para el *por qué* de cada cambio la única fuente son los mensajes de commit. Lo que no dicen está marcado como inferencia o pregunta abierta.

Reconstruido el 2026-11-04 por Aldo Saavedra, durante la sesión [2026-11-04](sesiones/2026-11-04_renombre-stack-local-e-integracion.md).

## Cómo leer las etiquetas

| Etiqueta | Significa | Cómo comprobarlo |
|---|---|---|
| **[git]** | Dato verificable en el repo | El comando indicado o `git show <hash>` |
| **[mensaje]** | Lo dice el mensaje del commit, escrito por su autor | `git log -1 <hash>` |
| **[inferido]** | Interpretación de los datos, sin confirmar | Preguntar a José (ver al final) |

## Línea de tiempo

Fuente: `git log --all --reverse --date=format:'%Y-%m-%d %H:%M' --format='%h|%ad|%an|%s'`. Horas en hora de Chile.

| Fecha | Commit | Rama | Identidad git | Qué dice el mensaje |
|---|---|---|---|---|
| 09-30 17:33 | `f36f740` | `main` | `riffocardenas-bit` | Backend inicial |
| 10-05 18:13 | `59dce4b` | `main` | `riffocardenas-bit` | Nuevos módulos y timeline de saldo por contrato |
| 10-06 17:55 | `74d8a2a` | `main` | `riffocardenas-bit` | Timeline de saldo con `ultimo_ep`; timeline P&C desde `SIC_EPs` |
| 10-08 18:15 | `c2f24be` | `main` | `riffocardenas-bit` | Fix cobertura-metros; además agrega `/proyecciones/comparacion` y filtros `proyecto`/`periodo_hasta` **[git]** |
| 10-13 18:54 | `168a78e` | `main` | `riffocardenas-bit` | Procesos de licitación desde Monday, fix `saldo_timeline` |
| 10-14 13:07 | `e96854d` | `main` | `riffocardenas-bit` | Endpoint `/estado-proyectos/saldo-timeline` por proyecto; elimina `/upload/proyecciones-adc` duplicado |
| 10-19 12:48 | `f500ec7` | `main` | `riffocardenas-bit` | Reclasificación de estados SOLPE |
| 10-19 18:01 | `cd59c66` | `main` | `riffocardenas-bit` | Tipo Servicio y `fin_estimado`; "Simplificada get_proyecciones: removidos parámetros proyecto/periodo_hasta y lógica monto_usd"; "Removidos _transform_adc, load_proyecciones_adc…" **[mensaje]** |
| 10-21 17:37 | `2d1633c` | `master` | `stonks-lab` | "Initial commit: FastAPI backend DAB-DPO", sin padre **[git]** |
| 10-26 18:02 | `c06c526` | `master` | `stonks-lab` | Dashboard DAB |
| 10-27 12:44 | `39b0ab3` | `master` | `stonks-lab` | Selector de versión PAI (metros lee `etl/d2.parquet`) |
| 10-29 13:22 | `d34646c` | `master` | `stonks-lab` | Proveedor en EPs, curva S, tendencia razones Monday |
| 10-29 18:18 | `7b9d561` | `master` | `stonks-lab` | Módulo KPI Contratos, rediseño Alertas |
| 11-02 17:05 | `fc536ab` | `feat/simulacion-improvements` | `stonks-lab` | Simulación: filtro vigentes SIC, saldo P&C en duplas |
| 11-03 18:11 | `2e76ab2` | `main` | `riffocardenas-bit` | Presupuesto Perforación (metros por SQL `Proyecciones_P&C`), curva S financiera, **auth JWT** |

## Hechos verificados

1. **Dos historias sin relación.** El repo tiene dos commits raíz: `f36f740` (30-sep) y `2d1633c` (21-oct) **[git]** (`git rev-list --max-parents=0 --all`). `master` y `feat/simulacion-improvements` salen del segundo y `main` del primero. Desde el 21-oct, `main` solo recibió `2e76ab2` (3-nov).
2. **Dos identidades, un correo.** `riffocardenas-bit` y `stonks-lab` firman con el mismo correo **[git]** (`git log --all --format='%an <%ae>' | sort -u`). La segunda aparece el 21-oct.
3. **Commits pareados con el frontend.** 13 de estos 15 commits tienen un par en `emsa-sgff-frontend` con la misma fecha y hora (±1 minuto), por ejemplo 21-oct 17:37 y 29-oct 18:18 **[git]**. Las excepciones son `c2f24be` (8-oct) y `2e76ab2` (3-nov 18:11). La parte de frontend de la auth JWT (`f37ed1f`, 3-nov 13:17) se hizo con `stonks-lab` en `feat/simulacion-improvements`. En el frontend no hubo historia nueva: `fc10393` (21-oct, `stonks-lab`) tiene como padre al último commit de `main` y siguió en `main`.
4. **Edad de cada archivo en el "Initial commit" de `master`.** Comparé el contenido de cada archivo de `2d1633c` con todas las versiones de `main` **[git]**:
   - Coinciden con `main` al 19-oct (`cd59c66`): `sql_server.py`, `metros.py`, `calculations.py` (con `saldo_timeline_por_proyecto()`), `main.py`.
   - `proyecciones.py` coincide solo con `74d8a2a` (6-oct): no tiene `/comparacion` ni los filtros de `c2f24be`.
   - `estado_proyectos.py` coincide con `59dce4b`…`168a78e`: no tiene la ruta `/saldo-timeline` de `e96854d`, aunque la función que usa sí está.
   - `loader.py`, `licitaciones.py` y `monday.py` no coinciden con ninguna versión de `main`: traen trabajo nuevo.
5. **`main` roto desde el 19-oct.** `cd59c66` quitó `proyecto` y `periodo_hasta` de `get_proyecciones()`, pero `proyecciones.py` en `main` los sigue pasando. `/proyecciones/tabla` y `/comparacion` dan 500 **[git]** (código) y lo confirma la prueba local del 4-nov.
6. **Desde el 19-oct no hay carga AdC.** `cd59c66` eliminó el cargador AdC **[mensaje]**. Todas las cargas actuales vacían `dbo.proyecciones` (`TRUNCATE`) e insertan solo P&C **[git]**: `load_proyecciones_pyc()`, la tarea `etl/auto_reload_proyecciones.py` y el ETL de Power BI en modo `full`, que es el que trae por defecto `etl/config_etl.example.py`.
7. **Despliegue en Windows.** Los scripts de `master` apuntan a `C:\Dev\Tablero-integrado\tablero-web\` (`etl/schedule_etl.ps1`, `run_servicio.bat`) **[git]**.
8. **El frontend nunca dejó de usar lo que `master` no tiene.** `AnalisisProyecto.tsx` (llama a `/saldo-timeline`) no se toca desde el 14-oct y `Proyecciones.tsx` (llama a `/comparacion` y a los filtros) desde el 13-oct **[git]** (repo del frontend).

## Inferencias (sin confirmar)

- **[inferido]** El 21-oct el trabajo pasó a otro entorno, probablemente el equipo Windows de `C:\Dev\Tablero-integrado`, con otra configuración de git (`stonks-lab`). Lo sugieren los hechos 2, 3 y 7.
- **[inferido]** En ese entorno el backend no era un clon del repo. Se habría hecho `git init`, cuya rama por defecto se llama `master`, y se subió como historia nueva. El frontend, en cambio, sí era un clon y siguió en `main`. Lo sugieren los hechos 1 y 3 y el nombre de la rama.
- **[inferido]** `2e76ab2` (3-nov) se hizo desde el entorno original (`riffocardenas-bit`) y sobre el `main` del 19-oct, sin los cambios de `master`.
- **Sin determinar:** por qué `proyecciones.py` y `estado_proyectos.py` quedaron en versiones anteriores (hecho 4). Hay dos lecturas compatibles con los datos:
  1. el entorno nuevo tenía una copia desactualizada de esos archivos;
  2. se revirtieron a propósito para calzar con la simplificación de `get_proyecciones()` del 19-oct.

  Git no permite distinguirlas. El hecho 8 muestra que, si fue a propósito, el frontend no se ajustó.

## Preguntas abiertas para José

1. ¿Cómo nació `master` el 21-oct? ¿`git init` en otro equipo, copia de carpeta…?
2. `proyecciones.py` y `estado_proyectos.py` del 21-oct: ¿copia desactualizada o reversión intencional?
3. ¿Desde qué rama y equipo se despliega hoy producción?
4. AdC: ¿vuelve su carga o se saca del frontend? (`docs/BACKLOG.md`, ítem 1a)

Cuando José responda, registra la respuesta en la sesión que corresponda y actualiza esta página: cambia la etiqueta **[inferido]** por la fuente, por ejemplo "confirmado por José, 2026-11-05".

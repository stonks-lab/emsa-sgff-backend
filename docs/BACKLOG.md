# Backlog técnico — emsa-sgff-backend

Pendientes detectados al revisar el repo y al preparar un entorno local de pruebas (noviembre 2026). Prioridad: **P1** bloquea o es riesgo de seguridad · **P2** reduce fricción o deuda importante · **P3** mejora.

Cuando trabajes un ítem, abre un issue o PR y enlázalo aquí. Borra el ítem cuando esté resuelto.

## P1

### 1. Unificar `master` y `main`
`master` (y `feat/simulacion-improvements`, que sale de ella) tiene una historia **sin ningún commit en común con `main`**. Código que solo está en `master`: `etl/` completo, scripts del servicio de Windows (`setup_servicio.ps1`, `run_servicio.bat`, `start.ps1`), `app/routers/kpi_contratos.py`, `reload_proyecciones.py`. Solo en `main`: `app/routers/auth.py`. Además, 16 archivos tienen contenido distinto en las dos ramas.
- Integrar en `main` (merge con `--allow-unrelated-histories` y resolver los conflictos), confirmar desde qué rama se despliega y luego borrar `master`.
- Ojo: `.gitignore` excluye `etl/`, pero en `master` está versionado. Hay que decidir si va al repo.

Lo que se reconstruyó del historial:
1. `main` avanzó hasta el 19-oct (`cd59c66`).
2. `master` partió el 21-oct como copia de ese `main`, con cambios encima, y siguió hasta el 2-nov.
3. El 3-nov se commiteó en `main` (`2e76ab2`, auth y metros vía SQL) sobre el `main` viejo.

Consecuencia: `main` quedó inconsistente. Su `proyecciones.py` llama a `get_proyecciones(proyecto=…, periodo_hasta=…)`, parámetros que `sql_server.py` eliminó el 19-oct, por lo que `/proyecciones/tabla` y `/comparacion` dan 500. Además, 8 endpoints que usa el frontend existen solo en `master`.

Propuesta de integración, ya probada en local contra el frontend: tomar `feat/simulacion-improvements` como base y aplicar encima `2e76ab2`. Quedan 10 bloques de conflicto en 5 archivos:

| Archivo | Versión elegida | Detalle |
|---|---|---|
| `main.py` | ambas | registra `kpi_contratos` y `auth` |
| `sql_server.py` | `feat` | sin `DEBUG`, con filtro de vigentes |
| `licitaciones.py` | `main` | diagnóstico con respaldo SOLPE |
| `metros.py` | `main` | lee `Proyecciones_P&C` por SQL en vez de `etl/d2.parquet`, que no está en el repo; se pierden `/cruce/debug` y `/avance/debug` |

Resultado: 70 de 77 endpoints responden 200 con datos de prueba. Fallan los 5 de Monday (sin token) y los 2 que se describen abajo.
- `/proyecciones/comparacion` no existe en `master`, pero el frontend todavía la llama desde `Proyecciones.tsx`. Hay que restaurarla o quitarla del frontend.
- En `feat`, las 4 fuentes SIC se leen desde SQL (`SIC_EPsDetalles`, `SIC_Solpes`, `SIC_BoletasGarantia`, `SIC_ContratosItemizado`) y no desde Excel. `config.EXCEL_FILES` queda solo para `/upload/fuentes-externas`, que reporta fechas de archivos que ya no se usan.

### 1b. La API no exige autenticación
Solo `/auth/users` valida el token. Todos los endpoints de datos (`/saldo/*`, `/simulacion/*`, `/upload/*`, etc.) responden 200 sin token: el login solo protege la UI. Agregar una dependencia global (`dependencies=[Depends(...)]` en cada `include_router`) que valide el JWT y, donde corresponda, el rol. Los permisos por rol hoy viven solo en el frontend (`src/auth/roles.ts`).

### 2. Seguridad de la autenticación (`app/routers/auth.py`)
- `JWT_SECRET` tiene un valor por defecto en el código (`tablero-emsa-key-2024`). Debe ser obligatorio por entorno y sin default.
- Las contraseñas se guardan con SHA-256 sin sal. Hay que migrar a bcrypt o argon2 (por ejemplo, `passlib` o `argon2-cffi`).
- Los usuarios viven en `users.json`, en la raíz del repo, y **ese archivo no está en `.gitignore`**: hay riesgo de subir hashes al repo. Moverlos a una tabla de la base o, como mínimo, agregarlos al `.gitignore`.
- Evaluar si conviene integrar con `emsa-identity-backend` (LDAP/AD), que ya existe en la org.

### 3. CORS abierto
`app/main.py` usa `allow_origins=["*"]`. Restringirlo por variable de entorno a los orígenes reales.

## P2

### 4. Migraciones de base de datos (Alembic)
No hay migraciones. Hoy el esquema está repartido:
- Tablas que la app crea sola con `IF NOT EXISTS`: `CostoMetro`, `ConfigDPO`, `RegistroCarga`, `Simulacion`, `SimulacionLinea`, `proyecciones`.
- Tablas que se dan por existentes y llena el ETL (solo en `master`): `SIC_Contratos`, `SIC_EPs`, `sourcing_plan`, la vista `v_proyecciones_vs_ep`.
- Tablas que se borran y recrean en cada carga de Excel: `dim_articulos`, `dim_proyectos`, `dim_programas`, `registro_incidencias`.

Propuesta: usar Alembic (SQLAlchemy ya es dependencia) para las tablas propias y la vista, de modo que `alembic upgrade head` deje cualquier servidor listo. Quedan fuera las tablas de la base BI (`PAI_Proyectos`, `Avance_Semanal`), que son de otro equipo, aunque hay que documentar qué columnas se esperan de ellas.

### 5. Entorno local reproducible
Falta una forma de levantar el sistema sin acceso a los servidores de EMSA. Propuesta: `docker-compose` con SQL Server Developer y un script de datos de prueba (`seed`), más un `.env.example` completo. Ya hay una versión local fuera del repo que puede servir de base.

### 6. Rutas fijas en el código
- `app/config.py`: `EXCEL_DIR` se calcula subiendo 4 niveles desde `config.py` hasta `API-SIC/`. Depende de dónde quede clonado el repo. Debería ser una variable de entorno. Si se integra `master`, que ya no lee Excel, basta con eliminarlo.
- `app/main.py`: el build del frontend se busca en `../frontend/dist`. Si el repo del frontend se clona con su nombre (`emsa-sgff-frontend`), no lo encuentra. Debería ser una variable de entorno.

### 7. Conexión a SQL Server no configurable
El connection string (`app/data/sql_server.py`) no permite definir `Encrypt` ni `TrustServerCertificate`. El ODBC Driver 18 cifra por defecto, así que falla contra servidores con certificado propio. Agregar variables de entorno para esto. En local se resolvió agregando esas opciones al valor de `SQL_SERVER`, pero es un parche.

En macOS, el driver ODBC 18 solo soporta OpenSSL 1.x o 3.x, y Homebrew puede apuntar `openssl` a la versión 4. Hay que documentarlo en el README (`DYLD_LIBRARY_PATH=$(brew --prefix openssl@3)/lib`).

### 8. `.env.example` incompleto
Faltan `MONDAY_API_KEY`, `MONDAY_BOARD_ID`, `SQL_BI_DATABASE` y `JWT_SECRET`.

### 9. Dependencias sin versión fija
`requirements.txt` usa `>=`. Fijar versiones (por ejemplo, con `pip-tools` o `uv`) para que los despliegues sean reproducibles. Declarar también la versión de Python soportada.

### 10. Errores silenciados
Hay unos 50 `except Exception:` que devuelven `[]`, `{}` o `None` sin registrar nada. Cuando falla la base, la UI muestra vacíos en vez de un error. Agregar `logging` y devolver errores HTTP donde corresponda.

## P3

### 11. Tests y CI
No hay tests ni CI. Partir con tests de humo de los endpoints (FastAPI `TestClient` contra la base de prueba del punto 5) y un workflow de GitHub Actions que corra lint y tests en cada PR.

### 12. Código de depuración
`app/data/sql_server.py` (`get_sim_vendor_codes`) tiene `print("=== DEBUG SIM ===")` y su comentario dice "eliminar después". Quitarlo o pasarlo a `logging.debug`.

### 13. Nombre visible
El título de la API sigue siendo "Tablero DAB-DPO API" (`app/main.py`). Decidir si pasa a SGFF.

### 14. Protección de `main`
`main` no tiene reglas de protección. Exigir PR y revisión antes de mergear.

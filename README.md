# emsa-sgff-backend

API del **SGFF — Sistema de Gestión Físico-Financiera** de EMSA.

El SGFF conecta la gestión **física** (la operación: proyectos, sondajes, metros perforados) con la gestión **financiera** (contratos, licitaciones, compras, presupuesto). Así se puede ver el impacto económico de cada decisión operativa. Reemplaza el trabajo que hoy se hace en planillas Excel y en Monday.com.

Frontend asociado: [`emsa-sgff-frontend`](https://github.com/stonks-lab/emsa-sgff-frontend).

## Funcionalidades

- **Contratos**: saldo de contratos, asignación contrato ↔ proyecto, evolución y línea de tiempo del saldo.
- **Estados de pago (EP)**: detalle por mes y por tipo, curva S financiera.
- **Licitaciones y compras**: procesos de licitación (desde Monday.com), SOLPEs, KPIs por categoría y tiempos.
- **Operación**: estado de proyectos, metros perforados, presupuesto de perforación y costo por metro (AR / DDH).
- **Proyecciones y simulación**: validación de proyecciones, sourcing plan y escenarios.
- **Alertas**: vencimiento de boletas y alertas de contratos.
- **Administración**: carga de datos (Excel) y registro de cargas.
- **Autenticación**: JWT.

## Stack

- Python 3 · [FastAPI](https://fastapi.tiangolo.com/) · Uvicorn
- pandas · openpyxl (procesamiento de planillas)
- SQLAlchemy · pyodbc → Microsoft SQL Server
- httpx → API de Monday.com
- PyJWT

## Requisitos previos

- Python 3.10 o superior
- [Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Acceso de red a la base de datos SQL Server de EMSA

## Instalación y ejecución local

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # completar con los valores reales
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000/api`
- Health check: `GET /api/health`
- Documentación interactiva (OpenAPI): `http://localhost:8000/docs`

## Configuración

Las variables se leen desde el entorno o desde un archivo `.env` en la raíz del repo (ver `.env.example`). **No subas `.env` al repositorio.**

| Variable | Descripción |
|---|---|
| `SQL_SERVER` | Host o IP de SQL Server (obligatoria) |
| `SQL_DATABASE` | Base de datos principal (obligatoria) |
| `SQL_AUTH` | Tipo de autenticación (por defecto `sql`) |
| `SQL_USER` / `SQL_PASSWORD` | Credenciales principales |
| `SQL_BI_USER` / `SQL_BI_PASSWORD` | Credenciales de lectura para las tablas de avance/PAI |
| `SQL_BI_DATABASE` | Base de datos BI (por defecto `BI_dev`) |
| `MONDAY_API_KEY` | Token de la API de Monday.com |
| `MONDAY_BOARD_ID` | ID del tablero de Monday.com |

## Estructura del proyecto

```
app/
├── main.py          # App FastAPI, registro de routers y servicio del build del frontend
├── config.py        # Configuración y variables de entorno
├── routers/         # Endpoints por módulo (saldo, ep, licitaciones, metros, dpo, monday, auth…)
├── data/            # Acceso a datos: SQL Server y carga de planillas
└── metrics/         # Cálculo de KPIs y métricas
```

## Despliegue

En producción, el backend también sirve el frontend ya compilado. Si existe el directorio `../frontend/dist` (relativo a la raíz de este repo), FastAPI lo publica en `/` y deja la API bajo `/api`.

## Documentación

La documentación técnica y funcional va en la carpeta [`docs/`](docs/) de este repositorio.

## Contribuir

1. Crea una rama desde `main` (`feat/…`, `fix/…`, `docs/…`).
2. Haz commits con tu propia identidad de git/GitHub.
3. Abre un Pull Request para revisión.

---

© EMSA. Uso interno.

# AGENTS.md

Instrucciones para agentes de IA y personas que trabajan en este repositorio.

## Proyecto

`emsa-sgff-backend`: API del SGFF (Sistema de Gestión Físico-Financiera) de EMSA, con FastAPI y SQL Server. La consume [`emsa-sgff-frontend`](https://github.com/stonks-lab/emsa-sgff-frontend). Ver [README.md](README.md).

## Ramas y Git

- **La rama principal es `main`.** `master` y `feat/simulacion-improvements` son historia anterior y se integran en el PR #4. No crees ramas a partir de ellas.
- Crea cada rama desde un `main` actualizado (`git pull` antes), con prefijo `feat/`, `fix/` o `docs/`.
- Todo cambio entra a `main` por Pull Request. No hagas push directo a `main`.
- No crees ramas con historia propia, por ejemplo con un `git init` nuevo o un repo copiado: así nació `master`. Si `git merge-base main <rama>` no devuelve nada, detente y avisa.
- Para un merge que une historias, usa "Create a merge commit", no squash.
- Cada persona firma sus commits con su propia identidad de git/GitHub. El proyecto es de EMSA.
- Borra la rama cuando su PR esté mergeado.

## Comandos

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # completar con los valores reales
uvicorn app.main:app --reload --port 8000           # API en http://localhost:8000/api, docs en /docs
```

No hay tests automatizados. Antes de abrir un PR, levanta la API y prueba los endpoints que tocaste. Si el cambio afecta pantallas, pruébalo también con el frontend.

## Convenciones

- Un router por módulo en `app/routers/`. El acceso a SQL Server va en `app/data/sql_server.py`. Los cálculos, en `app/metrics/`.
- Antes de quitar o dar por "no usado" un endpoint, búscalo en el frontend por la ruta **y** por el nombre de la función de `src/api/client.ts`. El frontend captura los errores y muestra bloques vacíos, así que una pantalla rota no siempre da error en la consola.
- Si cambias la firma de una función de `app/data/`, revisa todas sus llamadas (`git grep "<función>("`). En `main` hubo dos endpoints que dieron 500 durante semanas por eso.
- La documentación va en `docs/` de este repo y los pendientes técnicos en [`docs/BACKLOG.md`](docs/BACKLOG.md). No hay un repo `-docs` aparte.

## Secretos

- Las credenciales reales van en `.env`, que está ignorado por git. No subas `.env`, `users.json` ni `etl/config_etl.py`, y no imprimas sus valores en logs, PR ni chats.
- Un entorno local de pruebas nunca debe apuntar al SQL Server real. Si usas uno, que exporte sus propias variables `SQL_*` y verifique que el servidor sea local.

## Sesiones y worklog

El trabajo se registra en [`.worklog/`](.worklog/INDICE.md) con el protocolo de [`.claude/rules/sesiones.md`](.claude/rules/sesiones.md). Con Claude Code: `/inicio-sesion <objetivo>` al empezar y `/cierre-sesion` al terminar, en la misma rama.

- **Una sesión = una rama = un archivo** `.worklog/sesiones/AAAA-MM-DD_tema.md`, con su fila en `.worklog/INDICE.md`.
- Registra decisiones con hora, quién decidió y por qué. Anota también los hallazgos y los errores, incluidos los propios.
- **Cada hecho lleva su fuente** (commit, PR, comando o prueba). Lo que no se pudo comprobar se marca **[inferido]**, con a quién preguntar. No se reconstruye el *por qué* de un cambio ajeno desde su diff.
- Lo anterior al 4-nov de 2026 está reconstruido desde git en [`.worklog/HISTORIAL-RECONSTRUIDO.md`](.worklog/HISTORIAL-RECONSTRUIDO.md), con preguntas abiertas para el autor original.

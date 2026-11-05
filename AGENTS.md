# AGENTS.md

Instrucciones para agentes de IA y personas que trabajan en este repositorio.

## Proyecto

`emsa-sgff-backend`: API del SGFF (Sistema de Gestión Físico-Financiera) de EMSA, con FastAPI y SQL Server. La consume [`emsa-sgff-frontend`](https://github.com/stonks-lab/emsa-sgff-frontend). Ver [README.md](README.md).

## Flujo de trabajo: GitHub Flow

**Regla:** este repo usa **GitHub Flow**. Pasará a **Gitflow** solo cuando lo decida Aldo Saavedra. Hasta que esa decisión quede escrita en este archivo, nadie, ni persona ni agente, crea `develop`, `release/*` ni `hotfix/*` ni cambia el flujo.

- **La rama principal es `main`**, la única permanente, y debe poder desplegarse siempre. `master` y `feat/simulacion-improvements` eran historia anterior: entraron a `main` con el PR #4 y se borraron el 2026-11-04.
- Cada cambio va en una rama corta creada desde un `main` actualizado (`git pull` antes). El prefijo es el tipo de Conventional Commits: `feat/`, `fix/`, `docs/`, `refactor/`, `chore/` o `test/`.
- Todo cambio entra a `main` por Pull Request. No hagas push directo a `main`.
- **Todo PR necesita la aprobación de otra persona del equipo** (Aldo Saavedra u otro miembro), **nunca de quien lo abrió**. Solo después de esa aprobación, el autor lo mergea como se indica abajo.
- Cómo mergear un PR:
  - **Squash merge** si es un solo cambio lógico. El título del PR va en formato Conventional Commits, porque queda como el commit en `main`.
  - **Create a merge commit** si trae varios commits atómicos que vale la pena conservar, o si une historias. El mensaje es `Merge PR #N: <título>`.
- No crees ramas con historia propia, por ejemplo con un `git init` nuevo o un repo copiado. Así nació `master`. Si `git merge-base main <rama>` no devuelve nada, detente y avisa.
- Cada persona firma sus commits con su propia identidad de git/GitHub. El proyecto es de EMSA.
- Borra la rama cuando su PR esté mergeado.
- Al pasar a Gitflow se actualizan este archivo, `CLAUDE.md` y `.claude/hooks/session-context.sh`.

## Commits

- **Conventional Commits, siempre:** `<tipo>(<ámbito opcional>): <descripción>`.
  - Tipos: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `style` y `revert`.
  - Descripción en español, con minúscula inicial, sin punto final y de hasta 72 caracteres.
  - El cuerpo, opcional, explica qué cambia y por qué.
  - Un cambio incompatible lleva `!` después del tipo o el pie `BREAKING CHANGE: …`.
  - Ejemplos: `fix(proyecciones): aceptar los filtros proyecto y periodo_hasta`, `docs(backlog): registrar que no hay carga AdC`.
- **Commits atómicos:** un commit es un solo cambio lógico, que funciona por sí mismo y se puede revertir sin arrastrar otra cosa.
  - No mezcles en un commit una funcionalidad con un refactor, con formato o con documentación de otro tema.
  - Si para describir el commit necesitas "y" entre dos cambios independientes, son dos commits. Usa `git add -p` para separar cambios dentro de un mismo archivo.
  - Los merge commits (`Merge PR #N: …`) quedan exentos del formato.
- Los commits anteriores a esta regla (adoptada el 2026-11-04 a las 14:38) no siempre la cumplen y no se reescriben.

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

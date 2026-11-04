# CLAUDE.md

Las instrucciones de este repo están en [AGENTS.md](AGENTS.md). Las más importantes:

- **GitHub Flow, siempre.** `main` es la única rama permanente. Cada cambio va en una rama corta desde `main` (`feat/`, `fix/`, `docs/`, `refactor/`, `chore/`, `test/`) y entra por PR. No crees `develop` ni pases a Gitflow: eso lo decide solo Aldo Saavedra.
- **Conventional Commits y commits atómicos, siempre:** `<tipo>(<ámbito>): <descripción>`, un cambio lógico por commit.
- Si `git merge-base main <rama>` está vacío, detente y avisa.
- Abre la sesión con `/inicio-sesion` y ciérrala con `/cierre-sesion`; el registro va en `.worklog/`.

@AGENTS.md

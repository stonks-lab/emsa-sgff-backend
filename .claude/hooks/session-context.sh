#!/bin/sh
# session-context (SessionStart): inyecta el contexto del repo al abrir la sesión.
# Emite JSON con hookSpecificOutput.additionalContext.
# POSIX sh: funciona en macOS/Linux y en Windows con Git Bash.

# La raíz se deriva del script, no del cwd: el hook puede correr desde cualquier lado.
RAIZ=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$RAIZ" || exit 0

rama=$(git symbolic-ref --short -q HEAD 2>/dev/null || echo "?")
sucios=$(git status --porcelain 2>/dev/null | grep -c . | tr -d ' ')

texto="## Contexto del repo (SessionStart)
- Rama: $rama | archivos sin commitear: $sucios
- Abre la sesión con /inicio-sesion y ciérrala con /cierre-sesion en la misma rama (ver .claude/rules/sesiones.md)."

if [ -d ".worklog/sesiones" ]; then
    ultima=$(ls -1 .worklog/sesiones/*.md 2>/dev/null | sort -r | head -1)
    [ -n "$ultima" ] && texto="$texto
- Última sesión: $(basename "$ultima")"
fi

if [ "$rama" = "main" ]; then
    texto="$texto
- Estás en main: crea una rama antes de cambiar algo. main solo recibe PR."
fi

# Lección de este repo: master nació el 21-oct como una historia aparte de main.
base=main
git rev-parse -q --verify main >/dev/null 2>&1 || base=origin/main
if git rev-parse -q --verify "$base" >/dev/null 2>&1 && [ "$rama" != "main" ] && [ "$rama" != "?" ]; then
    if ! git merge-base "$base" HEAD >/dev/null 2>&1; then
        texto="$texto
- ⚠️ La rama $rama NO comparte historia con main (git merge-base vacío). Detente y avisa antes de seguir."
    fi
fi

texto="$texto
- Flujo: GitHub Flow (rama corta desde main y PR a main; pasar a Gitflow lo decide solo Aldo).
- Commits: Conventional Commits y atómicos, con tu propia identidad de git."

# JSON a mano (sin jq): se escapan comillas, backslashes y saltos de línea.
escapado=$(printf '%s' "$texto" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk 'BEGIN{ORS=""} {print (NR>1 ? "\\n" : "") $0}')
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$escapado"
exit 0

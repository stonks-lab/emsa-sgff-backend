#!/bin/sh
# worklog-reminder (Stop): recordatorio NO bloqueante para mantener el worklog.
# Solo avisa si hay cambios sin commitear que no tocan .worklog/, es decir, trabajo
# sin registrar. Una línea y exit 0.
# POSIX sh: funciona en macOS/Linux y en Windows con Git Bash.

# La raíz se deriva del script, no del cwd.
RAIZ=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$RAIZ" || exit 0

changes=$(git status --porcelain 2>/dev/null)
[ -z "$changes" ] && exit 0

count=$(printf '%s\n' "$changes" | grep -c .)

if printf '%s\n' "$changes" | grep -q '\.worklog/'; then
    exit 0
fi

echo "[worklog-reminder] Hay $count cambio(s) sin registrar en .worklog/. Recuerda registrar la sesión (ver .claude/rules/sesiones.md)."
exit 0

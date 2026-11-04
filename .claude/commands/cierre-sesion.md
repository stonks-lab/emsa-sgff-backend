---
description: Cierra la sesión en su rama, actualiza el worklog y el backlog, y abre el PR a main.
---

# /cierre-sesion

En la **misma rama** de la sesión, en este orden:

1. Completa el archivo de sesión de `.worklog/sesiones/` (resumen: logros, bloqueos, para retomar). Revisa que cada hecho tenga fuente y que lo no comprobado esté marcado **[inferido]**.
2. Agrega o actualiza su fila en `.worklog/INDICE.md`:
   `| [MM-DD](sesiones/AAAA-MM-DD_tema.md) | Descripción breve | `ruta/` | ✅/🔄/❌ |`
3. Actualiza `docs/BACKLOG.md` si apareció, cambió o se resolvió un pendiente.
4. Si se respondió una pregunta abierta de `.worklog/HISTORIAL-RECONSTRUIDO.md`, actualízala con su fuente.
5. Actualiza `AGENTS.md` solo si cambió una instrucción durable.
6. Commit de cierre: `docs(worklog): cerrar la sesión de <tema>`, con tu propia identidad de git.
7. Pregunta antes de publicar: `git push -u origin <rama>` y `gh pr create --base main`. No mergees sin confirmación explícita.
8. Confirma qué archivos se actualizaron.

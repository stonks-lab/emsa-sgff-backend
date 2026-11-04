# Protocolo de sesiones de trabajo

**Una sesión = una rama.** `/inicio-sesion` la abre y `/cierre-sesion` la completa en esa misma rama, antes del PR. Con otro agente u otra herramienta, sigue los mismos pasos a mano.

## Al iniciar (`/inicio-sesion`)

1. Revisa lo abierto: `git status`, ramas sin integrar y PR abiertos.
2. Pregunta el objetivo si no viene como argumento.
3. Lee la última sesión de `.worklog/sesiones/` y los pendientes de `docs/BACKLOG.md` que toquen el tema.
4. Crea la rama desde un `main` al día.
5. Crea `.worklog/sesiones/AAAA-MM-DD_tema.md` con la plantilla del comando.

## Durante la sesión

- Registra cada decisión con su hora, quién la tomó y las alternativas consideradas.
- Anota los hallazgos: limitaciones, configuraciones no obvias y errores, incluidos los propios.
- **Separa lo verificado de lo inferido.** Todo hecho lleva su fuente: commit, PR, comando o prueba. Lo que no se pudo comprobar va marcado como **[inferido]**, con a quién hay que preguntarle.
- No reconstruyas el *por qué* de un cambio ajeno a partir de su diff. Si el mensaje del commit no lo dice, pregúntale al autor y anota la pregunta.

## Al cerrar (`/cierre-sesion`)

1. Completa el archivo de sesión: resumen, bloqueos y para retomar.
2. Agrega o actualiza su fila en `.worklog/INDICE.md`.
3. Actualiza `docs/BACKLOG.md` si apareció, cambió o se resolvió un pendiente.
4. Si alguien respondió una pregunta abierta de `.worklog/HISTORIAL-RECONSTRUIDO.md`, actualízala ahí, con la fuente.
5. Actualiza `AGENTS.md` **solo** si cambió una instrucción durable: regla, stack o convención.
6. Haz el commit de cierre y el PR hacia `main`. No mergees sin confirmación.

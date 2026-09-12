# Evidencias de AulaData

Ejecución local del **12 de septiembre de 2026** sobre PostgreSQL 17, FastAPI y
Next.js 16.3.5 en contenedores Docker. URL: <http://localhost:3000>.
Ambiente `DEV`, versión `v1.0.0-local`, código de aplicación
`a6ac4966ef3c09edbd3c855a8668fe6e2e8410cf`. Los commits posteriores documentan esta
entrega y añaden evidencias; no cambian el código ejecutado en las imágenes.

## Capturas finales

Todas son capturas originales de Chromium mediante Playwright contra la API y
PostgreSQL reales. No se usaron respuestas simuladas. El frontend estaba en modo
producción, aunque el ambiente de la aplicación era DEV local.

| Archivo | Acción y resultado observado |
| --- | --- |
| [01-login.png](01-login.png) | Inicio de sesión y metadatos de ambiente. |
| [02-aulas-admin.png](02-aulas-admin.png) | Directorio de seis aulas sintéticas con controles ADMIN. |
| [03-nueva-aula.png](03-nueva-aula.png) | Formulario completo antes del alta. |
| [04-detalle-aula.png](04-detalle-aula.png) | Registro persistido, consultado de nuevo tras recargar. |
| [05-editar-aula.png](05-editar-aula.png) | Cambio de capacidad y estado, guardado después por la prueba. |
| [06-confirmacion-baja.png](06-confirmacion-baja.png) | Confirmación de baja lógica; se probó cancelar y confirmar. |
| [07-aulas-viewer.png](07-aulas-viewer.png) | Consulta VIEWER sin controles de administración. |
| [08-aulas-movil.png](08-aulas-movil.png) | Consulta a 390 px, sin desbordamiento del documento. |
| [09-health.png](09-health.png) | Respuesta real con ambiente, versión y commit. |

Las capturas anteriores se conservan en `desarrollo/` y `docker-inicial/`. Esas
carpetas reflejan fases previas, incluidos metadatos `unknown` o un commit anterior;
no deben presentarse como evidencia de la release final. Las aulas creadas por E2E
se dan de baja al finalizar; por eso no aparecen luego en el directorio.

## Resultados ejecutados

| Verificación | Resultado | Evidencia |
| --- | --- | --- |
| Backend PostgreSQL 17 | 69 aprobadas | [JUnit](backend-postgres-junit.xml) |
| Backend SQLite aislado | 69 aprobadas | [JUnit](backend-sqlite-junit.xml) |
| Navegador Chromium | 5 aprobadas, última ejecución 8,0 s | [JUnit](frontend-junit.xml) |
| Manifiestos de despliegue | 7 aprobadas | [Resumen](validation-summary.md) |
| Ruff, ESLint, TypeScript | Sin errores | [Resumen](validation-summary.md) |
| Next.js y dos imágenes Docker | Construcción exitosa | [Resumen](validation-summary.md) |
| Backend y frontend no-root | Verificados | [Estado e IDs de imágenes](infra-final-status.txt) |
| PostgreSQL, backend y frontend | 3 servicios saludables, 0 reinicios | [Estado](infra-final-status.txt) |
| pip-audit / pnpm audit runtime | 0 vulnerabilidades conocidas | [Backend](backend-audit.json), [frontend](frontend-audit.json) |
| Smoke, backup y restauración aislada | Aprobados | [Resumen](validation-summary.md) |

Las cinco pruebas E2E verifican también cookies HttpOnly/SameSite=Lax, ausencia de
token en localStorage, duplicados 409, capacidad inválida, persistencia al recargar,
filtros, cancelación de baja, baja confirmada, logout y rechazo 403 a POST/PUT/PATCH/
DELETE de VIEWER. Los tests backend comprueban que la fila dada de baja se conserva.

## Incidencia de hora del equipo

Se observaron saltos de seis horas en Docker/WSL que produjeron
`ExpiredSignatureError`. Se reprodujeron con HTTP directo y mediante Next.js.
Reiniciar Docker y ajustar una vez el reloj UTC del invitado no estableció una
sincronización permanente: el desfase reapareció. Windows y su zona horaria no se
modificaron. Se mantuvieron los límites de expiración y la validación JWT.

El stack final aprobó 160 consultas autenticadas y dos ejecuciones E2E completas
consecutivas. Esto prueba los flujos ejecutados; no demuestra que la causa del
reloj haya quedado resuelta. Revisar sincronización UTC/NTP antes de las prácticas
de laboratorio y si reaparecen cierres de sesión. Microsoft documenta problemas de
[desfase de reloj de WSL](https://github.com/microsoft/WSL/issues/10006); el diagnóstico
de este equipo y sus límites se describen en [operación](../operations.md).

## Pendiente en infraestructura real

Publicar el repositorio y obtener revisión humana del PR; desplegar en DEV, QA y
PROD reales; registrar los mismos digests entre ambientes y ejecutar rollback,
migración live, HA y monitoreo en Proxmox. Estas capturas locales no acreditan esos
eventos. Consultar [aceptación](../acceptance.md) y [entrega](../entrega.md).

Los secretos, cookies, trazas de red y dumps privados están excluidos de Git.

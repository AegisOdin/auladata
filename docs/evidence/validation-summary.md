# Registro de verificaciones locales

Fecha: 2026-09-12. Código final de aplicación: `a6ac496`.
Este documento resume las salidas observadas durante la sesión; los XML y JSON
adjuntos conservan los reportes automáticos. No es una ejecución de GitHub Actions
ni una prueba de despliegue en Proxmox.

| Comando o procedimiento | Resultado observado |
| --- | --- |
| `python -m pytest tests/backend` con SQLite efímero | 69 PASS. |
| Mismo comando con `TEST_DATABASE_URL` PostgreSQL 17 | 69 PASS; última ejecución 8,85 s. |
| `python -m unittest discover -s deploy/tests -v` | 7 PASS. |
| `ruff check app/backend migrations tests deploy/scripts deploy/tests` | All checks passed. |
| `ruff format --check app/backend migrations tests deploy/scripts deploy/tests` | 35 archivos correctamente formateados. |
| `pnpm lint` | Exit 0; sin advertencias ni errores. |
| `pnpm typecheck` | Exit 0. |
| `pnpm build` | Next.js 16.3.5 compiló rutas y salida standalone. |
| Docker build backend y frontend | Ambos completados; IDs en `infra-final-status.txt`. |
| `pnpm test:e2e` sobre Docker | 5/5 PASS (7,6 s); repetido tras fijar metadatos al commit final: 5/5 PASS (8,0 s). |
| `alembic upgrade head` | Migración inicial aplicada a PostgreSQL. |
| `alembic check` sobre PostgreSQL de pruebas | Sin cambios de esquema pendientes. |
| `python -m app.seed` | 2 usuarios, 6 aulas sintéticas; idempotencia verificada por pytest. |
| `docker compose ... config --quiet` | Compose local, laboratorio y tests válidos. |
| `bash -n deploy/scripts/*.sh` (cada archivo) | Sintaxis aprobada. |
| actionlint sobre los dos workflows | Sin hallazgos. |
| `python deploy/scripts/check-secrets.py` | Archivos privados y patrones de claves/tokens excluidos. |
| Smoke con origen HTTP, credenciales privadas y cookie | Salud, readiness, metadatos, login, sesión, aulas y logout PASS. |
| `pg_dump --format=custom` + `pg_restore --list` | Respaldo creado y archivo validado. |
| Restauración en base temporal nueva | 2 usuarios y 6 aulas comprobados; destino temporal retirado después. |

PostgreSQL de integración escucha solo en loopback, puerto local 15432; su base se
denomina `auladata_test` y las pruebas usan esquemas efímeros. PostgreSQL DEV local
no publica un puerto hacia el host. Los datos DEV se conservan en un volumen.

El ensayo temporal de API nativa en el puerto 8001 se detuvo. Al cerrar, la vista
previa utiliza el frontend Docker en 3000, el backend Docker en 8000 y PostgreSQL
Docker; no depende de ese proceso de diagnóstico ni de `next dev`.

Los tests emiten una advertencia de deprecación de Starlette/AnyIO sobre
`BlockingPortal`; no produce fallos. Los límites del reloj WSL y las tareas de
infraestructura pendientes se mantienen en el [inventario](README.md).

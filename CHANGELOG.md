# Changelog

## 1.0.0 — candidato sin publicar

- Gestión de aulas con consulta, búsqueda, filtros, creación, edición y baja lógica.
- Autenticación FastAPI con JWT en cookie HttpOnly y roles ADMIN/VIEWER validados en servidor.
- Modelos SQLAlchemy, validación Pydantic, migración Alembic y seed idempotente con datos sintéticos.
- Frontend Next.js App Router con TypeScript, Tailwind y metadatos de ambiente en runtime.
- Pruebas HTTP aisladas para autenticación, permisos, validaciones, CRUD y salud.
- Dockerfiles, Compose local y Compose para VM de aplicación con PostgreSQL externo.
- Pipeline de validación, pruebas, análisis y construcción, y herramientas de promoción por digest y rollback.
- Documentación de arquitectura, API, despliegue, operación, pruebas y evidencias académicas.

La publicación del tag `v1.0.0` y la promoción a PROD se realizan después de la aprobación real de QA. Consultar `docs/evidence/` para los resultados ejecutados y `docs/acceptance.md` para lo pendiente de demostrar en laboratorio.

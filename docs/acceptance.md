# Aceptación y evidencias de la práctica

Este documento indica cómo demostrar cada requisito. Los resultados de ejecución y las capturas disponibles se registran en `docs/evidence/`; una instrucción o una prueba escrita no equivale a una ejecución aprobada.

## Resultado local final

Se aprobaron 69 pruebas backend sobre PostgreSQL 17, 69 sobre SQLite aislado, 7 de los manifiestos de despliegue y 5/5 escenarios E2E en 8,0 s. E2E utilizó frontend Docker en modo producción, backend Docker y PostgreSQL 17. Se construyeron las dos imágenes, los tres servicios quedaron saludables y se completaron smoke, respaldo y restauración aislada. La auditoría runtime backend reportó 0 vulnerabilidades conocidas. Los [reportes y capturas](evidence/README.md) conservan el detalle.

Sigue abierta la estabilidad del reloj Docker/WSL: reaparece un desfase de aproximadamente seis horas respecto de Windows tras reinicio y ajuste manual. Las últimas 160 solicitudes autenticadas y E2E fueron correctas; no se declara resuelta la sincronización permanente. Comprobar UTC/NTP antes de las pruebas del laboratorio conforme a la [guía de entrega](entrega.md#hora-y-sesiones-del-laboratorio), manteniendo la validación temporal JWT sin ampliar `leeway`.

La verificación local de software está acreditada por esos resultados. El despliegue y la aceptación de los ambientes Proxmox requieren las evidencias pendientes indicadas abajo.

## Verificación de software

| Requisito | Evidencia a conservar |
| --- | --- |
| Arranque backend y PostgreSQL | `alembic current`, `/health` 200 y `/ready` 200 |
| Login real | Login correcto, error de contraseña y `/auth/me` |
| CRUD | Crear, consultar, editar y dar de baja desde la UI |
| Validaciones | Capacidad cero rechazada y clave duplicada con HTTP 409 |
| Baja lógica | Aula ausente en listado; fila conservada con `deleted_at` |
| ADMIN | Controles de crear/editar/baja y operación exitosa |
| VIEWER | Controles limitados y mutaciones HTTP rechazadas con 403 |
| Metadatos runtime | Captura del ambiente, versión y commit en la UI y `/health` |
| Pruebas automáticas | Salida íntegra de pytest y número real de casos aprobados |
| Frontend | Resultado de lint, TypeScript y build de producción |
| Despliegue reproducible | Validación de Compose, construcción Docker y smoke tests |
| Seguridad de configuración | `.env.example` sin secretos y estado Git revisado |
| Promoción | SHA y ambos digests iguales en QA y PROD |

## Capturas locales sugeridas

Guardar las capturas originales en `docs/evidence/` con nombres descriptivos. La suite E2E con `E2E_CAPTURE=1` utiliza `01-login.png`, `02-aulas-admin.png`, `03-nueva-aula.png`, `04-detalle-aula.png`, `05-editar-aula.png`, `06-confirmacion-baja.png`, `07-aulas-viewer.png` y `08-aulas-movil.png`. El inventario debe incluir fecha, ambiente real, URL, acción y resultado observado. Añadir la evidencia HTTP de `/health` y `/ready` al realizar las verificaciones de despliegue.

Una captura con `APP_ENV=QA` configurado localmente solo demuestra lectura runtime; no demuestra que la VM de QA exista ni que se haya desplegado en ella. Las capturas del navegador tampoco sustituyen la comprobación HTTP del RBAC.

## Ejecución pendiente en laboratorio

1. Registrar `dev-app01=10.10.30.10` y verificar conectividad hacia la base DEV real.
2. Desplegar DEV y guardar login, CRUD, `/health`, `/ready`, logs y revisión Alembic.
3. Crear el PR y obtener revisión real del otro integrante.
4. Desplegar el candidato en QA, ejecutar tests/smoke y registrar aprobación.
5. Promover los mismos digests a PROD y capturar `/health` con SHA esperado.
6. Ejecutar un rollback controlado de aplicación y demostrar persistencia de datos.
7. Respaldar PostgreSQL y restaurar en una base aislada; verificar conteos y login.
8. Ejecutar y documentar migración live de la app VM, falla de nodo y HA con los responsables del laboratorio.
9. Registrar alertas de monitoreo y recuperación, con tiempos medidos.

El contexto reporta una migración live previa de DEV. Las pruebas de PROD, HA, restauración y monitoreo requieren evidencias nuevas de su ejecución real. La aplicación preparada para esas pruebas no configura Proxmox, NFS, firewall, DNS ni certificados por sí sola.

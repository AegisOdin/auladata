# Operación y recuperación

Ejecutar las operaciones de laboratorio en la app VM correcta. Cada ambiente tiene archivo privado `/etc/auladata/<ambiente>.env`, manifiesto actual y base independiente. Las instrucciones locales de Docker están en el [README](../README.md).

## Consultar salud

`/health` comprueba que la API está viva y entrega metadatos; `/ready` comprueba conexión a PostgreSQL. El script compara los metadatos con el manifiesto actual:

```bash
(
  source deploy/scripts/common.sh
  load_runtime PROD
  load_release "$STATE_DIR/current.env"
  bash deploy/scripts/healthcheck.sh
)
```

El dominio se obtiene del archivo privado `BASE_URL` y el SHA de `current.env`. Para el smoke completo cargar de forma privada `SMOKE_EMAIL` y `SMOKE_PASSWORD` como indica [deploy/README.md](../deploy/README.md), y ejecutar `bash deploy/scripts/smoke-test.sh` dentro de la misma subshell. No poner contraseñas en capturas o argumentos del comando.

## Estado, logs, reinicio y parada

Desde Bash, en la raíz del repositorio, abrir una subshell que carga solo configuración propia y valida el manifiesto actual:

```bash
(
  source deploy/scripts/common.sh
  load_runtime DEV
  load_release "$STATE_DIR/current.env"
  compose ps
  compose logs --tail 100 backend frontend
)
```

En ese mismo patrón, sustituir `compose ps` por la operación necesaria:

| Operación | Comando |
| --- | --- |
| Reiniciar procesos | `compose restart backend frontend` |
| Detener temporalmente | `compose stop` |
| Arrancar detenidos | `compose start` |
| Recrear con la configuración vigente | `compose up -d --no-build --wait` |
| Esquema instalado | `compose run --rm --no-deps backend alembic current` |
| Historial de esquema | `compose run --rm --no-deps backend alembic history` |

Cambiar `DEV` por el ambiente real. `restart` no aplica modificaciones de variables de entorno; para ello recrear servicios con `up -d`. Las migraciones se ejecutan por el script de despliegue antes del arranque. No ejecutar varias migraciones/despliegues simultáneamente ni alterar tablas manualmente en QA/PROD.

Los logs deben mostrar rutas, estados y fallos sin cuerpos de login, cookies, JWT ni conexión completa. Revisar eventos fallidos por hora/ruta; no habilitar logging de secretos para diagnosticar un 401. Los contenedores del laboratorio rotan logs mediante el driver `json-file` configurado en Compose.

## Diagnóstico rápido

| Síntoma | Verificación |
| --- | --- |
| `/health` falla | Contenedor backend, puerto, proceso, firewall y ruta del proxy. |
| `/health` OK, `/ready` 503 | Host/puerto de PostgreSQL, rol, contraseña, reglas de acceso y disponibilidad de DB. |
| Login 401 | Correo/password del usuario realmente creado, estado activo y vigencia de la sesión. |
| Login funciona pero no mantiene sesión | HTTPS frente a `COOKIE_SECURE`, cookie y origen público consistente. |
| Mutación 403 | Rol, `X-Requested-With: AulaData` y `Origin` dentro de `CORS_ORIGINS`. |
| Tabla vacía | Ambiente/base correctos, seed de aulas, filtros y bajas lógicas. |
| Duplicado 409 tras baja | La clave de una fila dada de baja sigue reservada. Usar otra clave. |
| Metadatos inesperados | `current.env`, imágenes/digests efectivos y variables runtime. |
| Fallo al arrancar Next.js | Logs, `API_INTERNAL_URL` accesible desde su contenedor y disponibilidad de la API. |

## Migraciones y compatibilidad

La secuencia de migraciones es la misma en los tres ambientes; el destino lo determina `DATABASE_URL`. Se ejecuta desde la raíz con `alembic upgrade head`. Alembic registra la revisión aplicada y permite consultar el historial. [Tutorial oficial de Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

Antes de una nueva release comprobar compatibilidad del esquema con la versión anterior de la aplicación. Preferir ampliar el esquema y retirar elementos en una release posterior. La migración inicial sirve para una base nueva; su downgrade elimina tablas y no es un rollback operativo seguro de datos.

## Respaldos

El script de PROD ejecuta `backup.py` antes de migrar y aborta si el respaldo falla. Para generar un respaldo manual con la misma configuración:

```bash
(
  source deploy/scripts/common.sh
  load_runtime PROD
  python3 deploy/scripts/backup.py
)
```

El resultado es un archivo custom-format de `pg_dump` en `BACKUP_DIR` con permisos privados. Se escribe primero como `.partial` y se publica como `.dump` al completar el proceso. Mantener copias fuera de la VM y definir retención según el laboratorio. Confirmar que `BACKUP_IMAGE` corresponde a una versión de cliente PostgreSQL compatible con el servidor.

Un dump de base no incluye roles globales del clúster. Documentar también los roles y privilegios necesarios, sin publicar sus secretos. Un archivo existente no prueba recuperación; hay que restaurarlo y validar la aplicación. [Respaldo lógico de PostgreSQL](https://www.postgresql.org/docs/current/backup-dump.html).

## Prueba de restauración aislada

Elegir un servidor de pruebas y crear una base vacía con nombre distinto de DEV/QA/PROD. Ejemplo con herramientas PostgreSQL instaladas y autenticación administrada por el operador:

```bash
createdb --host "$RESTORE_HOST" --username "$RESTORE_USER" --template template0 auladata_restore_test
pg_restore --host "$RESTORE_HOST" --username "$RESTORE_USER" --dbname auladata_restore_test --no-owner --no-acl --exit-on-error "$BACKUP_FILE"
psql --host "$RESTORE_HOST" --username "$RESTORE_USER" --dbname auladata_restore_test -c 'SELECT version_num FROM alembic_version;'
psql --host "$RESTORE_HOST" --username "$RESTORE_USER" --dbname auladata_restore_test -c 'SELECT count(*) FROM classrooms;'
```

Configurar `RESTORE_HOST`, `RESTORE_USER` y `BACKUP_FILE` con destinos reales antes de usar el ejemplo; las herramientas solicitarán credenciales si corresponde. Apuntar una instancia aislada de AulaData a esa base, probar `/ready`, login y consulta, y guardar los resultados. No sobrescribir una base de servicio para realizar la práctica.

## Rollback de aplicación

Si una release falla, conservar logs y comprobar que el esquema continúa siendo compatible con la versión anterior. La reversión usa el manifiesto anterior o uno elegido explícitamente:

```bash
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/rollback.sh PROD
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/rollback.sh PROD /ruta/a/release-anterior.env
```

El script descarga las imágenes previas, levanta servicios sin reconstruir y ejecuta smoke. Actualiza el manifiesto actual solo después de validar. No ejecuta `alembic downgrade` ni restaura la base de forma automática.

Si la migración destruyó información o rompió compatibilidad, recuperar requiere un plan separado: detener escrituras, elegir el respaldo, estimar la pérdida de cambios posteriores, restaurar en un destino controlado y verificar antes de cambiar tráfico. Esta decisión debe registrarse con el responsable del ambiente.

## Alcance de la sesión

Logout borra la cookie del navegador. La autenticación JWT sin almacén central conserva el vencimiento del token emitido; no ofrece un panel de revocación individual. Rotar `JWT_SECRET` invalida todas las sesiones de ese ambiente. Mantener el secreto estable al reiniciar o migrar una app VM para conservar las sesiones válidas.

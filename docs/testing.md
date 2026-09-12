# Pruebas y validación

Las pruebas backend se ejecutan desde la raíz con pytest y FastAPI TestClient. Utilizan una base aislada: SQLite temporal para la comprobación rápida o PostgreSQL de pruebas cuando se define `TEST_DATABASE_URL`. PostgreSQL es la base de ejecución de la aplicación; una pasada con SQLite no sustituye la integración PostgreSQL.

Los resultados realmente ejecutados, versiones y limitaciones se guardan en [evidencias](evidence/README.md). Esta guía describe cómo repetir las verificaciones y no declara una ejecución que no se haya registrado.

## Resultado final de la ejecución local

| Verificación | Resultado |
| --- | --- |
| Backend PostgreSQL 17 | 69/69 aprobadas. |
| Backend SQLite aislado | 69/69 aprobadas. |
| Contratos de despliegue | 7/7 aprobadas. |
| E2E Chromium | 5/5 aprobadas en 8,0 s sobre frontend Docker en modo producción, backend Docker y PostgreSQL 17. |
| Docker | Ambas imágenes construidas; 3 servicios saludables. |
| Integración y recuperación | Smoke completo, respaldo y restauración aislada aprobados. |
| Auditoría runtime backend | 0 vulnerabilidades conocidas reportadas. |

Los JUnit backend y frontend se conservan en `docs/evidence/`. La limitación restante del entorno local es un desfase intermitente del reloj Docker/WSL de aproximadamente seis horas detrás de Windows. Se aprobaron las últimas 160 solicitudes autenticadas y la corrida E2E; no se considera resuelta la sincronización permanente después del reinicio/ajuste manual. Antes de repetir pruebas o pasar al laboratorio, [comparar UTC y verificar NTP](entrega.md#hora-y-sesiones-del-laboratorio). Mantener la validación temporal del JWT sin aumentar `leeway` para compensar el reloj.

## Backend

Instalar primero el entorno de desarrollo del [README](../README.md). PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m ruff check app/backend migrations tests
.\.venv\Scripts\python.exe -m ruff format --check app/backend migrations tests
```

Bash:

```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m ruff check app/backend migrations tests
.venv/bin/python -m ruff format --check app/backend migrations tests
```

La suite debe cubrir salud y metadatos, autenticación correcta/incorrecta, sesión, acceso sin login, creación válida, duplicados, capacidad inválida, edición, consulta inexistente, filtros, baja lógica, exclusión de bajas y permisos VIEWER para lectura/mutación. Consultar `tests/backend/` para los casos efectivos y sus aserciones. El resumen de pytest es la fuente del número de pruebas ejecutadas; no contar parametrizaciones manualmente.

## Integración con PostgreSQL aislado

`deploy/compose.test.yml` levanta un PostgreSQL efímero llamado `auladata_test`, con almacenamiento temporal y puerto `127.0.0.1:5433` por defecto. No comparte el volumen de desarrollo. Las credenciales se generan para esta ejecución y no se guardan en Git. Si Windows reserva ese puerto, establecer `TEST_DB_PORT=15432` y usar ese mismo valor en la URL.

PowerShell:

```powershell
$env:TEST_DB_PASSWORD = & .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_hex(24))'
$env:TEST_DB_PORT = '5433'
$env:TEST_DATABASE_URL = "postgresql+psycopg://auladata_test:$($env:TEST_DB_PASSWORD)@127.0.0.1:$($env:TEST_DB_PORT)/auladata_test"
docker compose -f deploy/compose.test.yml up -d --wait
.\.venv\Scripts\python.exe -m pytest -v
docker compose -f deploy/compose.test.yml down
Remove-Item Env:TEST_DATABASE_URL, Env:TEST_DB_PASSWORD, Env:TEST_DB_PORT
```

Bash:

```bash
export TEST_DB_PASSWORD="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(24))')"
export TEST_DB_PORT=5433
export TEST_DATABASE_URL="postgresql+psycopg://auladata_test:${TEST_DB_PASSWORD}@127.0.0.1:${TEST_DB_PORT}/auladata_test"
docker compose -f deploy/compose.test.yml up -d --wait
.venv/bin/python -m pytest -v
docker compose -f deploy/compose.test.yml down
unset TEST_DATABASE_URL TEST_DB_PASSWORD TEST_DB_PORT
```

Revisar el resultado de pytest antes de cerrar la terminal; `down` es limpieza y no debe interpretarse como resultado de pruebas. El `tmpfs` se pierde al detener el contenedor, por lo que esta base solo debe contener datos de test.

La fixture exige un nombre de base que contenga `test` cuando se proporciona PostgreSQL. Crea un esquema `auladata_test_<identificador>`, aplica allí `alembic upgrade head`, aísla cada caso mediante transacciones/savepoints y elimina ese esquema al terminar. El usuario de pruebas necesita permiso para crear esquemas en su base. El test independiente de upgrade/downgrade utiliza un archivo SQLite temporal; las pruebas HTTP con `TEST_DATABASE_URL` sí utilizan PostgreSQL.

La protección del nombre ayuda a evitar errores, pero no verifica quién administra el host: seleccionar explícitamente el servidor de pruebas. Nunca usar las credenciales ni la URL de PROD en `TEST_DATABASE_URL`. La suite crea y elimina sus propios objetos. La fixture fija la configuración de test antes de importar la aplicación para evitar conectarse accidentalmente a la base del `.env` de desarrollo.

## Frontend

Desde `app/frontend`, con Node.js 22 y pnpm 10.27.0:

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
```

El build compila y valida las rutas App Router.

## Navegador y capturas

Playwright requiere frontend y backend ya levantados, base migrada, cuentas ADMIN/VIEWER y al menos un aula vigente. Para el entorno de práctica local, ejecutar el seed con `SEED_DEMO=true` como indica el README. La suite crea, edita y da de baja aulas propias; ejecutarla en DEV local o en una instancia de pruebas, nunca en PROD.

Desde `app/frontend`:

```bash
pnpm exec playwright install chromium
pnpm test:e2e
```

En una instalación Linux sin bibliotecas de navegador, usar `pnpm exec playwright install --with-deps chromium` con los permisos administrativos correspondientes antes de correr las pruebas.

La configuración carga automáticamente el `.env` privado de la raíz mediante Node.js 22. Las variables E2E tienen precedencia en la selección de cuentas:

| Variable | Valor alternativo o predeterminado |
| --- | --- |
| `E2E_BASE_URL` | `http://localhost:3000` |
| `E2E_ADMIN_EMAIL` | `ADMIN_INITIAL_EMAIL` |
| `E2E_ADMIN_PASSWORD` | `ADMIN_INITIAL_PASSWORD` |
| `E2E_VIEWER_EMAIL` | `VIEWER_INITIAL_EMAIL` |
| `E2E_VIEWER_PASSWORD` | `VIEWER_INITIAL_PASSWORD` |
| `E2E_CAPTURE` | `1` guarda capturas; desactivado por defecto. |

En CI se pueden inyectar esas variables directamente sin archivo `.env`. Las cuentas deben existir con esas contraseñas; cambiar el valor del archivo no restablece usuarios ya creados. Si se cambia `E2E_BASE_URL`, incluir su origen en el `CORS_ORIGINS` del backend.

Para guardar las capturas desde PowerShell:

```powershell
$env:E2E_CAPTURE = '1'
pnpm test:e2e
Remove-Item Env:E2E_CAPTURE
```

En Bash:

```bash
E2E_CAPTURE=1 pnpm test:e2e
```

El reporte JUnit se escribe en `docs/evidence/frontend-junit.xml`. Las capturas opcionales se guardan en la misma carpeta con nombres `01-login.png` a `08-aulas-movil.png`, incluyendo ADMIN, formulario, detalle, edición, confirmación de baja y VIEWER. Una nueva ejecución actualiza los archivos con esos nombres; conservar en Git las evidencias que se quieran comparar. La configuración no genera trazas, HAR ni vídeo de sesiones.

Los cinco escenarios comprueban sesión/login/metadatos, CRUD ADMIN y persistencia al recargar, validaciones del formulario, permisos VIEWER por UI y HTTP, y consulta móvil sin desbordamiento. El resultado final de Playwright confirma cuántos pasaron; el archivo de pruebas no sustituye esa ejecución.

Como complemento, la validación manual reproducible es:

1. Login incorrecto: se muestra error y la sesión no queda activa.
2. Login ADMIN: aparece listado y controles de crear/editar/baja.
3. Crear aula: validar campos y comprobar que aparece en la tabla.
4. Buscar y combinar filtros: comprobar resultados y paginación.
5. Abrir detalle y editar: verificar los valores persistidos después de recargar.
6. Dar de baja: confirmar la operación y comprobar exclusión de la tabla.
7. Login VIEWER: solo consulta; verificar además el 403 con una petición HTTP de mutación.
8. Cerrar sesión: una ruta protegida vuelve a solicitar login.
9. Comprobar ambiente, versión y commit contra `/health`.

Guardar capturas en `docs/evidence/` con contexto y resultado real; evitar contraseñas y cookies visibles.

## Contenedores, smoke y dependencias

Con `.env` local completo, validar Compose sin imprimir valores secretos:

```bash
docker compose --env-file .env -f deploy/compose.local.yml config --quiet
docker compose --env-file .env -f deploy/compose.local.yml build
```

Después de arrancar y ejecutar migraciones/seed, el smoke en [deploy/README.md](../deploy/README.md) comprueba liveness, readiness PostgreSQL, metadatos, frontend, login, sesión, listado y logout.

El pipeline ejecuta análisis de dependencias además de tests/build. Repetir los comandos de auditoría definidos en `.github/workflows/ci.yml`; conservar el reporte real y justificar cualquier excepción concreta. No afirmar que una pasada de auditoría garantiza ausencia de vulnerabilidades.

## Criterio de aprobación

Una verificación queda aprobada cuando el comando termina con código cero y se revisa el resultado esperado. Para declarar la versión lista para laboratorio se necesita, al menos, una pasada de la suite contra PostgreSQL, frontend compilado, integración de navegador y arranque de contenedores. Cualquier verificación que no pueda ejecutarse en la estación debe anotarse como pendiente con el motivo y el comando para completarla.

La promoción de QA a PROD añade revisión humana, respaldo y comprobación de los mismos digests; está descrita en [aceptación](acceptance.md).

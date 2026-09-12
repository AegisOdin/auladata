# Despliegue de AulaData

Los archivos preparan el despliegue; no afirman que QA, PROD, DNS, certificados o runners estén provisionados. La única dirección de app confirmada es `dev-app01 = 10.10.30.10`. PostgreSQL vive en una VM diferente por ambiente en el laboratorio.

## Desarrollo local con Docker

Desde la raíz del repositorio, copia `.env.example` a `.env`, completa contraseñas propias y un `JWT_SECRET` aleatorio de al menos 32 caracteres. Un generador local es `python -c "import secrets; print(secrets.token_hex(32))"`; evita incluir su resultado en capturas. Si la contraseña PostgreSQL tiene caracteres especiales, codifícalos para el componente de contraseña de `DATABASE_URL`.

```bash
cp .env.example .env
# Editar .env antes de continuar. SEED_DEMO=true agrega aulas sintéticas.
docker compose --env-file .env -f deploy/compose.local.yml build
docker compose --env-file .env -f deploy/compose.local.yml up -d postgres --wait
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend alembic upgrade head
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend python -m app.seed
docker compose --env-file .env -f deploy/compose.local.yml up -d --wait
```

Abre `http://localhost:3000`. La API escucha en `127.0.0.1:8000`; PostgreSQL no publica puerto del host. El volumen `postgres-local` conserva los datos entre reinicios. `down` detiene los contenedores; añadir `--volumes` elimina los datos y se reserva para bases descartables.

Los usuarios iniciales reciben `ADMIN_INITIAL_EMAIL`, `ADMIN_INITIAL_PASSWORD`, `VIEWER_INITIAL_EMAIL`, `VIEWER_INITIAL_PASSWORD`. El seed es idempotente; no cambia contraseñas de usuarios existentes. Usa `COOKIE_SECURE=false` solamente para el HTTP local/DEV. QA y PROD requieren HTTPS y cookies seguras.

Pruebas PostgreSQL independientes:

```bash
export TEST_DB_PASSWORD="$(python -c 'import secrets; print(secrets.token_hex(24))')"
export TEST_DB_PORT=5433
docker compose -f deploy/compose.test.yml up -d --wait
export TEST_DATABASE_URL="postgresql+psycopg://auladata_test:${TEST_DB_PASSWORD}@127.0.0.1:${TEST_DB_PORT}/auladata_test"
pytest tests/backend -v
docker compose -f deploy/compose.test.yml down
```

`compose.test.yml` usa tmpfs, una base cuyo nombre contiene `test` y puerto loopback configurable. Si Windows reserva el puerto, usa otro, por ejemplo `TEST_DB_PORT=15432`. Nunca apuntes tests a la base de desarrollo o producción.

## Preparar cada VM app Ubuntu

Requiere Docker Engine + Compose v2 con `--wait`, Bash, Python 3.11 o posterior y `flock` (util-linux). El usuario de despliegue debe poder usar Docker y escribir su directorio de estado y respaldos. No hace falta Node, pnpm o pip en la VM. El backend usa un worker; el compose limita cada app a 512 MiB y una CPU.

```bash
sudo install -d -m 750 /etc/auladata
sudo install -d -o "$USER" -m 700 /var/lib/auladata/dev /var/backups/auladata/dev
sudo install -o "$USER" -m 600 deploy/env/dev.env.example /etc/auladata/dev.env
# Editar /etc/auladata/dev.env con un editor; no guardar el archivo en Git.
```

Repite para QA/PROD usando sus ejemplos y directorios. Cada archivo debe apuntar a una **instancia PostgreSQL independiente**, con usuario y contraseña propios y permisos para migraciones. Completa `APP_BIND_ADDRESS` con la IP real de la VM y `DATABASE_URL` con su servidor DB externo. Configura `BASE_URL` como la URL pública del ambiente; los smoke tests deben atravesar el mismo proxy que el navegador. `CORS_ORIGINS` es CSV de orígenes explícitos, sin comodines, y debe incluir el origen público de `BASE_URL` incluso usando same-origin: la protección CSRF valida el encabezado `Origin`. Los smoke tests envían ese mismo origen.

Los archivos runtime son configuración Bash de confianza del operador: usa asignaciones `NOMBRE=valor`, comillas para caracteres especiales y permisos `600`. No se descargan como artefactos. Las variables iniciales del seed se pueden quitar después de crear las cuentas. `SMOKE_EMAIL` y `SMOKE_PASSWORD` deben corresponder a una cuenta VIEWER activa; no se pasan por argumentos de procesos ni se imprimen. Usa una contraseña diferente por ambiente.

Configura el firewall para permitir únicamente proxy → app `3000/8000` y app → su DB `5432`. El compose de laboratorio no crea PostgreSQL. `deploy/nginx/auladata.conf.example` se instala en el proxy externo; sustituye los marcadores y ejecuta `nginx -t` antes de recargar. Conserva `/api/`, `/health` y `/ready` en el backend, y `/` en Next. Ajusta certificados y DNS después de provisionarlos. `/docs`, `/redoc` y `/openapi.json` se consultan por el backend DEV o se agregan explícitamente al proxy DEV si se necesitan.

## Artefacto inmutable

CI construye backend y frontend en commits de `develop` o `release/*`, los publica en GHCR con tag del SHA completo y entrega el artefacto `release-manifest`. Los pushes a `main` y tags ejecutan validaciones, sin recompilar imágenes. **Conserva el manifiesto aprobado en QA**: es la autoridad de promoción, aunque exista otro build del mismo commit. Un tag Docker por SHA identifica el build, pero el digest es el identificador inmutable.

El manifiesto `release.env` contiene exactamente cuatro líneas:

```text
BACKEND_IMAGE=ghcr.io/OWNER/REPOSITORY-backend@sha256:DIGEST_DE_64_HEXADECIMALES
FRONTEND_IMAGE=ghcr.io/OWNER/REPOSITORY-frontend@sha256:DIGEST_DE_64_HEXADECIMALES
GIT_COMMIT=SHA_GIT_COMPLETO_DE_40_HEXADECIMALES
APP_VERSION=v1.0.0
```

Los ejemplos en mayúscula son marcadores y deben sustituirse. `release.py` rechaza tags mutables, claves adicionales, duplicadas y contenido ejecutable. Para descargar un build real, usa `gh run download ID_DEL_RUN --name release-manifest --dir release`. Guarda una copia fuera de los artefactos temporales de GitHub (retención configurada: 90 días).

`APP_ENV`, versión y SHA se inyectan **en runtime** al backend. Next obtiene estos datos por `/health`; la misma imagen usa `API_INTERNAL_URL=http://backend:8000` en todos los ambientes. No necesita `NEXT_PUBLIC_*` específico de DEV/QA/PROD.

## Scripts manuales en las VM

Después de autenticar Docker en GHCR para descargar las imágenes privadas, copia el mismo manifiesto a cada VM. No incluyas el token de registro en argumentos; usa `docker login ghcr.io --username TU_USUARIO --password-stdin` desde un gestor o entrada segura.

```bash
# Primer despliegue de cada base: habilitar creación inicial de cuentas.
SEED_USERS=true ENV_FILE=/etc/auladata/dev.env bash deploy/scripts/deploy-dev.sh release/release.env

# Promociones siguientes: imágenes idénticas; cambia la configuración runtime.
ENV_FILE=/etc/auladata/qa.env bash deploy/scripts/deploy-qa.sh release/release.env
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/deploy-prod.sh release/release.env
```

Para la primera ejecución de QA/PROD añade también `SEED_USERS=true` y completa las credenciales iniciales en su archivo privado. Alternativamente guarda el manifiesto como `deploy/releases/SHA_COMPLETO.env` y usa `IMAGE_TAG=SHA_COMPLETO bash deploy/scripts/deploy-dev.sh`. `IMAGE_TAG` selecciona un manifiesto local validado, no un tag Docker mutable. `RELEASE_FILE` acepta otra ruta.

El script bloquea despliegues concurrentes, valida configuración e imágenes, descarga, guarda el manifiesto anterior, respalda antes de migrar PROD, ejecuta `alembic upgrade head`, aplica seed si se solicita, arranca con `--no-build` y verifica salud, disponibilidad PostgreSQL, metadata, frontend, login, sesión, listado y logout. Los resultados nunca incluyen contraseña, token ni cookies. Un fallo detiene el flujo y deja el manifiesto previo disponible; no marca el candidato como desplegado.

Para pruebas manuales sin desplegar, carga primero las variables de confianza:

```bash
set -a
source /etc/auladata/dev.env
set +a
bash deploy/scripts/healthcheck.sh
bash deploy/scripts/smoke-test.sh
```

Si exportas también `GIT_COMMIT` y `APP_VERSION` desde el manifiesto, los scripts exigen esos valores exactos. Un `health` correcto solo prueba liveness; `/ready` comprueba PostgreSQL por separado.

## Rollback y respaldo

```bash
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/rollback.sh PROD
# O seleccionar explícitamente otro manifiesto ya conocido:
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/rollback.sh PROD /ruta/release-anterior.env
```

El rollback usa el manifiesto anterior conservado en `STATE_DIR/rollback.env`, descarga esas imágenes, arranca y repite smoke tests. No ejecuta downgrade ni restaura datos automáticamente. Las migraciones futuras deben ser compatibles con la versión anterior; si son destructivas, diseña y ensaya restauración antes de autorizar el despliegue. El primer despliegue no tiene imagen anterior.

PROD exige HTTPS, `COOKIE_SECURE=true` y un respaldo completo exitoso antes de migrar. `backup.py` usa `pg_dump --format=custom` de `BACKUP_IMAGE` (predeterminado PostgreSQL 17), pasando la conexión por variables `PG*`, sin contraseñas en la línea de comandos. Usa la misma versión mayor que el servidor DB. Verifica el índice mediante `pg_restore --list`, guarda archivos con permisos restrictivos y extensión `.dump`; los fallos eliminan el archivo parcial y abortan. `BACKUP_DIR` debe tener espacio suficiente. El contenedor usa red `host` en Ubuntu para alcanzar la VM DB; para ensayos con el compose local puedes establecer `BACKUP_DOCKER_NETWORK=auladata-local_default`. Copia respaldos a almacenamiento externo y prueba restauraciones en una base aislada; crear un dump no demuestra por sí solo que se haya ensayado una restauración. Si usas TLS con certificados de cliente/CA propios, adapta el montaje de certificados para el contenedor de respaldo antes de habilitar PROD.

## GitHub Actions y aprobaciones

1. Publica el repositorio y concede al workflow permiso de escritura en GHCR. CI valida Ruff/formato, configuración, Alembic, pytest con PostgreSQL aislado, scripts de despliegue, ESLint, TypeScript, build Next, `pip-audit`, `pnpm audit` y una búsqueda básica de secretos. Esta última no sustituye un escáner completo.
2. Configura environments `DEV`, `QA`, `PROD`; **en PROD agrega required reviewers y prevent self-review**. La disponibilidad de estas protecciones depende del plan/visibilidad del repositorio. Declarar `environment: PROD` en YAML por sí solo no configura revisores. Usa aprobación QA también si la práctica la requiere.
3. Prepara runners Linux de confianza con etiquetas `auladata-dev`, `auladata-qa`, `auladata-prod` en las respectivas VM app. Deben tener Docker autenticado en GHCR, `/etc/auladata/ENV.env` y permisos en sus rutas de estado/respaldo. Restringe los runners a este repositorio y sus ramas autorizadas; CI de PRs usa runners hospedados, nunca estas VM.
4. Ejecuta **Promote the same release DEV to QA to PROD** indicando `ci_run_id`. Valida que el run CI pasó, que es del repositorio y workflow correctos y que el SHA del manifiesto coincide. DEV se despliega antes que QA. Ambos consumen los mismos digests.
5. Para continuar hasta PROD, activa `deploy_production` y proporciona un tag existente `vX.Y.Z` que apunte al SHA exacto del artefacto. El workflow verifica el tag y exige aprobación del environment PROD si está configurada. Cambia solo la versión runtime y promueve el mismo manifiesto usado por DEV y QA en esa ejecución. No contiene pasos de build en despliegue.

Mantén `main` y el tag de release apuntando al commit aprobado cuando completes la estrategia Git. Si una fusión genera un commit diferente, su SHA no cumple la comprobación del artefacto: usa fast-forward cuando sea posible o valida un nuevo candidato antes de promover.

Referencias oficiales: [Compose services](https://docs.docker.com/reference/compose-file/services/), [artefactos entre workflows](https://docs.github.com/en/actions/tutorials/store-and-share-data), [protecciones de environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

## Relojes y sesiones JWT

Mantén el reloj UTC sincronizado en hosts, VM y proxy mediante el servicio de hora de la infraestructura. Una sesión recién creada puede dar 401 si el reloj salta y el JWT parece vencido o emitido en el futuro. Comprueba `date -u`, `timedatectl status` y la fecha HTTP; no amplíes la vida del JWT ni su tolerancia para ocultar desfases de horas. El smoke informa diferencias grandes observadas al recibir 401, además de recordar revisar HTTPS/cookies.

En Docker Desktop/WSL2 compara `Get-Date -AsUTC` de PowerShell con `wsl -d docker-desktop -- date -u`. Un reinicio de Docker Desktop conserva volúmenes y puede recuperarse con `docker compose ... up -d --wait`. Un apagado global de WSL afecta otras distribuciones y procesos: evalúa su impacto antes de hacerlo. No cambies la hora ni zona horaria de Windows como parte del despliegue de la app. Referencias: [reinicio de Docker Desktop](https://docs.docker.com/reference/cli/docker/desktop/restart/) e [incidencias de desfase WSL documentadas por Microsoft](https://github.com/microsoft/WSL/issues/10006).

# AulaData

Aplicación de gestión de aulas para la materia Infraestructura de Servicios. Incluye autenticación real, roles ADMIN/VIEWER, CRUD con baja lógica, PostgreSQL, migraciones, pruebas y despliegue mediante contenedores. El frontend muestra ambiente, versión y commit obtenidos del backend en runtime.

El código está preparado para el laboratorio Proxmox descrito por el usuario. La publicación remota, revisión humana del PR y despliegues DEV/QA/PROD requieren ejecución y evidencia en ese laboratorio. Consultar [aceptación y evidencias](docs/acceptance.md).

La [guía de entrega y defensa](docs/entrega.md) reúne el árbol de archivos, comandos de arranque, pruebas, despliegue en dev-app01 y evidencias pendientes.

## Arranque local con Docker

Requisitos: Git, Docker Engine/Docker Desktop con contenedores Linux y Docker Compose v2. Ejecutar desde la carpeta `auladata`.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
chmod 600 .env
```

Editar `.env` y completar `POSTGRES_PASSWORD`, `JWT_SECRET`, `ADMIN_INITIAL_PASSWORD` y `VIEWER_INITIAL_PASSWORD`. Usar secretos nuevos: JWT de al menos 32 caracteres y contraseñas seed de 12 a 128 caracteres. Conservar `COOKIE_SECURE=false` solo para este entorno HTTP local. Para incluir las seis aulas sintéticas, establecer `SEED_DEMO=true`.

Para generar un JWT aleatorio sin usar una clave incluida en el repositorio:

```powershell
$randomBytes = New-Object byte[] 48
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$generator.GetBytes($randomBytes)
[Convert]::ToBase64String($randomBytes)
$generator.Dispose()
```

En Linux puede usarse `openssl rand -hex 48`. Guardar el resultado directamente en el archivo privado de configuración. La contraseña de PostgreSQL en `DATABASE_URL` debe estar codificada como componente URL si contiene caracteres especiales; una contraseña hexadecimal aleatoria simplifica el ejemplo local.

Los siguientes comandos funcionan en PowerShell y Bash:

```bash
docker compose --env-file .env -f deploy/compose.local.yml config --quiet
docker compose --env-file .env -f deploy/compose.local.yml build
docker compose --env-file .env -f deploy/compose.local.yml up -d postgres
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend alembic upgrade head
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend python -m app.seed
docker compose --env-file .env -f deploy/compose.local.yml up -d
docker compose --env-file .env -f deploy/compose.local.yml ps
```

Abrir [AulaData local](http://localhost:3000), [Swagger](http://localhost:8000/docs), [salud](http://localhost:8000/health) y [readiness](http://localhost:8000/ready). Entrar con `ADMIN_INITIAL_EMAIL` o `VIEWER_INITIAL_EMAIL` y la contraseña que se haya configurado. No se incluye una contraseña universal.

El seed es idempotente: no duplica usuarios ni aulas existentes. Cambiar una contraseña en `.env` y volver a ejecutar el seed no restablece la contraseña de un usuario existente. Las aulas sintéticas van de ISC-A01 a ISC-A06; no son datos reales. Si no se configura ni correo ni contraseña de un rol, se omite; si se configura solo uno, el seed falla para evitar una cuenta incompleta.

PostgreSQL local se conserva en un volumen y no publica `5432` en el host. Los puertos de aplicación se publican únicamente en loopback. Para detener conservando los datos:

```bash
docker compose --env-file .env -f deploy/compose.local.yml down
```

## Desarrollo sin contenedores de aplicación

Requisitos adicionales: Python 3.13, Node.js 22, pnpm 10.27.0 y PostgreSQL. Python 3.13 es la versión utilizada por CI, Docker y las dependencias verificadas. La versión de pnpm se declara en `app/frontend/package.json`. La base de desarrollo debe ser independiente de QA, PROD y tests.

Si PostgreSQL ya está instalado, crear un rol y una base local desde `psql` con una cuenta administradora. `\password` solicita el secreto de forma interactiva:

```sql
CREATE ROLE auladata_dev LOGIN;
\password auladata_dev
CREATE DATABASE auladata_dev OWNER auladata_dev;
```

En `.env`, ajustar `DATABASE_URL` a `postgresql+psycopg://auladata_dev:<contraseña-codificada>@127.0.0.1:5432/auladata_dev`. La forma con `@postgres:5432` del ejemplo sirve dentro de la red Docker; la instalación nativa utiliza la dirección real del servidor.

PowerShell, desde la raíz del repositorio:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/backend/requirements.lock
.\.venv\Scripts\python.exe -m pip install -c app/backend/requirements-dev.lock -e './app/backend[dev]'
.\.venv\Scripts\python.exe -m app.config
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Linux/macOS:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.lock
.venv/bin/python -m pip install -c app/backend/requirements-dev.lock -e './app/backend[dev]'
.venv/bin/python -m app.config
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

En otra terminal crear `app/frontend/.env.local` con:

```dotenv
API_INTERNAL_URL=http://127.0.0.1:8000
```

Después ejecutar:

```bash
cd app/frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

El navegador consume `/api/v1/*`; `API_INTERNAL_URL` solo lo usa el servidor Next.js. No se necesitan secretos ni nombres de ambiente en `NEXT_PUBLIC_*`.

## Variables de configuración

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Obligatoria. Conexión `postgresql+psycopg://...` del ambiente. |
| `JWT_SECRET` | Obligatoria. Mínimo 32 caracteres aleatorios; distinta por ambiente. |
| `APP_ENV` | `DEV`, `QA`, `PROD`; `TEST` se reserva para pruebas. |
| `APP_VERSION`, `GIT_COMMIT` | Metadatos de release mostrados por `/health`. |
| `JWT_ALGORITHM` | `HS256`. |
| `JWT_EXPIRES_MINUTES` | Duración de sesión, 60 por defecto. |
| `COOKIE_SECURE` | `true` por defecto en backend. QA/PROD lo exigen; `false` solo para DEV HTTP. |
| `CORS_ORIGINS` | Orígenes completos, explícitos, separados por comas; sin comodines. |
| `ADMIN_INITIAL_EMAIL`, `ADMIN_INITIAL_PASSWORD` | Credenciales para crear el administrador en el seed. |
| `VIEWER_INITIAL_EMAIL`, `VIEWER_INITIAL_PASSWORD` | Credenciales para crear el observador en el seed. |
| `ADMIN_INITIAL_NAME`, `VIEWER_INITIAL_NAME` | Nombres opcionales de usuarios seed. |
| `SEED_DEMO` | `true` incluye seis aulas sintéticas; `false` por defecto. |
| `LOG_LEVEL` | Nivel de logs, `INFO` por defecto. |
| `API_INTERNAL_URL` | Dirección de FastAPI accesible desde Next.js en runtime. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Inicialización del PostgreSQL de Compose local. |
| `BACKEND_IMAGE`, `FRONTEND_IMAGE` | Referencias inmutables por digest en Compose de laboratorio. |
| `APP_BIND_ADDRESS` | IP de escucha del host; loopback por defecto, IP real de app VM en laboratorio. |

El backend lee `.env` desde el directorio de ejecución. Ejecutar los comandos nativos desde la raíz. Compose recibe el archivo explícitamente mediante `--env-file`; las variables ya exportadas en la terminal pueden tener precedencia. [Interpolación de variables de Docker Compose](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

## Pruebas y validaciones

Desde la raíz con el entorno Python instalado:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app/backend migrations tests
.\.venv\Scripts\python.exe -m ruff format --check app/backend migrations tests
```

En Linux sustituir `.\.venv\Scripts\python.exe` por `.venv/bin/python`. Para el frontend, desde `app/frontend`:

```bash
pnpm lint
pnpm typecheck
pnpm build
```

Ver [pruebas](docs/testing.md) para la base aislada, integración PostgreSQL y cobertura; los resultados realmente ejecutados se conservan en [evidencias](docs/evidence/README.md).

## API, laboratorio y operación

Endpoints de autenticación: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`. Aulas: `GET/POST /api/v1/classrooms`, `GET/PUT/PATCH/DELETE /api/v1/classrooms/{id}`. Salud: `GET /health` y `GET /ready`. Las mutaciones requieren `X-Requested-With: AulaData`. Consultar [contrato API](docs/api.md).

Para `dev-app01=10.10.30.10`, usar `deploy/compose.yml`, PostgreSQL en una VM separada y los scripts de [despliegue](deploy/README.md). Las IP de QA, PROD, bases y proxy siguen siendo propuestas. El procedimiento de preparación y promoción está en [despliegue de laboratorio](docs/deployment.md); respaldo, logs y rollback en [operación](docs/operations.md).

La estrategia es `feature/gestion-aulas` → PR revisado → `develop`/DEV → `release/1.0.0`/QA → `main` → `v1.0.0`/PROD. Se promueven las mismas imágenes por digest. Ver [flujo Git](docs/git-workflow.md) y [changelog](CHANGELOG.md).

## Estructura

```text
auladata/
├── app/
│   ├── backend/              # FastAPI, SQLAlchemy, schemas, auth, seed
│   └── frontend/             # Next.js App Router, TypeScript, Tailwind
├── migrations/              # Revisiones Alembic
├── tests/backend/           # Pruebas HTTP y persistencia aisladas
├── deploy/
│   ├── compose.local.yml     # PostgreSQL + backend + frontend locales
│   ├── compose.test.yml      # PostgreSQL de pruebas efímero
│   ├── compose.yml           # App VM: backend + frontend
│   ├── env/                 # Plantillas sin secretos
│   └── scripts/             # Deploy, smoke, respaldo y rollback
├── docs/                    # Arquitectura, API, operación, pruebas, evidencias
├── .github/workflows/       # CI y promoción configurable
├── .env.example
├── alembic.ini
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

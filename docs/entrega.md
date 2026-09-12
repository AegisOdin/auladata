# Entrega y defensa de AulaData

AulaData implementa gestión de aulas con FastAPI, Next.js y PostgreSQL. Un ADMIN crea, consulta, edita y da de baja; un VIEWER consulta. La baja conserva el registro y la API controla los permisos. La sesión usa JWT en cookie HttpOnly; ambiente, versión y commit se muestran desde `/health` en runtime.

Esta guía concentra la entrega. Los detalles se encuentran en [arquitectura](architecture.md), [API](api.md), [pruebas](testing.md), [despliegue](deployment.md), [operación](operations.md) y [Git](git-workflow.md).

## Qué está comprobado

| Verificación local | Resultado registrado |
| --- | --- |
| Backend sobre PostgreSQL 17 | 69 pruebas aprobadas, sin fallos ni omisiones. |
| Backend sobre SQLite aislado | 69 pruebas aprobadas, sin fallos ni omisiones. |
| Auditoría de dependencias runtime backend | 0 vulnerabilidades conocidas reportadas por pip-audit. |
| Construcción y servicios Docker | Ambas imágenes construidas; PostgreSQL, backend y frontend saludables. |
| Persistencia PostgreSQL | Migración Alembic, seed de 2 usuarios y 6 aulas, `/health` y `/ready` correctos. |
| Respaldo y restauración | Dump custom validado; restauración en base temporal comprobada con 2 usuarios y 6 aulas. |
| Automatización | 7 pruebas del manifiesto, sintaxis Bash, Ruff y actionlint aprobados; smoke completo aprobado. |
| Navegador | 5/5 escenarios E2E aprobados en 8,0 s sobre frontend Docker en modo producción, backend Docker y PostgreSQL 17. |

Los resultados están en [JUnit PostgreSQL](evidence/backend-postgres-junit.xml), [JUnit SQLite](evidence/backend-sqlite-junit.xml), [JUnit E2E](evidence/frontend-junit.xml) y [auditoría](evidence/backend-audit.json). El [inventario de evidencias](evidence/README.md) concentra capturas y el cierre de verificaciones. Los dumps y la configuración privada permanecen fuera de Git.

Estos ensayos son locales. Aún se deben acreditar el despliegue en las VM reales, PR/revisión humana, QA, PROD, rollback en laboratorio, HA, migración live de PROD y monitoreo. Una pantalla que diga `DEV`, `QA` o `PROD` por configuración local no demuestra promoción entre VM. `version=development` o `commit=unknown` tampoco acreditan el artefacto de una release.

## Arranque con Docker en Windows o Linux

Requiere Docker Engine/Desktop en modo Linux y Compose v2. Ejecutar desde `auladata/`; no iniciar simultáneamente la aplicación nativa y Docker sobre los mismos puertos.

Crear la configuración privada:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux
cp .env.example .env
chmod 600 .env
```

Editar `.env` antes de continuar:

| Variable | Valor que debe definir el operador |
| --- | --- |
| `POSTGRES_PASSWORD` | Secreto propio para PostgreSQL local. |
| `DATABASE_URL` | Conservar el host `postgres` dentro de Compose; usuario/base deben coincidir con `POSTGRES_USER` y `POSTGRES_DB`. |
| `JWT_SECRET` | Secreto aleatorio de al menos 32 caracteres. |
| `ADMIN_INITIAL_EMAIL` / `ADMIN_INITIAL_PASSWORD` | ADMIN a crear; el ejemplo de correo es `admin@example.com`. Contraseña propia de 12 a 128 caracteres. |
| `VIEWER_INITIAL_EMAIL` / `VIEWER_INITIAL_PASSWORD` | VIEWER a crear; el ejemplo de correo es `viewer@example.com`. Contraseña distinta, de 12 a 128 caracteres. |
| `SEED_DEMO` | `true` para las seis aulas sintéticas y la práctica E2E. |
| `COOKIE_SECURE` / `CORS_ORIGINS` | Local HTTP: `false` y `http://localhost:3000`. QA/PROD: cookies seguras y origen HTTPS real. |

`ADMIN_INITIAL_NAME` y `VIEWER_INITIAL_NAME` personalizan los nombres. El [README](../README.md#variables-de-configuración) detalla las demás variables y cómo generar secretos. Nunca publicar `.env`. Si se incluyen caracteres especiales en la contraseña de la URL PostgreSQL, codificarlos como componente URL.

Estos comandos funcionan tanto en PowerShell como en Bash:

```bash
docker compose --env-file .env -f deploy/compose.local.yml config --quiet
docker compose --env-file .env -f deploy/compose.local.yml build
docker compose --env-file .env -f deploy/compose.local.yml up -d postgres --wait
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend alembic upgrade head
docker compose --env-file .env -f deploy/compose.local.yml run --rm backend python -m app.seed
docker compose --env-file .env -f deploy/compose.local.yml up -d --wait
docker compose --env-file .env -f deploy/compose.local.yml ps
```

Abrir [login](http://localhost:3000/login), [Swagger](http://localhost:8000/docs), [health](http://localhost:8000/health) y [ready](http://localhost:8000/ready). Ingresar con las credenciales configuradas; no hay una contraseña predeterminada. El seed no duplica cuentas/aulas ni restablece contraseñas existentes.

Para detener conservando datos: `docker compose --env-file .env -f deploy/compose.local.yml down`. PostgreSQL local usa un volumen; no publica su puerto en el host.

## Arranque nativo en Windows o Linux

Requiere Python 3.13, PostgreSQL, Node.js 22 y pnpm 10.27.0. Crear el rol y la base de desarrollo como indica el [README](../README.md#desarrollo-sin-contenedores-de-aplicación). Cambiar en `.env` el host `postgres` por la dirección real accesible desde el host; para PostgreSQL instalado localmente es `127.0.0.1:5432`.

En PowerShell, desde la raíz:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/backend/requirements.lock
.\.venv\Scripts\python.exe -m pip install -c app/backend/requirements-dev.lock -e './app/backend[dev]'
.\.venv\Scripts\python.exe -m app.config
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

En Bash:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.lock
.venv/bin/python -m pip install -c app/backend/requirements-dev.lock -e './app/backend[dev]'
.venv/bin/python -m app.config
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Crear `app/frontend/.env.local` con `API_INTERNAL_URL=http://127.0.0.1:8000`. En otra terminal, tanto en Windows como en Linux:

```bash
cd app/frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

El frontend usa `/api/v1/` relativo al mismo origen. La URL interna solo la conoce Next.js en el servidor.

## Pruebas que debe poder repetir el equipo

Backend, desde la raíz en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m ruff check app/backend migrations tests deploy/scripts
.\.venv\Scripts\python.exe -m ruff format --check app/backend migrations tests deploy/scripts
```

En Linux, usar `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`. La pasada predeterminada es aislada con SQLite. Para PostgreSQL utilizar [los comandos de integración](testing.md#integración-con-postgresql-aislado): `compose.test.yml`, una contraseña temporal y `TEST_DATABASE_URL` hacia `auladata_test`. La fixture crea un esquema propio, aplica Alembic y lo elimina al terminar. Si Windows reserva `5433`, elegir otro `TEST_DB_PORT`, por ejemplo `15432`.

Frontend, desde `app/frontend`:

```bash
pnpm lint
pnpm typecheck
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

La suite E2E requiere API/frontend levantados y seed con aulas. Lee las credenciales del `.env` raíz; las variables `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`, `E2E_VIEWER_EMAIL` y `E2E_VIEWER_PASSWORD` permiten elegir otras cuentas de prueba. `E2E_BASE_URL` vale `http://localhost:3000` por defecto. Nunca apuntar la suite de mutaciones a PROD.

Para guardar capturas: en PowerShell establecer `$env:E2E_CAPTURE='1'` antes de `pnpm test:e2e`; en Bash usar `E2E_CAPTURE=1 pnpm test:e2e`. El reporte y las capturas van a `docs/evidence/`. Consultar [navegador y capturas](testing.md#navegador-y-capturas) para los nombres y la interpretación del resultado.

## Endpoints para demostrar

| Método | Ruta | Acceso |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Credenciales JSON; crea cookie. |
| POST | `/api/v1/auth/logout` | Borra cookie. |
| GET | `/api/v1/auth/me` | Usuario autenticado. |
| GET | `/api/v1/classrooms` | ADMIN/VIEWER; búsqueda, filtros y paginación. |
| GET | `/api/v1/classrooms/{id}` | ADMIN/VIEWER. |
| POST | `/api/v1/classrooms` | ADMIN; creación 201. |
| PUT/PATCH | `/api/v1/classrooms/{id}` | ADMIN; edición completa/parcial. |
| DELETE | `/api/v1/classrooms/{id}` | ADMIN; baja lógica 204. |
| GET | `/health` | Liveness, ambiente, versión y commit. |
| GET | `/ready` | Conexión PostgreSQL, 200 o 503. |

Todas las mutaciones requieren `X-Requested-With: AulaData`; el origen enviado debe estar permitido. Demostrar 401 sin sesión, 403 para mutaciones VIEWER, 409 por clave duplicada y 422 con capacidad inválida. Ejemplos ejecutables y esquemas en [API](api.md).

## Llevarlo a dev-app01 y promoverlo

`dev-app01=10.10.30.10` es la app VM confirmada por el contexto. Las direcciones de bases, QA, PROD y proxy siguen siendo propuestas. Confirmarlas antes de completar las plantillas. Cada ambiente requiere su propia instancia PostgreSQL y sus credenciales.

1. Copiar/clonar el repositorio en la app VM e instalar Docker, Compose v2, Bash, Python 3.11+ y `flock`.
2. Crear `/etc/auladata/dev.env` desde `deploy/env/dev.env.example`, con permisos privados y conexión a la base DEV real. Preparar directorios de estado/respaldo y la conectividad como indica [despliegue](deployment.md#configurar-dev-app01).
3. Publicar las imágenes del SHA validado y obtener `release.env` con referencias por digest. Autenticar Docker en el registro si es privado.
4. Ejecutar desde la raíz en la VM:

```bash
SEED_USERS=true ENV_FILE=/etc/auladata/dev.env bash deploy/scripts/deploy-dev.sh release.env
```

Para QA y PROD, usar el mismo manifiesto aprobado y archivos privados independientes:

```bash
ENV_FILE=/etc/auladata/qa.env bash deploy/scripts/deploy-qa.sh release.env
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/deploy-prod.sh release.env
```

En la primera instalación de cada base añadir `SEED_USERS=true`. QA/PROD requieren HTTPS y `COOKIE_SECURE=true`. PROD se ejecuta tras la aprobación real y el script exige respaldo correcto antes de migrar. Los comandos detallados, GitHub environments/runners y las restricciones de promoción están en [deploy/README.md](../deploy/README.md).

El rollback utiliza imágenes anteriores y mantiene el esquema de la base:

```bash
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/rollback.sh PROD
```

Solo aplicarlo si la versión anterior es compatible con el esquema actual. La restauración de datos es una operación separada descrita en [operación](operations.md).

## Guion breve para la defensa

1. Mostrar el diagrama: navegador → proxy/Next → FastAPI → PostgreSQL del ambiente.
2. Ingresar como ADMIN, crear un aula sintética, filtrar, editar y recargar para mostrar persistencia.
3. Dar de baja y mostrar que la fila permanece con `deleted_at` mientras desaparece de la consulta ordinaria.
4. Ingresar como VIEWER y mostrar el 403 de una mutación HTTP, además de la ausencia de controles administrativos.
5. Mostrar pytest, build, revisión Alembic, `/health`, `/ready` y los metadatos visibles en la UI.
6. Explicar que el manifiesto fija dos digests y un SHA; QA y PROD reciben esas mismas imágenes y bases distintas.
7. Mostrar el respaldo y una restauración aislada, y explicar la diferencia entre rollback de aplicación y recuperación de datos.

Los commits utilizan las identidades autorizadas `AegisOdin <odingarra@gmail.com>` y `JuanPaGargoo <juanpablogargoo@gmail.com>`, con mayoría de AegisOdin. Consultar el conteo vigente con `git shortlog -sne HEAD` y el detalle con `git log --oneline --decorate --graph --all`. La rama de trabajo es `feature/gestion-aulas`; la URL del remoto sigue pendiente de proporcionar por el usuario. La autoría Git no acredita revisión humana del PR.

## Capturas y pruebas pendientes de infraestructura

- [ ] Publicar el repositorio y guardar enlace del PR `feature/gestion-aulas` → `develop` y revisión del otro integrante.
- [ ] DEV real: VM/IP, contenedores, login/CRUD, Alembic y `/health` con SHA desplegado.
- [ ] QA real: manifiesto/digests, pruebas, UI con ambiente QA y aprobación documentada.
- [ ] PROD real: mismo SHA/digests, tag `v1.0.0`, respaldo previo, `/health`, `/ready` y UI.
- [ ] Rollback controlado en laboratorio con manifiesto anterior y comprobación de datos.
- [ ] Restauración PostgreSQL en el laboratorio y validación de la aplicación restaurada.
- [ ] Migración live de la app VM PROD: log, tiempos, conectividad y continuidad del servicio.
- [ ] Falla de nodo/HA: evento, reubicación, recuperación y tiempos medidos.
- [ ] Monitoreo: señales de disponibilidad, alertas y recuperación.

La migración live previa de DEV descrita por el usuario no reemplaza estas evidencias nuevas. Consultar [aceptación](acceptance.md) para registrar cada prueba sin atribuirle un resultado no observado.

## Hora y sesiones del laboratorio

Durante el ensayo local se detectó un desfase intermitente: el reloj de Docker/WSL vuelve a quedar aproximadamente seis horas detrás de Windows incluso después de reiniciar y ajustar UTC manualmente. Las últimas 160 solicitudes autenticadas contra Docker y la corrida E2E fueron correctas, pero eso no demuestra que la sincronización permanente del host esté resuelta. El diagnóstico queda en el [inventario de evidencias](evidence/README.md).

Un desfase puede hacer que un JWT parezca emitido en el futuro o ya vencido. La corrección debe realizarse en la sincronización de relojes; se mantiene la validación temporal del JWT sin ampliar su tolerancia (`leeway`) para ocultar el problema.

Antes de las pruebas de autenticación comparar hora UTC entre host, contenedor y VM:

```powershell
(Get-Date).ToUniversalTime().ToString('o')
w32tm /query /status
docker compose --env-file .env -f deploy/compose.local.yml exec -T backend python -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())'
```

Antes de las pruebas Proxmox, verificar los relojes de los nodos y de cada VM Ubuntu:

```bash
date -u
timedatectl status
timedatectl show -p NTPSynchronized
```

Configurar y comprobar el servicio NTP del laboratorio en los nodos y VM. Volver a comparar UTC y repetir login/smoke después de un reinicio o migración para comprobar estabilidad, no solo una corrección momentánea. Una diferencia de zona horaria en la presentación no equivale a un desfase real: comparar siempre UTC.

## Árbol de archivos de la entrega

El árbol incluye código, configuración y documentación versionables. Omite `.git`, dependencias instaladas, `.runtime`, secretos, dumps y archivos generados de evidencia; estos últimos se consultan en [su inventario](evidence/README.md).

```text
auladata/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── promote.yml
│   └── actionlint.yaml
├── app/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   └── security.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   └── logging.py
│   │   │   ├── dependencies/
│   │   │   │   ├── __init__.py
│   │   │   │   └── auth.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── classroom.py
│   │   │   │   └── user.py
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   └── classrooms.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   └── classrooms.py
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   └── classroom.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── classrooms.py
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── main.py
│   │   │   └── seed.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── requirements-dev.lock
│   │   └── requirements.lock
│   └── frontend/
│       ├── app/
│       │   ├── (workspace)/
│       │   │   ├── aulas/
│       │   │   │   ├── [id]/
│       │   │   │   │   ├── editar/
│       │   │   │   │   │   └── page.tsx
│       │   │   │   │   └── page.tsx
│       │   │   │   ├── nueva/
│       │   │   │   │   └── page.tsx
│       │   │   │   └── page.tsx
│       │   │   └── layout.tsx
│       │   ├── api/
│       │   │   └── [...path]/
│       │   │       └── route.ts
│       │   ├── health/
│       │   │   └── route.ts
│       │   ├── login/
│       │   │   └── page.tsx
│       │   ├── ready/
│       │   │   └── route.ts
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   └── page.tsx
│       ├── components/
│       │   ├── app-shell.tsx
│       │   ├── auth-provider.tsx
│       │   ├── brand.tsx
│       │   ├── classroom-form.tsx
│       │   ├── classroom-loader.tsx
│       │   ├── delete-dialog.tsx
│       │   ├── environment.tsx
│       │   └── status-badge.tsx
│       ├── e2e/
│       │   └── auladata.spec.ts
│       ├── lib/
│       │   ├── api.ts
│       │   └── proxy.ts
│       ├── public/
│       │   └── icon.svg
│       ├── types/
│       │   └── index.ts
│       ├── .dockerignore
│       ├── Dockerfile
│       ├── eslint.config.mjs
│       ├── next-env.d.ts
│       ├── next.config.ts
│       ├── package.json
│       ├── playwright.config.ts
│       ├── pnpm-lock.yaml
│       ├── postcss.config.mjs
│       └── tsconfig.json
├── deploy/
│   ├── env/
│   │   ├── dev.env.example
│   │   ├── prod.env.example
│   │   └── qa.env.example
│   ├── nginx/
│   │   └── auladata.conf.example
│   ├── scripts/
│   │   ├── backup.py
│   │   ├── check-secrets.py
│   │   ├── common.sh
│   │   ├── deploy-dev.sh
│   │   ├── deploy-prod.sh
│   │   ├── deploy-qa.sh
│   │   ├── deploy.sh
│   │   ├── healthcheck.sh
│   │   ├── release.py
│   │   ├── rollback.sh
│   │   ├── smoke-test.sh
│   │   └── smoke.py
│   ├── tests/
│   │   └── test_release.py
│   ├── compose.local.yml
│   ├── compose.test.yml
│   ├── compose.yml
│   └── README.md
├── docs/
│   ├── evidence/
│   │   └── README.md
│   ├── acceptance.md
│   ├── api.md
│   ├── architecture.md
│   ├── deployment.md
│   ├── entrega.md
│   ├── git-workflow.md
│   ├── operations.md
│   └── testing.md
├── migrations/
│   ├── versions/
│   │   └── 20260912_0001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── tests/
│   └── backend/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_classrooms.py
│       └── test_configuration_seed.py
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── alembic.ini
├── CHANGELOG.md
├── pyproject.toml
└── README.md
```

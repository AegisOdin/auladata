# Despliegue DEV, QA y PROD

El repositorio entrega los contenedores y procedimientos. La existencia de `dev-app01=10.10.30.10` proviene del contexto del usuario; no se han aprovisionado desde estos archivos las demás VM, el firewall, certificados ni DNS.

## Antes del primer despliegue

1. Confirmar la IP real de la app VM y aprovisionar la VM PostgreSQL independiente del ambiente.
2. Instalar Docker Engine y Compose v2 en la app VM; Bash, Python 3 y `flock` ejecutan los scripts.
3. Crear rol y base PostgreSQL exclusivos, habilitar acceso desde la app VM y limitar `5432/TCP` mediante firewall y `pg_hba.conf`.
4. Configurar el proxy externo y HTTPS para QA/PROD. El backend exige `COOKIE_SECURE=true` allí.
5. Publicar las imágenes de un SHA validado en un registro accesible por la VM y conservar sus digests.
6. Copiar código/scripts de ese mismo SHA y crear el archivo privado del ambiente fuera del repositorio.

Las versiones y comandos concretos de contenedores están en [deploy/README.md](../deploy/README.md). El Compose de laboratorio contiene únicamente backend y frontend; no crea PostgreSQL.

## Configurar dev-app01

Desde una sesión SSH autorizada en `10.10.30.10`, con el repositorio ya copiado o clonado en la ubicación elegida:

```bash
sudo install -d -m 750 -o "$USER" /etc/auladata
sudo install -d -m 750 -o "$USER" /var/lib/auladata/dev
sudo install -d -m 700 -o "$USER" /var/backups/auladata/dev
install -m 600 deploy/env/dev.env.example /etc/auladata/dev.env
```

Editar `/etc/auladata/dev.env` con el host real de PostgreSQL, secretos nuevos, cuentas seed/smoke y origen accesible. La plantilla deja `DATABASE_URL` vacío porque `dev-db01=10.10.30.20` es una propuesta. Una vez provisionada esa dirección, el formato sería:

```dotenv
DATABASE_URL='postgresql+psycopg://auladata_dev:<contraseña-codificada>@10.10.30.20:5432/auladata_dev'
```

El texto entre `<...>` es un marcador y debe sustituirse. `APP_BIND_ADDRESS=10.10.30.10` permite que el proxy alcance los puertos de esa VM; limitar su acceso en firewall. Para acceso inicial directo por HTTP a DEV, la plantilla usa `BASE_URL=http://10.10.30.10:3000`, ese mismo `CORS_ORIGINS` y `COOKIE_SECURE=false`. Al habilitar HTTPS, cambiar los tres de forma coherente.

Los archivos del ambiente tienen sintaxis Bash confiable y los scripts los cargan con `source`; deben ser editados únicamente por el operador. Los manifiestos de imágenes, en cambio, se validan como datos antes de usarse.

## Manifiesto del artefacto

El archivo `release.env` contiene exactamente cuatro valores no secretos:

```dotenv
BACKEND_IMAGE=registro/propietario/auladata-backend@sha256:<digest-64-hex>
FRONTEND_IMAGE=registro/propietario/auladata-frontend@sha256:<digest-64-hex>
GIT_COMMIT=<sha-completo-40-hex>
APP_VERSION=1.0.0-rc.1
```

Los marcadores se sustituyen por los valores reales producidos por la construcción. El validador rechaza referencias sin digest, claves extra, SHA inválido o datos que pudieran ejecutarse como shell.

Primer despliegue de DEV, creando usuarios con variables del archivo privado:

```bash
ENV_FILE=/etc/auladata/dev.env SEED_USERS=true bash deploy/scripts/deploy-dev.sh release.env
```

El script descarga imágenes, aplica `alembic upgrade head`, ejecuta seed si se pide, levanta servicios y comprueba salud, readiness, metadatos, login y listado. No compila en la VM de 2 GB. El estado aceptado queda en `/var/lib/auladata/dev/current.env`; si falla una validación se conserva el diagnóstico y el manifiesto anterior para recuperación.

## Promoción

| Etapa | Código y artefactos | Configuración |
| --- | --- | --- |
| DEV | Commit integrado a `develop` después del PR | Base y secretos DEV |
| QA | Candidato `release/1.0.0`; conservar SHA y digests | Base y secretos QA, HTTPS |
| PROD | Exactamente el SHA y digests aprobados en QA | Base y secretos PROD, HTTPS y respaldo previo |

Crear las plantillas privadas QA/PROD como en DEV y completar las direcciones reales antes de ejecutar:

```bash
ENV_FILE=/etc/auladata/qa.env bash deploy/scripts/deploy-qa.sh release.env
ENV_FILE=/etc/auladata/prod.env bash deploy/scripts/deploy-prod.sh release.env
```

En el primer arranque de cada ambiente usar `SEED_USERS=true` o ejecutar el seed como operación explícita; configurar las credenciales de smoke para un usuario existente. PROD requiere aprobación humana, HTTPS y un respaldo correcto antes de aplicar migraciones. No reconstruir la imagen al promover ni reemplazar los digests del manifiesto aprobado.

Si el código cambia después de QA, es otro candidato: volver a validarlo. El historial Git, publicación del tag y registro de aprobación se detallan en [git-workflow.md](git-workflow.md).

## Reverse proxy y configuración runtime

Publicar el frontend por `/` hacia `:3000` y la API por `/api/v1/` hacia `:8000`, conservando la ruta. Enrutar `/health` y `/ready` a FastAPI. El proxy debe conservar `Host` y comunicar el esquema original de HTTPS. No reescribir el cookie path de sesión. La plantilla [Nginx](../deploy/nginx/auladata.conf.example) requiere sustituir hostname, dirección de app VM y rutas reales de certificados antes de usarla.

Los nombres previstos `dev.auladata.lab`, `qa.auladata.lab` y `auladata.lab` son configuración del laboratorio. Añadir el origen HTTPS efectivo a `CORS_ORIGINS`; no se incluye `/api` ni una ruta en un origen. Si se accede con puerto no estándar, el origen sí incluye ese puerto.

`API_INTERNAL_URL=http://backend:8000` funciona entre contenedores y no depende del nodo Proxmox. Los metadatos de ambiente, versión y commit los lee Next.js desde la API en runtime. Por eso el mismo frontend puede usarse en DEV, QA y PROD.

## CI/CD y limitaciones de ejecución

Los workflows en `.github/workflows/` definen las validaciones, pruebas, análisis y construcción. Los jobs que publican imágenes o despliegan requieren un remoto real, permisos de registro, ambientes GitHub y acceso al laboratorio. Revisar [deploy/README.md](../deploy/README.md) para variables, secretos y disparadores exactos.

Configurar protección de PROD en GitHub y registrar la aprobación. Declarar el ambiente en YAML no agrega automáticamente revisores. Los mecanismos disponibles varían según el plan y la visibilidad del repositorio. [Protección de ambientes en GitHub Actions](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

Conservar las salidas de CI, manifiesto, revisión Alembic, `/health`, smoke y capturas del ambiente. Marcar un despliegue como realizado únicamente después de completar esas verificaciones.

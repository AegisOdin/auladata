# API HTTP

La base es `/api/v1`. La API la implementa FastAPI; el navegador usa rutas relativas al origen de AulaData. En DEV y QA consultar `/docs`, `/redoc` y `/openapi.json` directamente en el puerto del backend; esas rutas se deshabilitan en PROD. Los esquemas generados son la referencia de campos y validaciones vigente.

## Sesión

El login recibe JSON y establece una cookie de sesión HttpOnly. La respuesta no contiene el JWT. En el cliente usar `credentials: "include"`; no copiar tokens a `localStorage`.

Todas las mutaciones, incluido login y logout, requieren:

```http
X-Requested-With: AulaData
Content-Type: application/json
```

El servidor rechaza un `Origin` enviado que no aparezca en `CORS_ORIGINS`. Para herramientas HTTP fuera del navegador, el encabezado `X-Requested-With` sigue siendo obligatorio. `Content-Type` aplica a cuerpos JSON; un DELETE sin cuerpo no lo necesita.

```http
POST /api/v1/auth/login
X-Requested-With: AulaData
Content-Type: application/json

{"email":"admin@example.com","password":"<contraseña configurada en el seed>"}
```

Respuesta 200:

```json
{
  "id": 1,
  "name": "Administrador",
  "email": "admin@example.com",
  "role": "ADMIN",
  "is_active": true
}
```

El nombre, correo e ID dependen del seed ejecutado. `/auth/me` entrega el mismo esquema público del usuario autenticado. Una cookie ausente, inválida o expirada produce 401. Un usuario sin permiso produce 403.

## Endpoints y permisos

| Método y ruta | Acceso | Resultado exitoso |
| --- | --- | --- |
| `POST /api/v1/auth/login` | Público + encabezado de mutación | 200, usuario y cookie |
| `POST /api/v1/auth/logout` | Encabezado de mutación | 204, elimina cookie |
| `GET /api/v1/auth/me` | Sesión activa | 200, usuario |
| `GET /api/v1/classrooms` | ADMIN, VIEWER | 200, listado paginado |
| `GET /api/v1/classrooms/{id}` | ADMIN, VIEWER | 200, aula |
| `POST /api/v1/classrooms` | ADMIN | 201, aula creada |
| `PATCH /api/v1/classrooms/{id}` | ADMIN | 200, aula actualizada |
| `PUT /api/v1/classrooms/{id}` | ADMIN | 200, reemplazo de los campos editables |
| `DELETE /api/v1/classrooms/{id}` | ADMIN | 204, baja lógica |
| `GET /health` | Público | 200, proceso y metadatos |
| `GET /ready` | Público | 200 si PostgreSQL responde; 503 si no |

## Aulas

Crear un aula:

```json
{
  "clave": "ISC-N01",
  "nombre": "Aula de Matemáticas",
  "edificio": "Edificio K",
  "capacidad": 30,
  "tipo": "TEORICA",
  "estado": "ACTIVA"
}
```

| Campo | Regla |
| --- | --- |
| `clave` | Obligatoria, única, máximo 20 caracteres; se recortan espacios externos y se normaliza a mayúsculas. |
| `nombre` | Obligatorio, máximo 100 caracteres. |
| `edificio` | Obligatorio, máximo 50 caracteres. |
| `capacidad` | Entero de 1 a 2.147.483.647; rechaza texto numérico, decimales y booleanos. |
| `tipo` | `LABORATORIO`, `TEORICA`, `MIXTA`. |
| `estado` | `ACTIVA`, `MANTENIMIENTO`, `INACTIVA`. |

Las respuestas incluyen `id`, los campos del aula, `created_at`, `updated_at` y `deleted_at`. Las fechas se serializan en ISO 8601. PATCH envía uno o más campos a modificar y rechaza valores nulos; PUT recibe el objeto completo. Se rechazan campos extra. Una clave duplicada devuelve 409 incluso si la fila anterior se dio de baja.

La baja conserva la fila, establece su fecha de baja y la marca inactiva. El listado y el detalle ordinarios dejan de mostrarla; una consulta por un ID inexistente o dado de baja devuelve 404.

Ejemplo de consulta:

```http
GET /api/v1/classrooms?search=ISC&estado=ACTIVA&tipo=LABORATORIO&page=1&page_size=20
```

Respuesta:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

`total` cuenta coincidencias antes de paginar. `page` comienza en 1; `page_size` admite de 1 a 100, con 20 por defecto; `search` admite hasta 100 caracteres. Los filtros se combinan; no se incluyen filas con `deleted_at` establecido.

## Salud

Ejemplo ilustrativo de `/health`:

```json
{
  "status": "ok",
  "service": "auladata-api",
  "environment": "DEV",
  "version": "development",
  "commit": "unknown"
}
```

Estos valores salen de `APP_ENV`, `APP_VERSION` y `GIT_COMMIT`. Para comprobar persistencia disponible utilizar `/ready`; un `/health` correcto por sí solo no garantiza acceso a PostgreSQL.

## Errores

| Código | Causa habitual |
| --- | --- |
| 401 | Credenciales incorrectas o sesión no válida. |
| 403 | VIEWER intenta mutar, falta encabezado de mutación u origen rechazado. |
| 404 | Aula inexistente o con baja lógica. |
| 409 | Clave ya registrada. |
| 422 | Campos, enum o parámetros de consulta inválidos. |
| 500/503 | Error interno o dependencia no disponible; consultar logs sin exponer secretos. |

Los errores de dominio usan `detail`; los de validación de FastAPI pueden usar una lista en `detail`. El frontend admite ambas formas.

## Comprobar desde PowerShell

Con la app local abierta en `http://localhost:3000`, estas instrucciones solicitan credenciales sin dejarlas escritas en el ejemplo:

```powershell
$credentials = Get-Credential -Message 'Usuario creado por el seed'
$payload = @{
  email = $credentials.UserName
  password = $credentials.GetNetworkCredential().Password
} | ConvertTo-Json
$headers = @{ 'X-Requested-With' = 'AulaData'; Origin = 'http://localhost:3000' }
Invoke-RestMethod -Uri 'http://localhost:3000/api/v1/auth/login' -Method Post -Headers $headers -ContentType 'application/json' -Body $payload -SessionVariable aulaSession
Invoke-RestMethod -Uri 'http://localhost:3000/api/v1/auth/me' -WebSession $aulaSession
Invoke-RestMethod -Uri 'http://localhost:3000/api/v1/classrooms?page=1&page_size=20' -WebSession $aulaSession
Invoke-RestMethod -Uri 'http://localhost:3000/api/v1/auth/logout' -Method Post -Headers $headers -WebSession $aulaSession
Remove-Variable payload, credentials, aulaSession
```

En HTTPS sustituir origen y URL por el dominio real. Usar el script de smoke documentado en [despliegue](../deploy/README.md) para repetir salud, login y consulta en Linux.

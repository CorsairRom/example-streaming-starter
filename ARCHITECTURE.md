# Arquitectura

Este documento explica cómo está armado el servicio, por qué está así y dónde tocar cuando haya que
cambiar algo. Está pensado para alguien que nunca trabajó con FastAPI.

## 1. Vista general

```text
                       ┌──────────────────────────────────────────┐
   Emisor   ──POST──►  │  FastAPI                                 │
   (cámara LIVE /      │                                          │
    DEFERRED)          │  api/routes/webhook.py                   │
                       │    ├─ require_api_key  ──► 401           │
                       │    └─ StreamEventBody  ──► 422           │
                       │           │                              │
                       │           ▼                              │
                       │  application/stream_events.py            │
                       │    └─ ack (log + "accepted")             │
                       └──────────────────────────────────────────┘

   Admin  ──HTTP──►  /admin  ──►  api/routes/admin.py
                                    ├─ sesión firmada (cookie)
                                    ├─ token CSRF
                                    └─ api_keys: create / rotate / revoke
                                            │
                                            ▼
                                    SQLite (tabla api_keys)
```

Dos caminos de entrada, una sola base de código:

1. **Webhook**: máquina a máquina, autenticado por `X-API-Key`.
2. **Panel**: persona a máquina, autenticado por usuario/contraseña + cookie de sesión.

### Alcance de esta entrega

Incluye el receptor del webhook, la validación de la API key, el panel de claves y esta documentación.
No persiste eventos ni deduplica: el handler registra el evento en el log y responde. Las mejoras
pendientes están en [BACKLOG.md](./BACKLOG.md).

## 2. Capas

La estructura separa dominio, aplicación e infraestructura, adaptada a FastAPI. La regla es simple:
**las dependencias apuntan hacia adentro**.

| Capa | Carpeta | Responsabilidad | Puede importar |
| --- | --- | --- | --- |
| Dominio | `src/app/domain/` | Entidades, errores de negocio, puertos (interfaces). | Nada del proyecto. |
| Aplicación | `src/app/application/` | Casos de uso. Orquesta dominio y puertos. | `domain`. |
| Infraestructura | `src/app/infrastructure/` | SQLAlchemy, hashing, repositorios concretos. | `domain`. |
| HTTP | `src/app/api/` | Rutas, dependencias, plantillas, manejo de errores. | `application`, `domain`, `container`. |
| Composición | `src/app/main.py`, `container.py`, `settings.py` | Une todo. | Todos. |

### Dominio

- `entities.py`: `StreamEvent`, `StreamState`, `ApiKeyRecord`, `StoredSecret`. Son `dataclass`
  inmutables, sin Pydantic ni SQLAlchemy. Así el negocio no depende del framework.
- `errors.py`: `AppError` y sus subclases. Cada subclase declara su `status_code` y su `code`, y el
  handler HTTP los traduce a JSON. Agregar un error nuevo es agregar una clase.
- `ports.py`: `ApiKeyRepository`, un `Protocol` con las operaciones de persistencia. La aplicación
  depende de esta interfaz, no de SQLAlchemy.

### Aplicación

- `api_keys.py`: `ApiKeyService`. Genera claves, las rota, las revoca y las autentica. No sabe qué es
  HTTP ni qué es SQL.
- `stream_events.py`: `StreamEventController.receive()`. En fase 1 solo registra en el log y confirma.
  Es el punto de entrada para la fase 2 (persistir, deduplicar, reenviar).

### Infraestructura

- `models.py`: tabla `api_keys` con SQLAlchemy 2.0 (`Mapped[...]`).
- `repositories.py`: implementación del puerto. Único lugar con SQL.
- `security.py`: generación y verificación de claves (`secrets`, `hashlib.scrypt`, `hmac`).
- `db.py`: engine, session factory y creación de esquema.

### HTTP

- `routes/webhook.py`: el contrato público. El modelo Pydantic `StreamEventBody` valida y normaliza.
- `routes/admin.py`: panel server-rendered con Jinja2. Sin JavaScript de build.
- `routes/health.py`: estado del servicio.
- `deps.py`: dependencias de FastAPI (contenedor, servicio, API key).
- `error_handlers.py`: traduce `AppError` y errores de validación a un JSON uniforme.
- `templates/`: HTML del panel. CSS embebido, sin CDN: funciona sin internet.

### Estructura de archivos

```text
.
├── src/app/
│   ├── api/              rutas HTTP, dependencias, handlers y plantillas del panel
│   ├── application/      casos de uso: API keys y eventos de streaming
│   ├── domain/           entidades, errores y puertos (sin FastAPI ni SQLAlchemy)
│   ├── infrastructure/   SQLAlchemy, hash de claves, repositorios
│   ├── container.py      composition root
│   ├── main.py           create_app() y app ASGI
│   └── settings.py       configuración con pydantic-settings
├── src/run.py            entrypoint: toma HOST y PORT de la configuración
├── tests/                contrato, API keys, panel y entrypoint
├── docs/                 contrato, catálogo de errores y ejemplos
├── Makefile
├── pyproject.toml
└── ruff.toml
```

## 3. Flujo de un webhook

1. El emisor hace `POST /webhooks/streams` con `X-API-Key`.
2. FastAPI resuelve `require_api_key` **antes** de tocar el body.
   - Sin header → `401 STREAM_API_KEY_MISSING`.
   - Prefijo desconocido, clave revocada o hash que no coincide → `401 STREAM_API_KEY_INVALID`.
3. El handler lee el body crudo y lo valida a mano con `StreamEventBody.model_validate_json`.
   - `state` se pasa a mayúsculas y debe ser `LIVE` o `DEFERRED`.
   - `datetime` debe traer zona horaria; se convierte a UTC.
   - `url` debe empezar con `wss://` y tener host.
   - Campos desconocidos se **ignoran** (para no romper si el emisor agrega campos).
   - Cualquier falla → `422 STREAM_PAYLOAD_INVALID` con el detalle por campo.
4. `StreamEventController.receive()` registra el evento en el log.
5. Recién entonces se actualiza `last_used_at` de la clave y se responde `200 {"status": "accepted"}`.

> **Por qué el body se lee a mano.** FastAPI parsea un parámetro de body *antes* de resolver las
> dependencias. Leer el body dentro del handler mantiene la autenticación como primer paso del request.
> Cubierto por `tests/test_contract.py`.

`last_used_at` significa "último evento **aceptado**", no "último intento": un request rechazado no
modifica la base.

### Por qué 200 y no 204

El requerimiento acepta `200` o `204`. Se elige `200` con un body mínimo porque, para un equipo que
recién empieza, ver `{"status":"accepted"}` confirma que el request llegó al código y no a un proxy.
Cambiar a `204` es una línea en `routes/webhook.py`.

## 4. Flujo del panel

1. `GET /admin/login` crea el token CSRF en la sesión y lo embebe en el formulario.
2. `POST /admin/login` valida CSRF, compara usuario y contraseña con `hmac.compare_digest`,
   limpia la sesión y marca `session["admin"] = True`.
3. `GET /admin` lista las claves. Si no hay sesión, redirige a `/admin/login` con `303`.
4. Crear / rotar / revocar son `POST` con CSRF obligatorio.
5. Crear y rotar muestran la clave completa una única vez (`key_created.html`).

La sesión es una cookie firmada por `SessionMiddleware` (itsdangerous), `HttpOnly`, `SameSite=Strict` y
con expiración de 8 horas.

## 5. Modelo de datos

```text
api_keys
├── id             INTEGER  PK
├── name           VARCHAR(120)   nombre visible ("produccion")
├── prefix         VARCHAR(32)    UNIQUE, INDEX  (10 hex, identifica sin revelar)
├── key_hash       VARCHAR(128)   scrypt(secret, salt) en hex
├── salt           VARCHAR(64)    salt por clave
├── created_at     DATETIME
├── last_used_at   DATETIME NULL
└── revoked_at     DATETIME NULL
```

No existe tabla de eventos en fase 1. Ver [BACKLOG.md](../BACKLOG.md).

## 6. Ciclo de vida de una API key

```text
crear ──► activa ──► rotar ──► activa (clave nueva, la anterior muere)
            │
            └──► revocar ──► revocada (irreversible)
```

- **Crear**: genera `cck_<prefix>_<secret>`, guarda hash y devuelve la clave completa una vez.
- **Rotar**: reemplaza prefijo, hash y salt en la misma fila. La clave anterior deja de funcionar
  inmediatamente. Es el mecanismo ante pérdida o sospecha de filtración.
- **Revocar**: marca `revoked_at`. La fila se conserva como historial; la clave ya no autentica.

Una clave revocada no se puede rotar: hay que crear una nueva. Esto evita "revivir" credenciales.

## 7. Formato de la API key

```text
cck_9aa3d10908_6f1c3a4d9e8b7a2c5d0e1f3a4b6c7d8e9f0a1b2c
 │   │          │
 │   │          └─ secret (48 hex = 192 bits de entropía) → se hashea
 │   └──────────── prefix (10 hex) → se guarda en claro para buscar
 └──────────────── marker fijo
```

La búsqueda es por `prefix` (índice único). Luego se verifica el `secret` contra el hash. Esto evita
recorrer toda la tabla.

## 8. Decisiones y trade-offs

| Decisión | Por qué | Costo |
| --- | --- | --- |
| SQLite | Cero instalación para un equipo sin backend. | Un solo proceso escritor; migrar a Postgres en producción real. |
| SQLAlchemy 2.0 sin Alembic | Menos piezas para entender. `create_all` crea la tabla. | Cambios de esquema requieren recrear la base (ver BACKLOG). |
| Hash `scrypt` de la stdlib | Sin dependencias extra y es un KDF de memoria dura. | ~50 ms por verificación; aceptable a este volumen. |
| Prefijo en claro + secreto hasheado | Permite buscar sin guardar la clave. | El prefijo visible no es secreto (por diseño). |
| Panel server-rendered + Jinja2 | Sin build de JS, sin CDN, funciona offline. | Menos interactivo; suficiente para CRUD de claves. |
| `extra="ignore"` en el payload | Si el emisor agrega un campo, la integración no se rompe. | Un campo mal escrito se ignora en silencio. |
| Body leído a mano en el handler | Garantiza `401` antes de `422` aunque el JSON esté roto. | Se pierde la validación automática de FastAPI; se rearma como `AppError`. |
| `last_used_at` solo en eventos aceptados | Un request rechazado no altera la base. | No refleja intentos fallidos (van al log). |
| `src/run.py` como entrypoint | `HOST` y `PORT` salen de `.env`: una sola fuente de verdad. | Hay que usar `make run` (o `python src/run.py`), no `uvicorn` a mano. |
| Sin persistencia de eventos | Fase 1 solo confirma la recepción. | No hay historial consultable; ver BACKLOG. |

## 9. Cómo extender

### Agregar un campo al payload

1. Agregar el campo a `StreamEventBody` en `src/app/api/routes/webhook.py`.
2. Agregar el campo a `StreamEvent` en `src/app/domain/entities.py`.
3. Pasarlo en la construcción del `StreamEvent`.
4. Agregar un test en `tests/test_webhook.py`.

### Agregar un proveedor de eventos

1. Crear una ruta nueva bajo `src/app/api/routes/`.
2. Reutilizar `require_api_key` o crear una dependencia de autenticación propia.
3. Registrar el router en `create_app()`.
4. Documentar el contrato en `docs/modules/<proveedor>/README.md`.

### Cambiar de base de datos

1. Cambiar `DATABASE_URL` (por ejemplo `postgresql+psycopg://...`).
2. Agregar el driver a `pyproject.toml`.
3. Antes de producción, incorporar migraciones (ver BACKLOG).

## 10. Convenciones

- Código, nombres e identificadores en inglés; documentación y UI en español.
- Errores de negocio como clases de `AppError`; nunca `raise HTTPException` desde la capa de aplicación.
- La capa `domain` no importa FastAPI, SQLAlchemy ni Pydantic.
- Un test por regla observable, a través de la interfaz pública (HTTP o servicio).
- `line-length = 100` con reglas estrictas de `ruff`.

## 11. Configuración

La configuración se lee con `pydantic-settings` desde `.env` o desde variables de entorno. Sin `.env`
el servicio arranca con los valores por defecto que se muestran acá.

| Variable | Default | Descripción |
| --- | --- | --- |
| `APP_NAME` | `Example Streaming Starter` | Nombre visible en `/docs` y en el panel. |
| `APP_VERSION` | `v0.1.0` | Versión reportada por `/health`. |
| `ENV` | `local` | Entorno (`local`, `staging`, `production`). |
| `DEBUG` | `false` | Nivel de log detallado. |
| `HOST` | `127.0.0.1` | Interfaz de escucha. |
| `PORT` | `8000` | Puerto de escucha. |
| `DATABASE_URL` | `sqlite+pysqlite:///./data/app.db` | Base de datos. |
| `ADMIN_USERNAME` | `admin` | Usuario del panel. |
| `ADMIN_PASSWORD` | `change-me-please` | Contraseña del panel. |
| `SESSION_SECRET` | `change-me-too-this-signs-the-admin-cookie` | Firma la cookie de sesión. |
| `SESSION_HTTPS_ONLY` | `false` | Marca la cookie como `Secure` (requiere HTTPS). |

`HOST` y `PORT` los consume `src/run.py`. El `Makefile` no fija ninguno, así que cambiar `.env` es
suficiente. Si el puerto está ocupado, cambiá `PORT` y volvé a ejecutar `make run`.

`make db-reset` borra la base local, incluidas las API keys. La base se recrea al arrancar.

## 12. Comandos

| Comando | Qué hace |
| --- | --- |
| `make help` | Lista los comandos disponibles. |
| `make install` | Crea `.venv` e instala las dependencias. |
| `make run` | Levanta el servidor con `HOST` y `PORT` de la configuración. |
| `make dev` | Igual que `run`, con recarga automática. |
| `make test` | Corre la suite de tests. |
| `make lint` | Verifica formato y reglas de lint. |
| `make format` | Formatea el código y aplica correcciones seguras. |
| `make check` | `lint` + `test`. |
| `make db-reset` | Borra la base SQLite local. |
| `make clean` | Borra `.venv`, caches y datos locales. |

## 13. Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `[Errno 98] address already in use` | El puerto de `PORT` está ocupado. | Cambiar `PORT` en `.env` y volver a `make run`. |
| `401 STREAM_API_KEY_MISSING` | Falta el header `X-API-Key`. | Agregar el header en el request. |
| `401 STREAM_API_KEY_INVALID` | Clave revocada, rotada o mal copiada. | Crear o rotar una clave en el panel. |
| `422 STREAM_PAYLOAD_INVALID` | Body vacío o fuera de contrato. | Revisar `details`; el ejemplo está en `/docs`. |
| `ModuleNotFoundError: No module named 'app'` | Se levantó `uvicorn` a mano sin `--app-dir src`. | Usar `make run`. |
| El panel no conserva la sesión | `SESSION_SECRET` cambia entre requests. | Dejar un valor fijo en `.env`. |

## 14. Seguridad

- Las API keys se guardan como `scrypt(secret, salt)` con salt por clave; nunca en texto plano.
- La comparación es de tiempo constante (`hmac.compare_digest`).
- La cookie del panel es firmada, `HttpOnly` y `SameSite=Strict`.
- Los formularios del panel validan token CSRF.
- El login no tiene rate limiting todavía (ver [BACKLOG.md](./BACKLOG.md)).
- En producción: HTTPS obligatorio, `SESSION_HTTPS_ONLY=true`, credenciales fuera del repositorio y
  `/admin` restringido por red o VPN cuando sea posible.

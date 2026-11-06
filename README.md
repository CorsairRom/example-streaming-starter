# c-Conecta Streaming Starter

Receptor mínimo para los eventos de streaming que **QForest** envía a **c-Conecta**.

QForest notifica por `HTTP POST` cada vez que una cámara empieza (`LIVE`) o termina (`DEFERRED`) una
transmisión. Este repositorio implementa ese endpoint, la validación de la API key y un panel de
administración para gestionar esas claves.

No hace falta saber de APIs para levantar esto: son tres comandos y una URL.

---

## Qué incluye

| Incluido | Detalle |
| --- | --- |
| `POST /webhooks/qforest/streams` | Recibe el evento, valida la API key y responde `200`. |
| Autenticación por API key | Header `X-API-Key`. La clave la genera c-Conecta y se la entrega a QForest. |
| Panel de administración | `/admin`: crear, rotar y revocar claves. |
| Documentación interactiva | `/docs` (Swagger) y `/openapi.json`. |
| Health check | `GET /health`. |
| Persistencia de claves | SQLite. Cero configuración. |
| Tests | `make test` (22 casos). |

## Qué **no** incluye (fase 2)

- Guardar los eventos recibidos (persistencia, historial, deduplicación).
- Simulador de QForest para probar sin esperar a una cámara real.
- Firma HMAC del payload, rate limiting, migraciones y Postgres.

Todo eso está priorizado en [BACKLOG.md](./BACKLOG.md).

---

## Requisitos

- **Python 3.12**
- **[uv](https://docs.astral.sh/uv/)** (maneja el entorno virtual y las dependencias)
- `make`
- `curl` (solo para las pruebas manuales)

Verificar:

```bash
python3.12 --version
uv --version
make --version
```

---

## Inicio rápido

```bash
# 1. Instalar dependencias (crea .venv automáticamente)
make install

# 2. Crear la configuración local
cp .env.example .env

# 3. Levantar el servidor
make run
```

Queda escuchando en la dirección de `HOST` y `PORT` en `.env` (por defecto `http://127.0.0.1:8000`).
Si ese puerto está ocupado, cambie `PORT` en `.env` y vuelva a ejecutar `make run`: no hay que tocar el
`Makefile`.

| Recurso | URL |
| --- | --- |
| Panel de administración | <http://127.0.0.1:8000/admin> |
| Documentación interactiva | <http://127.0.0.1:8000/docs> |
| Health check | <http://127.0.0.1:8000/health> |

> Antes de exponer el servicio a internet, cambie `ADMIN_PASSWORD` y `SESSION_SECRET` en `.env`.
> Para generar un secreto: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

---

## Primer uso en 5 minutos

### 1. Ingresar al panel

Abra <http://127.0.0.1:8000/admin> e ingrese con `ADMIN_USERNAME` / `ADMIN_PASSWORD` del archivo `.env`
(por defecto `admin` / `change-me-please`).

### 2. Crear una API key

En el panel, escriba un nombre (por ejemplo `c-conecta-produccion`) y presione **Crear key**.

La clave se muestra **una sola vez**:

```text
cck_9aa3d10908_6f1c3a4d9e8b7a2c5d0e1f3a4b6c7d8e9f0a1b2c
```

Cópiela y entréguela a QForest por un canal seguro. En la base de datos solo queda el prefijo y un hash
`scrypt`: **no se puede recuperar**. Si se pierde, se rota y se entrega la nueva.

### 3. Probar el endpoint

```bash
export API_URL="http://127.0.0.1:8000"
export API_KEY="cck_...la clave completa..."

curl -i -X POST "$API_URL/webhooks/qforest/streams" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_device_id": "CLA58",
    "datetime": "2026-10-27T15:32:24.935000+00:00",
    "url": "wss://hls.media.qforest.online/qforest/CLA58",
    "electromagnetic_spectrum": "combined",
    "state": "LIVE"
  }'
```

Respuesta esperada:

```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"accepted"}
```

---

## Contrato que se entrega a QForest

Esto es lo único que QForest necesita para integrarse:

| Dato | Valor |
| --- | --- |
| Método | `POST` |
| URL | `https://<dominio-de-c-conecta>/webhooks/qforest/streams` |
| Header de autenticación | `X-API-Key: <clave entregada por c-Conecta>` |
| Content-Type | `application/json` |
| Respuesta de éxito | `200 OK` con `{"status":"accepted"}` |
| Timeout recomendado | 5 segundos |
| Reintentos recomendados | Sí, con backoff; el receptor es idempotente a nivel de contrato (ver BACKLOG) |

Payload:

```json
{
  "camera_device_id": "CLA58",
  "datetime": "2026-10-27T15:32:24.935000+00:00",
  "url": "wss://hls.media.qforest.online/qforest/CLA58",
  "electromagnetic_spectrum": "combined",
  "state": "LIVE"
}
```

| Campo | Tipo | Regla en este servicio |
| --- | --- | --- |
| `camera_device_id` | string | Obligatorio, 1 a 64 caracteres. |
| `datetime` | string ISO-8601 | Obligatorio, **debe incluir zona horaria**. Se normaliza a UTC. |
| `url` | string | Obligatorio, debe empezar con `wss://`. |
| `electromagnetic_spectrum` | string | Opcional, por defecto `"combined"`. |
| `state` | string | Obligatorio, `LIVE` o `DEFERRED` (se acepta cualquier combinación de mayúsculas). |

Detalle completo, errores y casos borde:
[docs/modules/webhook-streams/README.md](./docs/modules/webhook-streams/README.md).

---

## Configuración

Toda la configuración vive en `.env` (ver `.env.example`). Nunca se versiona.

| Variable | Default | Descripción |
| --- | --- | --- |
| `APP_NAME` | `c-Conecta Streaming Starter` | Nombre visible en `/docs` y en el panel. |
| `APP_VERSION` | `v0.1.0` | Versión reportada por `/health`. |
| `ENV` | `local` | Entorno (`local`, `staging`, `production`). |
| `DEBUG` | `false` | Modo de depuración. |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Dirección de escucha. Los usa `make run`. |
| `DATABASE_URL` | `sqlite+pysqlite:///./data/app.db` | Base de datos. SQLite por defecto. |
| `ADMIN_USERNAME` | `admin` | Usuario del panel. |
| `ADMIN_PASSWORD` | `change-me-please` | Contraseña del panel. **Cambiar.** |
| `SESSION_SECRET` | `change-me...` | Firma la cookie de sesión. **Cambiar.** |
| `SESSION_HTTPS_ONLY` | `false` | Poner en `true` detrás de HTTPS. |

---

## Comandos disponibles

```bash
make help      # lista los comandos
make install   # crea .venv e instala dependencias
make run       # levanta el servidor
make dev       # levanta el servidor con recarga automática
make test      # corre los tests
make lint      # verifica formato y lint
make format    # formatea el código
make check     # lint + tests
make db-reset  # borra la base local (incluye las API keys)
make clean     # borra .venv, caches y datos locales
```

---

## Estructura del proyecto

```text
.
├── src/app/
│   ├── api/              # Capa HTTP: rutas, dependencias, plantillas del panel
│   ├── application/      # Casos de uso: API keys y eventos de streaming
│   ├── domain/           # Entidades, errores y puertos (sin FastAPI ni SQLAlchemy)
│   ├── infrastructure/   # SQLAlchemy, hash de claves, repositorios
│   ├── container.py      # Composition root
│   ├── main.py           # create_app() y app ASGI
│   └── settings.py       # Configuración con pydantic-settings
├── src/run.py            # Entrypoint: toma HOST y PORT de .env
├── tests/                # Tests de contrato (webhook, api keys, panel)
├── docs/                 # Contrato, catálogo de errores y documento original
├── Makefile
├── pyproject.toml
└── ruff.toml
```

La arquitectura y las decisiones están explicadas en [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Seguridad

- Las API keys se guardan como `scrypt(secret, salt)` con salt por clave. Nunca en texto plano.
- La comparación es de tiempo constante (`hmac.compare_digest`).
- La cookie del panel es firmada, `HttpOnly` y `SameSite=Strict`.
- Los formularios del panel usan token CSRF.
- `/admin` no tiene rate limiting todavía (ver [BACKLOG.md](./BACKLOG.md)).
- En producción: HTTPS obligatorio, `SESSION_HTTPS_ONLY=true`, credenciales fuera del repositorio y
  `/admin` restringido por red o VPN si es posible.

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `401 STREAM_API_KEY_MISSING` | Falta el header `X-API-Key`. | Agregar el header en el POST. |
| `401 STREAM_API_KEY_INVALID` | Clave revocada, rotada o mal copiada. | Crear/rotar una clave nueva en el panel. |
| `422 STREAM_PAYLOAD_INVALID` | `datetime` sin zona horaria o `url` que no es `wss://`. | Revisar el detalle en la respuesta. |
| `[Errno 98] address already in use` | El puerto de `PORT` está ocupado por otro proceso. | Cambiar `PORT` en `.env` (por ejemplo `8100`) y volver a `make run`. |
| `ModuleNotFoundError: No module named 'app'` | Se levantó `uvicorn` a mano sin `--app-dir src`. | Usar `make run`. |
| El panel no guarda la sesión | `SESSION_SECRET` cambió entre requests. | Dejar un valor fijo en `.env`. |

---

## Documentación

- [ARCHITECTURE.md](./ARCHITECTURE.md) — capas, flujos y decisiones de diseño.
- [docs/modules/webhook-streams/README.md](./docs/modules/webhook-streams/README.md) — contrato del webhook.
- [docs/modules/api-keys/README.md](./docs/modules/api-keys/README.md) — ciclo de vida de las claves.
- [docs/error-codes-catalog.md](./docs/error-codes-catalog.md) — códigos de error.
- [docs/webhook-examples.http](./docs/webhook-examples.http) — ejemplos ejecutables
  (VS Code REST Client / Thunder Client).
- [docs/referencia/](./docs/referencia/) — requerimiento original enviado por QForest.
- [BACKLOG.md](./BACKLOG.md) — fase 2.

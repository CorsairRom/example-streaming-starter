# c-Conecta Streaming Starter

Servicio mínimo que recibe eventos de streaming por `HTTP POST` y responde `200` cuando la transmisión
de una cámara empieza (`LIVE`) o termina (`DEFERRED`). Incluye un panel para administrar las API keys de
quien envía esos eventos.

Esta guía es el **camino feliz**, con la configuración de ejemplo tal como viene el repositorio. Para
cambiar puerto, credenciales o base de datos, y para entender el diseño, ver
[ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Antes de empezar

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- `make`

---

## Paso 1 — Instalar

```bash
make install
```

Crea el entorno virtual e instala las dependencias.

## Paso 2 — Ejecutar

```bash
make run
```

Queda escuchando en <http://127.0.0.1:8000>.

> Todos los links de esta guía usan el puerto por defecto (`8000`). Si `PORT` en tu `.env` tiene otro
> número, reemplazalo en las URLs.

## Paso 3 — Entrar al panel

Abrí <http://127.0.0.1:8000/admin> y usá las credenciales de ejemplo:

| Campo | Valor |
| --- | --- |
| Usuario | `admin` |
| Contraseña | `change-me-please` |

## Paso 4 — Crear una API key

1. En **Crear una API key**, escribí un nombre, por ejemplo `prueba`.
2. Presioná **Crear key**.
3. Copiá la clave completa (`cck_...`). **Se muestra una sola vez**; no se puede recuperar después.

## Paso 5 — Abrir Swagger

Ir a <http://127.0.0.1:8000/docs>.

## Paso 6 — Probar el endpoint

1. Buscá la sección **streams**.
2. Abrí `POST /webhooks/streams` y presioná **Try it out**.
3. En el campo `X-API-Key`, pegá la clave del paso 4.
4. El body ya viene precargado con el ejemplo; no hace falta editarlo.
5. Presioná **Execute**.

## Paso 7 — Ver la respuesta

```http
200 OK
{"status": "accepted"}
```

Listo: el servicio recibió el evento, validó la clave y confirmó.

---

## Qué significa cada respuesta

| Respuesta | Significado |
| --- | --- |
| `200 {"status":"accepted"}` | Evento recibido y aceptado. |
| `401 STREAM_API_KEY_MISSING` | Falta el header `X-API-Key`. |
| `401 STREAM_API_KEY_INVALID` | La clave no existe o fue revocada. |
| `422 STREAM_PAYLOAD_INVALID` | El body no cumple el contrato; `details` indica qué campo falló. |

Catálogo completo: [docs/error-codes-catalog.md](./docs/error-codes-catalog.md).

---

## Próximo paso — Entregar la clave al emisor

Esto es lo único que necesita quien envía los eventos:

| Dato | Valor |
| --- | --- |
| Método | `POST` |
| URL | `https://<tu-dominio>/webhooks/streams` |
| Header | `X-API-Key: <clave>` |
| Content-Type | `application/json` |
| Respuesta de éxito | `200 OK` con `{"status":"accepted"}` |
| Timeout recomendado | 5 segundos |

Payload:

```json
{
  "camera_device_id": "CLA58",
  "datetime": "2026-10-27T15:32:24.935000+00:00",
  "url": "wss://media.example.com/live/CLA58",
  "electromagnetic_spectrum": "combined",
  "state": "LIVE"
}
```

Contrato completo y casos borde:
[docs/modules/webhook-streams/README.md](./docs/modules/webhook-streams/README.md).

---

## Documentación técnica

| Documento | Contenido |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Capas, flujos, configuración, comandos, seguridad y problemas frecuentes. |
| [docs/modules/webhook-streams/README.md](./docs/modules/webhook-streams/README.md) | Contrato del webhook y casos borde. |
| [docs/modules/api-keys/README.md](./docs/modules/api-keys/README.md) | Ciclo de vida de las claves. |
| [docs/error-codes-catalog.md](./docs/error-codes-catalog.md) | Códigos de error. |
| [docs/webhook-examples.http](./docs/webhook-examples.http) | Ejemplos ejecutables. |
| [BACKLOG.md](./BACKLOG.md) | Mejoras fuera del alcance actual. |

> Las credenciales de ejemplo (`admin` / `change-me-please`), la clave de sesión y SQLite sirven para
> probar en local. Antes de exponer el servicio, seguí la sección **Seguridad** de
> [ARCHITECTURE.md](./ARCHITECTURE.md).

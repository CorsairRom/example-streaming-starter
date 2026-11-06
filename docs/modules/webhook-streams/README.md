# Módulo: webhook de streaming

Contrato público que QForest consume. Es la única interfaz que necesitan conocer para integrarse.

## Endpoint

```http
POST /webhooks/qforest/streams
```

| Requisito | Valor |
| --- | --- |
| Autenticación | Header `X-API-Key: <clave>` obligatorio |
| Content-Type | `application/json` |
| Respuesta de éxito | `200 OK` con `{"status": "accepted"}` |
| Tamaño máximo del body | Sin límite explícito (el proxy inverso decide) |

## Payload

```json
{
  "camera_device_id": "CLA58",
  "datetime": "2026-10-27T15:32:24.935000+00:00",
  "url": "wss://hls.media.qforest.online/qforest/CLA58",
  "electromagnetic_spectrum": "combined",
  "state": "LIVE"
}
```

### Campos

| Campo | Tipo | Obligatorio | Validación en este servicio |
| --- | --- | --- | --- |
| `camera_device_id` | string | Sí | 1 a 64 caracteres, sin espacios al inicio/fin. |
| `datetime` | string ISO-8601 | Sí | Debe incluir offset (`+00:00` o `Z`). Se normaliza a UTC. |
| `url` | string | Sí | Debe empezar con `wss://` y tener host. |
| `electromagnetic_spectrum` | string | No | Por defecto `"combined"`. 1 a 64 caracteres. |
| `state` | string | Sí | `LIVE` o `DEFERRED`, sin distinguir mayúsculas. |

Los campos desconocidos se ignoran. Los campos conocidos con tipo incorrecto se rechazan.

## Ciclo de vida

```text
[Cámara inicia transmisión]
        │
        ▼
POST { state: "LIVE" }       ──►  200 {"status":"accepted"}
        │
        │  (transmisión en curso)
        ▼
POST { state: "DEFERRED" }   ──►  200 {"status":"accepted"}
```

## Respuestas

### 200 — aceptado

```json
{ "status": "accepted" }
```

### 401 — sin clave

```json
{ "error": { "code": "STREAM_API_KEY_MISSING", "message": "The X-API-Key header is required." } }
```

### 401 — clave inválida o revocada

```json
{ "error": { "code": "STREAM_API_KEY_INVALID", "message": "The API key is unknown or revoked." } }
```

### 422 — payload inválido

```json
{
  "error": {
    "code": "STREAM_PAYLOAD_INVALID",
    "message": "The request body is invalid.",
    "details": [
      {
        "loc": ["body", "datetime"],
        "msg": "Value error, datetime must include a timezone offset (UTC is expected).",
        "type": "value_error"
      }
    ]
  }
}
```

## Ejemplos

```bash
API_URL="http://127.0.0.1:8000"
API_KEY="cck_..."

# Inicio de transmisión
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

# Fin de transmisión
curl -i -X POST "$API_URL/webhooks/qforest/streams" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_device_id": "CLA58",
    "datetime": "2026-10-27T15:40:00.000000+00:00",
    "url": "wss://hls.media.qforest.online/qforest/CLA58",
    "electromagnetic_spectrum": "combined",
    "state": "DEFERRED"
  }'
```

## Casos borde

| Caso | Comportamiento |
| --- | --- |
| `state` = `"Live"` | Aceptado; se normaliza a `LIVE`. |
| `state` = `"PAUSED"` | `422`. |
| `datetime` sin offset | `422`. |
| `url` = `https://...` | `422`; el contrato exige `wss://`. |
| Campo extra desconocido | Ignorado; responde `200`. |
| Body no es JSON | `422 STREAM_PAYLOAD_INVALID`. |
| Clave revocada | `401 STREAM_API_KEY_INVALID`. |

## Implementación

- Ruta: `src/app/api/routes/webhook.py`
- Validación: modelo `StreamEventBody` (Pydantic v2)
- Autenticación: `src/app/api/deps.py` → `require_api_key`
- Caso de uso: `src/app/application/stream_events.py`
- Tests: `tests/test_webhook.py`

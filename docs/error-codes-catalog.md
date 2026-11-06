# Catálogo de códigos de error

Todas las respuestas de error tienen la misma forma:

```json
{
  "error": {
    "code": "STREAM_API_KEY_INVALID",
    "message": "The API key is unknown or revoked.",
    "details": []
  }
}
```

`details` solo aparece en errores de validación.

## Webhook

| Código | HTTP | Cuándo ocurre | Qué hacer |
| --- | --- | --- | --- |
| `STREAM_API_KEY_MISSING` | 401 | El request no trae el header `X-API-Key`. | Configurar el header en el emisor. |
| `STREAM_API_KEY_INVALID` | 401 | La clave no existe, está revocada o el secreto no coincide. | Verificar la clave; si se perdió, rotar en el panel. |
| `STREAM_PAYLOAD_INVALID` | 422 | El body no cumple el contrato (campo faltante, tipo incorrecto, `datetime` sin zona horaria, `url` que no es `wss://`, `state` desconocido). | Revisar `details` y corregir el payload. |

## Panel de administración

| Código | HTTP | Cuándo ocurre | Qué hacer |
| --- | --- | --- | --- |
| `ADMIN_INVALID_CREDENTIALS` | 401 | Usuario o contraseña incorrectos. | Reintentar con las credenciales de `.env`. |
| `ADMIN_CSRF_TOKEN_INVALID` | 403 | Falta el token CSRF o la sesión expiró. | Recargar la página e intentar de nuevo. |
| `VALIDATION_ERROR` | 422 | Un formulario del panel llegó incompleto. | Recargar y completar los campos. |
| `API_KEY_NOT_FOUND` | 404 | Se intentó operar sobre una clave inexistente. | Recargar el panel. |
| `API_KEY_ALREADY_REVOKED` | 409 | Se intentó rotar o revocar una clave ya revocada. | Crear una clave nueva. |

## Códigos internos de FastAPI

`401` sin `X-API-Key` en rutas que no son del webhook y `422` de validación de query/path usan el formato
anterior, con `VALIDATION_ERROR`.

## Dónde se definen

`src/app/domain/errors.py`. Cada clase declara `status_code` y `code`; el handler
`src/app/api/error_handlers.py` arma la respuesta.

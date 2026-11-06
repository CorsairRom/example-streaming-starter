# Backlog — fase 2

Alcance actual: **un receptor mínimo que responde `200`**. Las siguientes son mejoras fuera de ese
alcance, en orden de valor para la integración. No están implementadas.

## Prioridad alta

### 1. Persistir los eventos recibidos

**Por qué.** Hoy el evento solo se escribe en el log: si el proceso se reinicia o el log rota, no queda
evidencia de que el emisor envió algo. Ante un reclamo ("la cámara estaba en vivo y no lo vimos") no hay
forma de responder.

**Qué hacer.**

- Tabla `stream_events`: `id`, `camera_device_id`, `datetime` (UTC), `url`, `state`,
  `electromagnetic_spectrum`, `received_at`, `payload_hash`.
- Índice único sobre `(camera_device_id, datetime, state)` o sobre `payload_hash` para deduplicar.
- Endpoint de consulta `GET /events` (protegido, solo para el panel) con filtros por cámara y fecha.
- Retención configurable (por ejemplo 90 días) con un script de limpieza.

**Criterio de aceptación.** Enviar el mismo payload dos veces deja una sola fila; el panel muestra los
eventos ordenados por fecha; los tests cubren deduplicación y retención.

### 2. Simulador del emisor

**Por qué.** El operador no puede probar el flujo completo hasta que el emisor conecte su lado. Un
simulador les permite validar red, HTTPS, proxy y firewall por su cuenta.

**Qué hacer.**

- `scripts/simulate.py` con `--url`, `--api-key`, `--camera` y `--state`.
- Secuencia `LIVE`, espera configurable y `DEFERRED`.
- Target `make simulate` que lea `API_URL` y `API_KEY` del entorno.
- Documentar el uso en el README.

**Criterio de aceptación.** `make simulate` contra el servicio local imprime `200 accepted` para ambos
estados y falla con un mensaje claro si falta la API key.

### 3. Idempotencia explícita en el contrato

**Por qué.** Si el emisor reintenta un POST (timeout, caída de red), el evento se procesa dos veces. Hoy
no duele porque no se persiste, pero duele apenas exista la tabla de eventos.

**Qué hacer.** Pedir al emisor un `event_id` o aceptar un header `Idempotency-Key`. Mientras no exista,
deduplicar por `(camera_device_id, datetime, state)`.

**Criterio de aceptación.** Dos requests con la misma identidad producen un solo efecto aguas abajo y la
segunda responde `200` sin duplicar.

## Prioridad media

### 4. Firma HMAC del payload

**Por qué.** La API key autentica al emisor, pero no protege la integridad del cuerpo si pasa por un
proxy intermedio ni permite detectar replay.

**Qué hacer.** Header `X-Signature: sha256=<hmac>` sobre `timestamp + body`, con secreto
compartido y ventana de tolerancia de 5 minutos. Mantener `X-API-Key` como autenticación primaria y
HMAC como verificación adicional durante la transición.

**Criterio de aceptación.** Un body alterado o un timestamp viejo devuelven `401`.

### 5. Rate limiting

**Por qué.** `/admin/login` acepta intentos ilimitados. El webhook también.

**Qué hacer.** Límite por IP en el login (por ejemplo 5 intentos por minuto) y límite global en el
webhook. En un despliegue de un solo proceso alcanza con un contador en memoria; con varios procesos,
Redis.

**Criterio de aceptación.** El intento 6 de login en un minuto responde `429`.

### 6. Migraciones de esquema

**Por qué.** `create_all` crea tablas faltantes, pero no altera columnas existentes. El primer cambio de
esquema en una instalación real obliga a borrar la base.

**Qué hacer.** Incorporar Alembic con una migración inicial que refleje el esquema actual, y documentar
`make migrate` / `make migration`.

**Criterio de aceptación.** Una base creada con la versión anterior se actualiza sin perder datos.

## Prioridad baja

### 7. Postgres en producción

SQLite alcanza para un receptor de bajo volumen y un solo proceso. Si se despliega con varias réplicas o
se persisten eventos, migrar a Postgres con `psycopg`.

### 8. Observabilidad

- Logs estructurados en JSON.
- `request_id` por request, propagado al log del evento.
- Métricas: eventos aceptados/rechazados por código, latencia, claves activas.
- Alerta si no se recibe ningún evento en N horas durante horario operativo.

### 9. Empaquetado y despliegue

- `Dockerfile` multi-stage con usuario no root.
- `docker-compose.yml` para levantar el servicio con volumen para SQLite.
- Workflow de CI: `make check` en cada push.

### 10. Reemisión a consumidores internos

Si el operador necesita que el evento llegue a otro sistema (ERP, monitoreo, cola), agregar un puerto
`EventPublisher` en `domain/ports.py` con una implementación de cola y reintentos.

### 11. Multi-cliente

Hoy hay un único conjunto de claves. Si el servicio se comparte entre clientes, agregar `client_id` a
la tabla de claves y segmentar el panel.

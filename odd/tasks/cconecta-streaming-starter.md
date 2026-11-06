# c-Conecta Streaming Starter

Repo de arranque para que c-Conecta reciba los eventos de streaming de QForest sin tener API propia.
Branch: `main`. Delivery: no aplica (repo de buena voluntad, se entrega como ZIP/GitHub a criterio del humano).
Test runner: `pytest` (via `make test`).

## Specs

S1. El servicio expone `POST /webhooks/qforest/streams` que acepta exactamente el payload del PDF
`requerimiento-integracion-streaming-cconecta`: `camera_device_id`, `datetime`, `url`,
`electromagnetic_spectrum`, `state`.

S2. Autenticacion: cada request debe traer el header `X-API-Key`. La key la genera c-Conecta en su panel
y se la entrega a QForest, que la envia en cada POST. Sin header → `401 STREAM_API_KEY_MISSING`.
Header presente pero desconocida o revocada → `401 STREAM_API_KEY_INVALID`.

S3. Validacion del payload: `state` se acepta case-insensitive (`LIVE`/`DEFERRED`) y se normaliza a
mayusculas; `datetime` debe traer timezone (se normaliza a UTC); `url` debe ser `wss://`; un payload
invalido responde `422 STREAM_PAYLOAD_INVALID`.

S4. Un request valido responde `200` con `{"status": "accepted"}`, sin persistir el evento (fase 2).

S5. Panel de administracion en `/admin`, protegido por una unica password (`ADMIN_PASSWORD`) con sesion
firmada. Permite listar, crear, rotar y revocar API keys.

S6. La API key se muestra una sola vez al crearla o rotarla. En la base se guarda solo `prefix` + hash
`scrypt` con salt por key; nunca la key en claro.

S7. `GET /health` responde estado del servicio y la version.

S8. Documentacion de arranque en `README.md`, arquitectura en `ARCHITECTURE.md`, contrato del webhook en
`docs/modules/webhook-streams/README.md`, catalogo de errores en `docs/error-codes-catalog.md`, y
`BACKLOG.md` con las recomendaciones de fase 2 (persistencia de eventos, simulador, dedupe, HMAC).

## Tasks

- T1 — Esqueleto (pyproject, ruff, Makefile, .env.example, .gitignore, .python-version) — S8 — `done`
- T2 — Tests de contrato del webhook y de API keys (RED) — S1-S4, S6 — `done` (RED: `ModuleNotFoundError: No module named 'app'`)
- T3 — Dominio + aplicacion + infraestructura (SQLite, hashing, repositorios) — S2, S5, S6 — `done`
- T4 — Rutas FastAPI del webhook, health y dependencias de auth — S1-S4, S7 — `done`
- T5 — Panel admin (login, sesion, CSRF, crear/rotar/revocar) — S5, S6 — `done`
- T6 — Documentacion + BACKLOG — S8 — `done`
- T7 — Verificacion (pytest verde, ruff, servidor arriba + curl real) — todas — `done`

## Log

L1 (2026-11-06, pedido original): "Neceisto que me eches una manno, hoy un cliente quiere integrarse con
nosotros para recibir link de lo que trasnmiten las camaras, puedes leer qforest-docs para tener mas info.
vale pero el tema que no saben nada de enpoint lo que es nada le pasamos este documento [PDF 1] para que
entendieran mas o menos que tenian que levantar pero dicen que no tienen nada de api lo que es nada.
Entonces les quiero crear un repo rapidito con fast api uvicorn pydantic setting pydantic v2 makefil etc
todo como esta qforest-be mas o menos un estracto con api-key osea asi ellos no dicen esta es nuestra api
key y nosotros se la enviamos a su endopoint. Con un peque;o panel de admin tambien para que puedan
gestionar sus apikey rotar etc algo sencillo bien documentado con architecc ture.md etc todo como sigue
qforest-be para que tenga algo en que guiarse y levantar. Dime si entendiste y que vas hacer primero anda
a buscar la info"

L2 (2026-11-06, correccion del humano): "que quede en personal porque es algo que hare de buena voluntad.
si el receptor minimo que responde 200, anotaa un backlog con las recomendaciones de persistencia de
envetos + simulador para verlo despues. en otra fase."

L3 (2026-11-06): Evidencia recolectada. PDF: POST JSON, respuesta 200/204, endpoint de ejemplo
`https://api.c-conecta.cl/webhooks/qforest/streams`. `qforest-be` es Django 5.2 + Django Ninja (no
FastAPI puro), Python 3.12, `uv`, `ruff`, `pytest`, capas domain/application/infrastructure,
`Result[T, E]`, `docs/modules/<modulo>/README.md` y `docs/error-codes-catalog.md`. Se portan las
convenciones, no el framework. `qforest-docs` define el patron de credenciales de solo escritura y
rotacion; aca se simplifica a hash + prefijo.

L4 (2026-11-06, evidencia GREEN): `uv run pytest` → `22 passed`. `uv run ruff check .` → `All checks
passed`. `npx markdownlint-cli2` → `0 issues` en 7 archivos `.md`. Smoke test real con `uvicorn` en
puerto 8010: `/health` 200; webhook sin key 401 `STREAM_API_KEY_MISSING`; login del panel 303; clave
creada desde el panel; `LIVE` y `DEFERRED` con key 200 `{"status":"accepted"}`; payload con
`datetime` sin offset y `url` https 422 `STREAM_PAYLOAD_INVALID`; rotacion desde el panel → clave
vieja 401 / nueva 200; revocacion → 401.

L5 (2026-11-06, decision): el repo queda en `/home/rmoore/dev/personal/cconecta-streaming-starter`
(pedido L2) y usa `--app-dir src` en uvicorn para no exigir un paquete instalable. La UI y la
documentacion van en espanol neutro porque el destinatario es un equipo chileno sin experiencia en
APIs; el codigo, los identificadores y los comentarios quedan en ingles.

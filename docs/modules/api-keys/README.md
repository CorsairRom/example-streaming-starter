# Módulo: API keys

Cómo c-Conecta emite, entrega y administra las claves que el emisor usa para autenticarse.

## Concepto

La clave la genera **c-Conecta** y se la entrega al emisor por un canal seguro. El emisor la envía en
cada request:

```http
X-API-Key: cck_9aa3d10908_6f1c3a4d9e8b7a2c5d0e1f3a4b6c7d8e9f0a1b2c
```

Es una credencial de **solo escritura** desde el punto de vista del panel: se muestra una vez al crearla
o rotarla y nunca más.

## Formato

```text
cck_<prefix>_<secret>

cck_   marker fijo
       │
       └─ prefix: 10 caracteres hex. Se guarda en claro, indexado, para buscar la fila.
                  │
                  └─ secret: 48 caracteres hex (192 bits). Se guarda como scrypt(secret, salt).
```

En la base de datos:

| Columna | Contenido |
| --- | --- |
| `prefix` | Los 10 hex del medio, en claro. |
| `key_hash` | `scrypt(secret, salt)` en hexadecimal. |
| `salt` | 16 bytes aleatorios en hexadecimal, uno por clave. |

Un volcado de la base **no** permite reconstruir las claves.

## Ciclo de vida

```text
                 ┌──────────────── rotar ────────────────┐
                 │                                       ▼
  crear ──► activa ─────────────────────────────────► activa (nueva)
                 │
                 └── revocar ──► revocada (irreversible)
```

### Crear

1. Panel → **Crear key** → nombre identificatorio.
2. La clave completa aparece una sola vez.
3. Copiarla y entregarla al emisor.

### Rotar

Usar cuando:

- La clave se filtró o se sospecha filtración.
- Cambió la persona que la administra.
- Política de rotación periódica.

Pasos:

1. Panel → **Rotar** en la fila de la clave.
2. Copiar la clave nueva.
3. Entregarla al emisor.
4. Confirmar que el emisor ya la está usando (ver `Último uso` en el panel).

La clave anterior deja de funcionar **inmediatamente**. Coordinar la entrega antes de rotar para evitar
una ventana sin autenticación.

### Revocar

1. Panel → **Revocar**.
2. La clave deja de autenticar al instante.
3. La fila queda como historial (`revoked_at`), no se borra.

Una clave revocada no se puede rotar ni reactivar. Si se necesita volver a operar, se crea una nueva.

## Buenas prácticas

- Una clave por integración, no una clave compartida entre clientes.
- Nombre descriptivo: `c-conecta-produccion`, `c-conecta-staging`.
- Entregar por canal seguro (gestor de secretos, no correo ni chat).
- Rotar ante cualquier duda, y también de forma periódica.
- Revisar `Último uso`: una clave activa sin uso durante meses es candidata a revocación.
- En producción, restringir `/admin` por red o VPN cuando sea posible.

## Implementación

- Servicio: `src/app/application/api_keys.py`
- Repositorio: `src/app/infrastructure/repositories.py`
- Hashing: `src/app/infrastructure/security.py`
- Panel: `src/app/api/routes/admin.py` y `src/app/api/templates/`
- Tests: `tests/test_api_keys.py`, `tests/test_admin.py`

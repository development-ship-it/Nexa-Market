-- =============================================================================
--  Migración 0010 — usuario.vistas_web
--  Equivalente a:  python manage.py migrate base_datos 0010
--
--  Secciones de la WEB habilitadas por usuario. La columna `vistas` que ya
--  existía es la de la app móvil y no se toca.
--
--  Las filas existentes quedan en NULL, que el modelo interpreta como "ve
--  todo": nadie pierde acceso al aplicar esto.
-- =============================================================================

BEGIN;

ALTER TABLE "usuario" ADD COLUMN "vistas_web" jsonb NULL;

-- Registrar la migración (equivale a `migrate --fake`). Sin esto, Django la va
-- a intentar aplicar más tarde y va a fallar con "la columna ya existe".
INSERT INTO django_migrations (app, name, applied)
VALUES ('base_datos', '0010_usuario_vistas_web', NOW());

COMMIT;


-- =============================================================================
--  DESHACER
-- =============================================================================
-- BEGIN;
-- ALTER TABLE "usuario" DROP COLUMN IF EXISTS "vistas_web";
-- DELETE FROM django_migrations
--  WHERE app = 'base_datos' AND name = '0010_usuario_vistas_web';
-- COMMIT;

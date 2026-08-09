-- =============================================================================
--  Migración 0009 — Pago, SolicitudPremium y suscripción en Empresa
--  Equivalente exacto a:  python manage.py migrate base_datos 0009
--
--  Generado con el motor de Django (no escrito a mano). Para ejecutar desde el
--  SQL Editor de Supabase cuando no se puede correr `migrate` por bloqueo de IP.
--
--  Todo va dentro de una transacción: si algo falla, no queda nada a medias.
--  La última sentencia registra la migración en `django_migrations`, que es lo
--  mismo que hace `migrate --fake`. Sin eso, Django intentará aplicarla más
--  tarde y fallará con "la tabla ya existe".
-- =============================================================================


-- ── ANTES DE EMPEZAR ────────────────────────────────────────────────────────
-- Ejecuta esto SOLO y revisa el resultado. Abajo se borra `empresa.fecha_pago`,
-- y este conteo dice si esa columna tiene datos que perderías.
--
--   SELECT COUNT(*) AS con_datos FROM empresa WHERE fecha_pago IS NOT NULL;
--
-- Si devuelve 0, adelante sin más. Si no, respáldala primero:
--
--   CREATE TABLE respaldo_empresa_fecha_pago AS
--   SELECT id_empresa, fecha_pago FROM empresa WHERE fecha_pago IS NOT NULL;
-- ─────────────────────────────────────────────────────────────────────────────


BEGIN;

-- ── 1. EMPRESA: estado de la suscripción y datos tributarios ────────────────
-- CASCADE también elimina vistas o reglas que dependan de la columna.
ALTER TABLE "empresa" DROP COLUMN "fecha_pago" CASCADE;

ALTER TABLE "empresa" ADD COLUMN "descuento_porcentaje" integer DEFAULT 0 NOT NULL;
ALTER TABLE "empresa" ALTER COLUMN "descuento_porcentaje" DROP DEFAULT;

ALTER TABLE "empresa" ADD COLUMN "estado_suscripcion" varchar(20) DEFAULT 'GRATUITO' NOT NULL;
ALTER TABLE "empresa" ALTER COLUMN "estado_suscripcion" DROP DEFAULT;

ALTER TABLE "empresa" ADD COLUMN "fecha_vencimiento" timestamp with time zone NULL;
ALTER TABLE "empresa" ADD COLUMN "razon_social" varchar(255) NULL;
ALTER TABLE "empresa" ADD COLUMN "giro" varchar(255) NULL;
ALTER TABLE "empresa" ADD COLUMN "direccion" varchar(255) NULL;


-- ── 2. PAGO: el libro contable de la suscripción ────────────────────────────
CREATE TABLE "pago" (
    "id_pago"               varchar(36) NOT NULL PRIMARY KEY,
    "usuarios_cobrados"     integer NOT NULL,
    "monto_neto"            integer NOT NULL,
    "monto_iva"             integer NOT NULL,
    "monto_total"           integer NOT NULL,
    "monto_descuento"       integer NOT NULL,
    "descripcion_descuento" varchar(255) NULL,
    "metodo_pago"           varchar(20) NOT NULL,
    "estado"                varchar(20) NOT NULL,
    "referencia_externa"    varchar(100) NULL UNIQUE,
    "fecha_pago"            timestamp with time zone NOT NULL,
    "fecha_confirmacion"    timestamp with time zone NULL,
    "periodo_inicio"        timestamp with time zone NULL,
    "periodo_fin"           timestamp with time zone NULL,
    "comprobante_url"       varchar(200) NULL,
    "comision_neto"         integer NULL,
    "comision_iva"          integer NULL,
    "comision_total"        integer NULL,
    "monto_abonado"         integer NULL,
    "fecha_abono"           timestamp with time zone NULL,
    "created_at"            timestamp with time zone NOT NULL,
    "confirmado_por_id"     varchar(36) NULL,
    "id_empresa"            varchar(36) NOT NULL,
    "id_plan"               integer NULL
);


-- ── 3. SOLICITUD_PREMIUM: bandeja de entrada del backoffice ─────────────────
CREATE TABLE "solicitud_premium" (
    "id_solicitud"    varchar(36) NOT NULL PRIMARY KEY,
    "fecha_solicitud" timestamp with time zone NOT NULL,
    "estado"          varchar(20) NOT NULL,
    "nota"            text NULL,
    "id_empresa"      varchar(36) NOT NULL,
    "id_pago"         varchar(36) NULL,
    "id_plan"         integer NULL
);


-- ── 4. ÍNDICES DE CONSULTA ──────────────────────────────────────────────────
-- Los nombres son los que Django guarda en el estado de la migración: si los
-- cambias, una migración futura que los elimine no los va a encontrar.
CREATE INDEX "pago_id_empr_0b4d08_idx" ON "pago" ("id_empresa", "estado");
CREATE INDEX "solicitud_p_estado_254a6e_idx" ON "solicitud_premium" ("estado", "fecha_solicitud");


-- ── 5. CLAVES FORÁNEAS ──────────────────────────────────────────────────────
ALTER TABLE "pago" ADD CONSTRAINT "pago_confirmado_por_id_20e99b19_fk_usuario_id_usuario"
    FOREIGN KEY ("confirmado_por_id") REFERENCES "usuario" ("id_usuario") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "pago" ADD CONSTRAINT "pago_id_empresa_422958ca_fk_empresa_id_empresa"
    FOREIGN KEY ("id_empresa") REFERENCES "empresa" ("id_empresa") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "pago" ADD CONSTRAINT "pago_id_plan_872ec45d_fk_plan_id_plan"
    FOREIGN KEY ("id_plan") REFERENCES "plan" ("id_plan") DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE "solicitud_premium" ADD CONSTRAINT "solicitud_premium_id_empresa_45f5df51_fk_empresa_id_empresa"
    FOREIGN KEY ("id_empresa") REFERENCES "empresa" ("id_empresa") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "solicitud_premium" ADD CONSTRAINT "solicitud_premium_id_pago_7986ddd0_fk_pago_id_pago"
    FOREIGN KEY ("id_pago") REFERENCES "pago" ("id_pago") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "solicitud_premium" ADD CONSTRAINT "solicitud_premium_id_plan_b7324e3b_fk_plan_id_plan"
    FOREIGN KEY ("id_plan") REFERENCES "plan" ("id_plan") DEFERRABLE INITIALLY DEFERRED;


-- ── 6. ÍNDICES DE LAS FORÁNEAS Y BÚSQUEDA POR PREFIJO ───────────────────────
-- Los `_like` los crea Postgres para que LIKE 'algo%' use índice en columnas
-- varchar. Django los genera siempre; sin ellos funciona igual, solo más lento.
CREATE INDEX "pago_id_pago_567a41aa_like" ON "pago" ("id_pago" varchar_pattern_ops);
CREATE INDEX "pago_referencia_externa_ff20d48b_like" ON "pago" ("referencia_externa" varchar_pattern_ops);
CREATE INDEX "pago_confirmado_por_id_20e99b19" ON "pago" ("confirmado_por_id");
CREATE INDEX "pago_confirmado_por_id_20e99b19_like" ON "pago" ("confirmado_por_id" varchar_pattern_ops);
CREATE INDEX "pago_id_empresa_422958ca" ON "pago" ("id_empresa");
CREATE INDEX "pago_id_empresa_422958ca_like" ON "pago" ("id_empresa" varchar_pattern_ops);
CREATE INDEX "pago_id_plan_872ec45d" ON "pago" ("id_plan");

CREATE INDEX "solicitud_premium_id_solicitud_34547013_like" ON "solicitud_premium" ("id_solicitud" varchar_pattern_ops);
CREATE INDEX "solicitud_premium_id_empresa_45f5df51" ON "solicitud_premium" ("id_empresa");
CREATE INDEX "solicitud_premium_id_empresa_45f5df51_like" ON "solicitud_premium" ("id_empresa" varchar_pattern_ops);
CREATE INDEX "solicitud_premium_id_pago_7986ddd0" ON "solicitud_premium" ("id_pago");
CREATE INDEX "solicitud_premium_id_pago_7986ddd0_like" ON "solicitud_premium" ("id_pago" varchar_pattern_ops);
CREATE INDEX "solicitud_premium_id_plan_b7324e3b" ON "solicitud_premium" ("id_plan");


-- ── 7. REGISTRAR LA MIGRACIÓN (equivale a `migrate --fake`) ─────────────────
-- Sin esto Django cree que 0009 sigue pendiente y va a fallar al aplicarla.
INSERT INTO django_migrations (app, name, applied)
VALUES ('base_datos', '0009_pago_solicitudpremium_suscripcion_empresa', NOW());


COMMIT;


-- =============================================================================
--  DESHACER (solo si ya hiciste COMMIT y necesitas volver atrás)
-- =============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS "solicitud_premium";
-- DROP TABLE IF EXISTS "pago";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "descuento_porcentaje";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "estado_suscripcion";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "fecha_vencimiento";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "razon_social";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "giro";
-- ALTER TABLE "empresa" DROP COLUMN IF EXISTS "direccion";
-- ALTER TABLE "empresa" ADD COLUMN "fecha_pago" timestamp with time zone NULL;
-- DELETE FROM django_migrations
--  WHERE app = 'base_datos'
--    AND name = '0009_pago_solicitudpremium_suscripcion_empresa';
-- COMMIT;

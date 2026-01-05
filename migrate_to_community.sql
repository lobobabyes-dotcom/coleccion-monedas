-- ============================================================================
-- MIGRATION SCRIPT - Community Platform Features
-- Fecha: 2026-01-05
-- Descripción: Añade funcionalidad de plataforma comunitaria con moderación
-- ============================================================================

-- IMPORTANTE: Este script debe ejecutarse en la base de datos Neon PostgreSQL
-- para actualizar el esquema existente con las nuevas funcionalidades

-- ============================================================================
-- PASO 1: Añadir columna de popularidad a catalogo_maestro
-- ============================================================================

-- Añadir columna popularidad si no existe
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'catalogo_maestro' 
        AND column_name = 'popularidad'
    ) THEN
        ALTER TABLE catalogo_maestro 
        ADD COLUMN popularidad INTEGER DEFAULT 0;
        
        -- Añadir constraint
        ALTER TABLE catalogo_maestro 
        ADD CONSTRAINT check_popularidad CHECK (popularidad >= 0);
        
        RAISE NOTICE 'Columna popularidad añadida a catalogo_maestro';
    ELSE
        RAISE NOTICE 'Columna popularidad ya existe en catalogo_maestro';
    END IF;
END $$;

-- ============================================================================
-- PASO 2: Crear tabla de solicitudes_catalogo
-- ============================================================================

CREATE TABLE IF NOT EXISTS solicitudes_catalogo (
    id_solicitud INTEGER PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    pais VARCHAR(100) NOT NULL,
    anio INTEGER NOT NULL,
    material VARCHAR(100) NOT NULL,
    peso_gramos DECIMAL(10, 2),
    diametro_mm DECIMAL(10, 2),
    foto_generica_url VARCHAR(500),
    usuario_solicitante INTEGER NOT NULL,
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_usuario_solicitante FOREIGN KEY (usuario_solicitante) 
        REFERENCES usuarios(id_usuario) 
        ON DELETE CASCADE,
    
    CONSTRAINT check_anio_solicitud CHECK (anio > 0 AND anio <= 2100)
);

-- ============================================================================
-- PASO 3: Crear índices para mejorar rendimiento
-- ============================================================================

-- Índice para popularidad (solo si no existe)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_indexes 
        WHERE tablename = 'catalogo_maestro' 
        AND indexname = 'idx_catalogo_popularidad'
    ) THEN
        CREATE INDEX idx_catalogo_popularidad ON catalogo_maestro(popularidad DESC);
        RAISE NOTICE 'Índice idx_catalogo_popularidad creado';
    ELSE
        RAISE NOTICE 'Índice idx_catalogo_popularidad ya existe';
    END IF;
END $$;

-- Índice para fecha de solicitud
CREATE INDEX IF NOT EXISTS idx_solicitudes_fecha 
ON solicitudes_catalogo(fecha_solicitud DESC);

-- ============================================================================
-- PASO 4: Actualizar popularidad de monedas existentes (opcional)
-- ============================================================================

-- Calcular popularidad basada en colecciones existentes
UPDATE catalogo_maestro cm
SET popularidad = (
    SELECT COUNT(*)
    FROM coleccion_usuario cu
    WHERE cu.id_moneda = cm.id_moneda
)
WHERE popularidad = 0;

-- ============================================================================
-- PASO 5: Verificación de la migración
-- ============================================================================

-- Mostrar resumen de cambios
DO $$
DECLARE
    count_solicitudes INTEGER;
    count_with_popularidad INTEGER;
BEGIN
    -- Contar solicitudes pendientes
    SELECT COUNT(*) INTO count_solicitudes FROM solicitudes_catalogo;
    
    -- Contar monedas con popularidad
    SELECT COUNT(*) INTO count_with_popularidad 
    FROM catalogo_maestro 
    WHERE popularidad > 0;
    
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRACIÓN COMPLETADA EXITOSAMENTE';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Tabla solicitudes_catalogo: creada';
    RAISE NOTICE 'Columna popularidad: añadida';
    RAISE NOTICE 'Índices: creados';
    RAISE NOTICE 'Solicitudes pendientes: %', count_solicitudes;
    RAISE NOTICE 'Monedas con popularidad > 0: %', count_with_popularidad;
    RAISE NOTICE '============================================';
END $$;

-- ============================================================================
-- FIN DE LA MIGRACIÓN
-- ============================================================================

-- Para ejecutar este script en Neon:
-- 1. Accede a tu proyecto en Neon.tech
-- 2. Ve al SQL Editor
-- 3. Copia y pega este script completo
-- 4. Haz clic en "Run" para ejecutar
-- 5. Verifica que veas el mensaje "MIGRACIÓN COMPLETADA EXITOSAMENTE"

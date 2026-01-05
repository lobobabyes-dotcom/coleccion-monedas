-- ============================================================================
-- MIGRACIÓN PROFESIONAL CON RIGOR ACADÉMICO
-- Fecha: 2026-01-05
-- Descripción: Base de datos numismática con distinción entre datos oficiales
--              y estimaciones históricas
-- ============================================================================

-- ============================================================================
-- FASE 1: Añadir Columnas Técnicas con Flag de Estimación
-- ============================================================================

-- Tirada (mintage/circulation)
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS tirada BIGINT DEFAULT NULL;

COMMENT ON COLUMN catalogo_maestro.tirada IS 'Cantidad acuñada. NULL si es desconocida';

-- Ceca (mint mark)
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS ceca VARCHAR(50) DEFAULT NULL;

COMMENT ON COLUMN catalogo_maestro.ceca IS 'Casa de moneda (Mo=México, L=Lima, S=Sevilla, P=Philadelphia, etc.)';

-- Pureza del metal (fineness)
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS pureza DECIMAL(5, 3) DEFAULT NULL;

COMMENT ON COLUMN catalogo_maestro.pureza IS 'Ley del metal (0.999, 0.925, 0.917, etc.)';

-- Forma de la moneda
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS forma VARCHAR(50) DEFAULT 'Redonda';

COMMENT ON COLUMN catalogo_maestro.forma IS 'Redonda, Cuadrada, Octogonal, Irregular, Macuquina';

-- Tipo de canto
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS canto VARCHAR(100) DEFAULT NULL;

COMMENT ON COLUMN catalogo_maestro.canto IS 'Estriado, Liso, Con leyenda, Cordoncillo, Grabado';

-- ⚠️ BANDERA DE RIGOR ACADÉMICO
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS es_estimacion BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN catalogo_maestro.es_estimacion IS 'TRUE = Datos estimados/aproximados. FALSE = Datos oficiales verificados';

-- ============================================================================
-- FASE 2: Índices para Búsquedas Eficientes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_catalogo_ceca ON catalogo_maestro(ceca);
CREATE INDEX IF NOT EXISTS idx_catalogo_pureza ON catalogo_maestro(pureza);
CREATE INDEX IF NOT EXISTS idx_catalogo_tirada ON catalogo_maestro(tirada DESC);
CREATE INDEX IF NOT EXISTS idx_catalogo_estimacion ON catalogo_maestro(es_estimacion);

-- Índice compuesto para filtros avanzados
CREATE INDEX IF NOT EXISTS idx_catalogo_pais_anio_material 
ON catalogo_maestro(pais, anio, material);

-- ============================================================================
-- FASE 3: Vista Profesional con Clasificación de Rareza
-- ============================================================================

CREATE OR REPLACE VIEW vista_catalogo_profesional AS
SELECT 
    id_moneda,
    nombre,
    pais,
    anio,
    material,
    peso_gramos,
    diametro_mm,
    tirada,
    ceca,
    pureza,
    forma,
    canto,
    popularidad,
    es_estimacion,
    foto_generica_url,
    -- Clasificación de rareza basada en tirada
    CASE 
        WHEN tirada IS NULL THEN 'Desconocida'
        WHEN tirada < 1000 THEN 'Extremadamente Rara (R8)'
        WHEN tirada < 10000 THEN 'Muy Rara (R7)'
        WHEN tirada < 50000 THEN 'Rara (R6)'
        WHEN tirada < 100000 THEN 'Escasa (R5)'
        WHEN tirada < 500000 THEN 'Poco Común (R4)'
        WHEN tirada < 1000000 THEN 'Común (R3)'
        WHEN tirada < 10000000 THEN 'Muy Común (R2)'
        ELSE 'Abundante (R1)'
    END AS clasificacion_rareza,
    -- Tipo de metal principal
    CASE 
        WHEN material ILIKE '%oro%' OR material ILIKE '%gold%' THEN 'Oro'
        WHEN material ILIKE '%plata%' OR material ILIKE '%silver%' OR material ILIKE '%ag%' THEN 'Plata'
        WHEN material ILIKE '%cobre%' OR material ILIKE '%copper%' THEN 'Cobre'
        WHEN material ILIKE '%bronce%' OR material ILIKE '%bronze%' THEN 'Bronce'
        WHEN material ILIKE '%bimetalica%' OR material ILIKE '%bimetallic%' THEN 'Bimetálica'
        ELSE 'Otro'
    END AS tipo_metal,
    -- Indicador de calidad de datos
    CASE 
        WHEN es_estimacion = FALSE AND tirada IS NOT NULL AND pureza IS NOT NULL THEN 'Datos Completos Verificados'
        WHEN es_estimacion = FALSE THEN 'Datos Oficiales Parciales'
        WHEN es_estimacion = TRUE THEN 'Datos Estimados'
        ELSE 'Información Limitada'
    END AS calidad_informacion
FROM catalogo_maestro
ORDER BY popularidad DESC, anio DESC;

-- ============================================================================
-- FASE 4: Verificación de Migración
-- ============================================================================

DO $$
DECLARE
    col_count INTEGER;
    vista_exists BOOLEAN;
BEGIN
    -- Contar columnas nuevas
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'catalogo_maestro'
    AND column_name IN ('tirada', 'ceca', 'pureza', 'forma', 'canto', 'es_estimacion');
    
    -- Verificar vista
    SELECT EXISTS (
        SELECT FROM information_schema.views 
        WHERE table_name = 'vista_catalogo_profesional'
    ) INTO vista_exists;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'MIGRACIÓN A BASE DE DATOS NUMISMÁTICA PROFESIONAL';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Columnas técnicas añadidas: % de 6', col_count;
    RAISE NOTICE 'Vista profesional creada: %', CASE WHEN vista_exists THEN 'SI' ELSE 'NO' END;
    
    IF col_count = 6 AND vista_exists THEN
        RAISE NOTICE '';
        RAISE NOTICE '✅ MIGRACIÓN COMPLETADA EXITOSAMENTE';
        RAISE NOTICE '';
        RAISE NOTICE '📊 Nuevas Capacidades:';
        RAISE NOTICE '   • Tirada oficial vs estimada';
        RAISE NOTICE '   • Clasificación de rareza automática';
        RAISE NOTICE '   • Marcas de ceca históricas';
        RAISE NOTICE '   • Pureza de metales preciosos';
        RAISE NOTICE '   • Rigor académico con flag de estimación';
    ELSE
        RAISE WARNING '⚠️  Verificar: Columnas=%  Vista=%', col_count, vista_exists;
    END IF;
    
    RAISE NOTICE '============================================================';
END $$;

-- ============================================================================
-- COMANDOS DE MANTENIMIENTO (OPCIONAL)
-- ============================================================================

-- Para limpiar completamente la tabla antes de importación masiva:
-- TRUNCATE TABLE catalogo_maestro RESTART IDENTITY CASCADE;

-- Para ver estadísticas de estimaciones:
-- SELECT 
--     es_estimacion,
--     COUNT(*) as cantidad,
--     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as porcentaje
-- FROM catalogo_maestro
-- GROUP BY es_estimacion;

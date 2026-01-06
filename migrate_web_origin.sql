-- ============================================================================
-- MIGRATION: Add Web Origin Tracking
-- Fecha: 2026-01-05
-- Descripción: Añade columna para rastrear monedas importadas desde búsqueda web
-- ============================================================================

-- Añadir columna origen_web
ALTER TABLE catalogo_maestro 
ADD COLUMN IF NOT EXISTS origen_web BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN catalogo_maestro.origen_web IS 
'TRUE = Importada desde búsqueda web (Wikipedia/DuckDuckGo). FALSE = Entrada manual o datos históricos';

-- Crear índice
CREATE INDEX IF NOT EXISTS idx_catalogo_origen_web ON catalogo_maestro(origen_web);

-- Verificación
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRACIÓN: Web Origin Tracking';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Columna origen_web añadida exitosamente';
    RAISE NOTICE 'Índice creado para búsquedas eficientes';
    RAISE NOTICE '============================================';
END $$;

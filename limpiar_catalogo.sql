-- ============================================================================
-- SCRIPT DE LIMPIEZA COMPLETA PARA NUEVA IMPORTACIÓN
-- ============================================================================
-- ⚠️  ADVERTENCIA: Este script borrará TODOS los datos del catálogo
-- Solo ejecutar si estás seguro de querer empezar desde cero
-- ============================================================================

BEGIN;

-- Paso 1: Eliminar dependencias en otras tablas
TRUNCATE TABLE ventas CASCADE;
TRUNCATE TABLE solicitudes_catalogo CASCADE;
TRUNCATE TABLE coleccion_usuario CASCADE;

-- Paso 2: Limpiar el catálogo maestro y reiniciar sequence
TRUNCATE TABLE catalogo_maestro RESTART IDENTITY CASCADE;

-- Paso 3: Verificar
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'LIMPIEZA COMPLETADA';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Tabla catalogo_maestro: VACÍA';
    RAISE NOTICE 'Tabla coleccion_usuario: VACÍA';
    RAISE NOTICE 'Tabla ventas: VACÍA';
    RAISE NOTICE 'Tabla solicitudes_catalogo: VACÍA';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Base de datos lista para importación masiva';
    RAISE NOTICE '============================================';
END $$;

COMMIT;

-- Verificar que las tablas están vacías
SELECT 
    'catalogo_maestro' as tabla, COUNT(*) as registros FROM catalogo_maestro
UNION ALL
SELECT 
    'coleccion_usuario', COUNT(*) FROM coleccion_usuario
UNION ALL
SELECT 
    'ventas', COUNT(*) FROM ventas
UNION ALL
SELECT 
    'solicitudes_catalogo', COUNT(*) FROM solicitudes_catalogo;

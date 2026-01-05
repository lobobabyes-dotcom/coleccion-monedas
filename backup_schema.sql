-- ============================================================================
-- BACKUP SCHEMA - Base de Datos ColeccionMonedas
-- Fecha de creación: 2026-01-04
-- ============================================================================

-- Eliminar tablas si existen (para poder recrear desde cero)
DROP TABLE IF EXISTS ventas CASCADE;
DROP TABLE IF EXISTS coleccion_usuario CASCADE;
DROP TABLE IF EXISTS catalogo_maestro CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- ============================================================================
-- TABLA: usuarios
-- Descripción: Información de los usuarios/coleccionistas
-- ============================================================================
CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY,
    nombre VARCHAR(100),
    email VARCHAR(100),
    fecha_registro DATE DEFAULT CURRENT_DATE
);

-- ============================================================================
-- TABLA: catalogo_maestro
-- Descripción: Catálogo maestro de monedas con sus especificaciones técnicas
-- ============================================================================
CREATE TABLE catalogo_maestro (
    id_moneda INTEGER PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    pais VARCHAR(100) NOT NULL,
    anio INTEGER NOT NULL,
    material VARCHAR(100) NOT NULL,
    peso_gramos DECIMAL(10, 2),
    diametro_mm DECIMAL(10, 2),
    foto_generica_url VARCHAR(500),
    popularidad INTEGER DEFAULT 0,
    CONSTRAINT check_anio CHECK (anio > 0 AND anio <= 2100),
    CONSTRAINT check_popularidad CHECK (popularidad >= 0)
);

-- ============================================================================
-- TABLA: coleccion_usuario
-- Descripción: Monedas adquiridas por los usuarios
-- ============================================================================
CREATE TABLE coleccion_usuario (
    id_item INTEGER PRIMARY KEY,
    id_usuario INTEGER NOT NULL,
    id_moneda INTEGER NOT NULL,
    estado_conservacion VARCHAR(50) NOT NULL,
    fecha_compra DATE NOT NULL,
    precio_compra DECIMAL(10, 2) NOT NULL,
    
    CONSTRAINT fk_usuario FOREIGN KEY (id_usuario) 
        REFERENCES usuarios(id_usuario) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_moneda FOREIGN KEY (id_moneda) 
        REFERENCES catalogo_maestro(id_moneda) 
        ON DELETE RESTRICT,
    
    CONSTRAINT check_precio_compra CHECK (precio_compra >= 0)
);

-- ============================================================================
-- TABLA: ventas
-- Descripción: Registro de ventas de monedas de la colección
-- ============================================================================
CREATE TABLE ventas (
    id_venta INTEGER PRIMARY KEY,
    id_item INTEGER NOT NULL UNIQUE,
    fecha_venta DATE NOT NULL,
    precio_venta DECIMAL(10, 2) NOT NULL,
    comprador VARCHAR(200),
    gastos_envio DECIMAL(10, 2) DEFAULT 0,
    comision_plataforma DECIMAL(10, 2) DEFAULT 0,
    
    CONSTRAINT fk_item FOREIGN KEY (id_item) 
        REFERENCES coleccion_usuario(id_item) 
        ON DELETE CASCADE,
    
    CONSTRAINT check_precio_venta CHECK (precio_venta >= 0),
    CONSTRAINT check_gastos_envio CHECK (gastos_envio >= 0),
    CONSTRAINT check_comision CHECK (comision_plataforma >= 0)
);

-- ============================================================================
-- TABLA: solicitudes_catalogo
-- Descripción: Solicitudes de usuarios para añadir nuevas monedas al catálogo
-- ============================================================================
CREATE TABLE solicitudes_catalogo (
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
-- ÍNDICES para mejorar el rendimiento
-- ============================================================================

-- Índices en catalogo_maestro
CREATE INDEX idx_catalogo_nombre ON catalogo_maestro(nombre);
CREATE INDEX idx_catalogo_pais ON catalogo_maestro(pais);
CREATE INDEX idx_catalogo_anio ON catalogo_maestro(anio);
CREATE INDEX idx_catalogo_material ON catalogo_maestro(material);
CREATE INDEX idx_catalogo_popularidad ON catalogo_maestro(popularidad DESC);

-- Índices en coleccion_usuario
CREATE INDEX idx_coleccion_usuario ON coleccion_usuario(id_usuario);
CREATE INDEX idx_coleccion_moneda ON coleccion_usuario(id_moneda);
CREATE INDEX idx_coleccion_fecha ON coleccion_usuario(fecha_compra);

-- Índices en ventas
CREATE INDEX idx_ventas_fecha ON ventas(fecha_venta);
CREATE INDEX idx_ventas_item ON ventas(id_item);

-- ============================================================================
-- DATOS DE EJEMPLO (OPCIONAL - Usuario por defecto)
-- ============================================================================

-- Insertar usuario por defecto (ID 100 usado en la aplicación)
INSERT INTO usuarios (id_usuario, nombre, email, fecha_registro)
VALUES (100, 'Usuario Principal', 'usuario@coleccion.com', CURRENT_DATE)
ON CONFLICT (id_usuario) DO NOTHING;

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista completa de monedas con información combinada
CREATE OR REPLACE VIEW vista_coleccion_completa AS
SELECT 
    cu.id_item,
    cu.id_usuario,
    cm.id_moneda,
    cm.nombre AS nombre_moneda,
    cm.pais,
    cm.anio,
    cm.material,
    cm.peso_gramos,
    cm.diametro_mm,
    cu.estado_conservacion,
    cu.fecha_compra,
    cu.precio_compra,
    v.precio_venta,
    v.fecha_venta,
    v.comprador,
    v.gastos_envio,
    v.comision_plataforma,
    CASE 
        WHEN v.id_venta IS NOT NULL THEN 'Vendida'
        ELSE 'En Cartera'
    END AS estado_venta,
    CASE 
        WHEN v.id_venta IS NOT NULL THEN 
            v.precio_venta - cu.precio_compra - COALESCE(v.gastos_envio, 0) - COALESCE(v.comision_plataforma, 0)
        ELSE NULL
    END AS ganancia_realizada
FROM coleccion_usuario cu
INNER JOIN catalogo_maestro cm ON cu.id_moneda = cm.id_moneda
LEFT JOIN ventas v ON cu.id_item = v.id_item;

-- Vista de estadísticas por usuario
CREATE OR REPLACE VIEW vista_estadisticas_usuario AS
SELECT 
    u.id_usuario,
    u.nombre,
    COUNT(DISTINCT cu.id_item) AS total_monedas,
    COUNT(DISTINCT v.id_venta) AS monedas_vendidas,
    COUNT(DISTINCT cu.id_item) - COUNT(DISTINCT v.id_venta) AS monedas_en_cartera,
    COALESCE(SUM(cu.precio_compra), 0) AS inversion_total,
    COALESCE(SUM(CASE WHEN v.id_venta IS NULL THEN cu.precio_compra ELSE 0 END), 0) AS inversion_activa,
    COALESCE(SUM(v.precio_venta), 0) AS ingresos_ventas,
    COALESCE(SUM(v.precio_venta - cu.precio_compra - COALESCE(v.gastos_envio, 0) - COALESCE(v.comision_plataforma, 0)), 0) AS ganancia_total
FROM usuarios u
LEFT JOIN coleccion_usuario cu ON u.id_usuario = cu.id_usuario
LEFT JOIN ventas v ON cu.id_item = v.id_item
GROUP BY u.id_usuario, u.nombre;

-- ============================================================================
-- FUNCIONES AUXILIARES
-- ============================================================================

-- Función para obtener el siguiente ID disponible en catalogo_maestro
CREATE OR REPLACE FUNCTION get_next_id_catalogo()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(MAX(id_moneda), 0) + 1 FROM catalogo_maestro;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener el siguiente ID disponible en coleccion_usuario
CREATE OR REPLACE FUNCTION get_next_id_item()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(MAX(id_item), 0) + 1 FROM coleccion_usuario;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener el siguiente ID disponible en ventas
CREATE OR REPLACE FUNCTION get_next_id_venta()
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(MAX(id_venta), 0) + 1 FROM ventas;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMENTARIOS EN LAS TABLAS
-- ============================================================================

COMMENT ON TABLE catalogo_maestro IS 'Catálogo maestro de monedas con especificaciones técnicas';
COMMENT ON TABLE coleccion_usuario IS 'Monedas adquiridas por los coleccionistas';
COMMENT ON TABLE ventas IS 'Registro de ventas realizadas';
COMMENT ON TABLE usuarios IS 'Información de usuarios/coleccionistas';

COMMENT ON COLUMN catalogo_maestro.peso_gramos IS 'Peso en gramos de la moneda';
COMMENT ON COLUMN catalogo_maestro.diametro_mm IS 'Diámetro en milímetros de la moneda';
COMMENT ON COLUMN coleccion_usuario.estado_conservacion IS 'Estado según escala numismática (MBC, EBC, SC, etc.)';
COMMENT ON COLUMN ventas.comision_plataforma IS 'Comisión cobrada por plataforma de venta';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

-- Para restaurar este backup:
-- 1. Crear base de datos: CREATE DATABASE ColeccionMonedas;
-- 2. Conectar a la base de datos: \c ColeccionMonedas
-- 3. Ejecutar este script: \i backup_schema.sql

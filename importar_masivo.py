"""
Script de Importación Masiva a Neon PostgreSQL
Importa el CSV generado por generador_historico.py
Usa execute_values para máxima eficiencia
"""

import csv
import psycopg2
from psycopg2.extras import execute_values
import sys
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

CSV_FILENAME = 'monedas_historicas.csv'
BATCH_SIZE = 500  # Procesar en lotes de 500 monedas

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def leer_connection_string():
    """Lee el connection string desde secrets.toml"""
    try:
        secrets_path = Path('.streamlit/secrets.toml')
        if not secrets_path.exists():
            print("❌ Error: No se encontró .streamlit/secrets.toml")
            sys.exit(1)
        
        with open(secrets_path, 'r', encoding='utf-8') as f:
            for line in f:
                if 'DATABASE_URL' in line and '=' in line:
                    # Extraer el valor entre comillas
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        value = parts[1].strip().strip('"').strip("'")
                        return value
        
        print("❌ Error: No se encontró DATABASE_URL en secrets.toml")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo secrets: {e}")
        sys.exit(1)

def leer_csv(filename):
    """Lee el archivo CSV y retorna lista de monedas"""
    monedas = []
    try:
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convertir valores vacíos a None
                moneda = {}
                for key, value in row.items():
                    if value == '' or value == 'None':
                        moneda[key] = None
                    elif key in ['anio', 'tirada']:
                        moneda[key] = int(value) if value and value != 'None' else None
                    elif key in ['peso_gramos', 'diametro_mm', 'pureza']:
                        moneda[key] = float(value) if value and value != 'None' else None
                    elif key == 'es_estimacion':
                        moneda[key] = value.lower() == 'true' if value else False
                    else:
                        moneda[key] = value
                monedas.append(moneda)
        
        return monedas
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{filename}'")
        print("   Ejecuta primero: python generador_historico.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        sys.exit(1)

def crear_conexion(connection_string):
    """Crea conexión a Neon PostgreSQL"""
    try:
        conn = psycopg2.connect(connection_string, options='-c client_encoding=UTF8')
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        sys.exit(1)

def verificar_schema(conn):
    """Verifica que las columnas necesarias existan"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'catalogo_maestro' 
            AND column_name IN ('tirada', 'ceca', 'pureza', 'forma', 'canto', 'es_estimacion')
        """)
        columnas = [row[0] for row in cursor.fetchall()]
        
        if len(columnas) != 6:
            print("❌ Error: Faltan columnas en la base de datos")
            print("   Columnas encontradas:", columnas)
            print("\n   Debes ejecutar primero:")
            print("   1. Abre Neon SQL Editor")
            print("   2. Ejecuta migrate_to_professional.sql")
            cursor.close()
            return False
        
        cursor.close()
        return True
    except Exception as e:
        print(f"❌ Error verificando schema: {e}")
        cursor.close()
        return False

def importar_lote(conn, monedas_lote):
    """Importa un lote de monedas usando execute_values"""
    cursor = conn.cursor()
    
    try:
        # Obtener el próximo ID disponible
        cursor.execute("SELECT COALESCE(MAX(id_moneda), 0) + 1 FROM catalogo_maestro")
        next_id = cursor.fetchone()[0]
        
        # Preparar datos para inserción
        valores = []
        for i, moneda in enumerate(monedas_lote):
            valores.append((
                next_id + i,
                moneda['nombre'],
                moneda['pais'],
                moneda['anio'],
                moneda['material'],
                moneda['peso_gramos'],
                moneda['diametro_mm'],
                moneda.get('foto_generica_url'),
                0,  # popularidad inicial
                moneda.get('tirada'),
                moneda.get('ceca'),
                moneda.get('pureza'),
                moneda.get('forma', 'Redonda'),
                moneda.get('canto'),
                moneda.get('es_estimacion', False)
            ))
        
        # Inserción masiva con ON CONFLICT
        insert_query = """
            INSERT INTO catalogo_maestro 
            (id_moneda, nombre, pais, anio, material, peso_gramos, diametro_mm, 
             foto_generica_url, popularidad, tirada, ceca, pureza, forma, canto, es_estimacion)
            VALUES %s
            ON CONFLICT (id_moneda) DO NOTHING
        """
        
        execute_values(cursor, insert_query, valores)
        insertados = cursor.rowcount
        
        conn.commit()
        cursor.close()
        return insertados
        
    except Exception as e:
        print(f"\n❌ Error en lote: {e}")
        conn.rollback()
        cursor.close()
        return 0

# ============================================================================
# FUNCIÓN PRINCIPAL DE IMPORTACIÓN
# ============================================================================

def importar_masivo():
    """Función principal de importación"""
    print("=" * 70)
    print("IMPORTACIÓN MASIVA A NEON POSTGRESQL")
    print("=" * 70)
    
    # 1. Leer CSV
    print(f"\n📄 Leyendo {CSV_FILENAME}...")
    monedas = leer_csv(CSV_FILENAME)
    print(f"   ✅ {len(monedas)} monedas cargadas desde CSV")
    
    # 2. Conectar a Neon
    print("\n🔌 Conectando a Neon PostgreSQL...")
    connection_string = leer_connection_string()
    conn = crear_conexion(connection_string)
    print("   ✅ Conexión establecida")
    
    # 3. Verificar schema
    print("\n🔍 Verificando estructura de la base de datos...")
    if not verificar_schema(conn):
        conn.close()
        sys.exit(1)
    print("   ✅ Schema verificado")
    
    # 4. Importar en lotes
    print(f"\n📊 Importando {len(monedas)} monedas en lotes de {BATCH_SIZE}...")
    print("=" * 70)
    
    total_insertados = 0
    num_lotes = (len(monedas) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(monedas), BATCH_SIZE):
        lote = monedas[i:i + BATCH_SIZE]
        lote_num = (i // BATCH_SIZE) + 1
        
        print(f"\n   Lote {lote_num}/{num_lotes}: Procesando {len(lote)} monedas...")
        insertados = importar_lote(conn, lote)
        total_insertados += insertados
        
        # Mostrar progreso
        progreso = (i + len(lote)) / len(monedas) * 100
        print(f"   ✅ {insertados} monedas insertadas | Progreso: {progreso:.1f}%")
    
    # 5. Estadísticas finales
    print("\n" + "=" * 70)
    print("IMPORTACIÓN COMPLETADA")
    print("=" * 70)
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM catalogo_maestro")
    total_en_bd = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM catalogo_maestro 
        WHERE tirada IS NOT NULL
    """)
    con_tirada = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT pais, COUNT(*) as total
        FROM catalogo_maestro
        GROUP BY pais
        ORDER BY total DESC
        LIMIT 5
    """)
    top_paises = cursor.fetchall()
    
    print(f"\n📊 Estadísticas:")
    print(f"   • Total de monedas insertadas: {total_insertados}")
    print(f"   • Total en base de datos: {total_en_bd}")
    print(f"   • Monedas con tirada: {con_tirada}")
    
    print(f"\n🌍 Top 5 países:")
    for pais, total in top_paises:
        print(f"   • {pais}: {total} monedas")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Importación finalizada exitosamente!")
    print("\n🚀 Siguiente paso:")
    print("   Actualiza tu app en Streamlit Cloud con los nuevos datos")

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == '__main__':
    try:
        importar_masivo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Importación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

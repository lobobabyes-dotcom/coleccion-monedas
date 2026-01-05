import psycopg2
import sys

# Este script verifica si la migración se ejecutó correctamente en Neon

try:
    # Leer connection string de secrets
    with open('.streamlit/secrets.toml', 'r', encoding='utf-8') as f:
        content = f.read()
        # Extraer DATABASE_URL
        for line in content.split('\n'):
            if 'DATABASE_URL' in line:
                connection_string = line.split('=')[1].strip().strip('"')
                break
    
    print("Conectando a Neon PostgreSQL...")
    conn = psycopg2.connect(connection_string, options='-c client_encoding=UTF8')
    cursor = conn.cursor()
    
    print("\n✅ Conexión exitosa!")
    print("\n" + "="*60)
    print("VERIFICACIÓN DE MIGRACIÓN")
    print("="*60)
    
    # 1. Verificar columna popularidad
    print("\n1. Verificando columna 'popularidad' en catalogo_maestro...")
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'catalogo_maestro' AND column_name = 'popularidad'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✅ Columna encontrada: {result[0]} ({result[1]}, default: {result[2]})")
    else:
        print("   ❌ Columna 'popularidad' NO existe")
        print("   ⚠️  DEBES EJECUTAR migrate_to_community.sql en Neon")
    
    # 2. Verificar tabla solicitudes_catalogo
    print("\n2. Verificando tabla 'solicitudes_catalogo'...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'solicitudes_catalogo'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✅ Tabla encontrada: {result[0]}")
        
        # Contar solicitudes pendientes
        cursor.execute("SELECT COUNT(*) FROM solicitudes_catalogo")
        count = cursor.fetchone()[0]
        print(f"   📊 Solicitudes pendientes: {count}")
    else:
        print("   ❌ Tabla 'solicitudes_catalogo' NO existe")
        print("   ⚠️  DEBES EJECUTAR migrate_to_community.sql en Neon")
    
    # 3. Verificar índice de popularidad
    print("\n3. Verificando índice 'idx_catalogo_popularidad'...")
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE indexname = 'idx_catalogo_popularidad'
    """)
    result = cursor.fetchone()
    if result:
        print(f"   ✅ Índice encontrado: {result[0]}")
    else:
        print("   ⚠️  Índice 'idx_catalogo_popularidad' no encontrado")
    
    # 4. Mostrar monedas con popularidad
    print("\n4. Monedas con popularidad > 0...")
    cursor.execute("""
        SELECT nombre, pais, popularidad
        FROM catalogo_maestro
        WHERE popularidad > 0
        ORDER BY popularidad DESC
        LIMIT 5
    """)
    results = cursor.fetchall()
    if results:
        for nombre, pais, pop in results:
            print(f"   🔥 {nombre} ({pais}) - Popularidad: {pop}")
    else:
        print("   📋 Ninguna moneda tiene popularidad aún")
    
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    
    cursor.execute("""
        SELECT 
            EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'catalogo_maestro' AND column_name = 'popularidad') as col_exists,
            EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'solicitudes_catalogo') as table_exists
    """)
    col_exists, table_exists = cursor.fetchone()
    
    if col_exists and table_exists:
        print("\n✅ MIGRACIÓN COMPLETA - Tu base de datos está actualizada")
        print("   Puedes hacer deploy a Streamlit Cloud")
    else:
        print("\n❌ MIGRACIÓN INCOMPLETA - Faltan cambios")
        print("\n📝 PASOS PARA COMPLETAR:")
        print("   1. Ve a https://console.neon.tech")
        print("   2. Abre el SQL Editor")
        print("   3. Copia el contenido de 'migrate_to_community.sql'")
        print("   4. Pégalo y ejecuta")
        print("   5. Verifica que veas 'MIGRACIÓN COMPLETADA EXITOSAMENTE'")
        print("   6. Vuelve a ejecutar este script para confirmar")
    
    cursor.close()
    conn.close()
    
except FileNotFoundError:
    print("❌ Error: No se encontró .streamlit/secrets.toml")
    print("   Verifica que el archivo exista")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)

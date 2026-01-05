import pg8000.native

try:
    # Conectar a la base de datos
    conn = pg8000.native.Connection(
        user="postgres",
        password="232425",
        host="127.0.0.1",
        port=5432,
        database="ColeccionMonedas"
    )
    
    print("✓ Conexión exitosa a la base de datos ColeccionMonedas")
    print()
    
    # Listar todas las tablas
    print("Tablas disponibles en la base de datos:")
    print("=" * 60)
    
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """
    
    tables = conn.run(query)
    
    if tables:
        for i, (table_name,) in enumerate(tables, 1):
            print(f"{i}. {table_name}")
            
            # Contar registros en cada tabla
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            try:
                count_result = conn.run(count_query)
                count = count_result[0][0]
                print(f"   → Tiene {count} registros")
            except Exception as e:
                print(f"   → Error al contar: {e}")
            print()
    else:
        print("No hay tablas en la base de datos")
    
    conn.close()
    print("✓ Conexión cerrada")
    
except Exception as e:
    print(f"✗ Error: {e}")

input("\nPresiona Enter para cerrar...")

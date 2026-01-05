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
    
    print("✓ Conexión exitosa a ColeccionMonedas")
    print()
    
    # Ver la estructura de la tabla Catalogo_Maestro
    print("Estructura de la tabla Catalogo_Maestro:")
    print("=" * 80)
    
    query = """
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'catalogo_maestro'
        ORDER BY ordinal_position
    """
    
    columns = conn.run(query)
    
    if columns:
        print(f"\n{'Columna':<30} {'Tipo':<20} {'Longitud':<10}")
        print("-" * 80)
        for col_name, data_type, max_length in columns:
            length_str = str(max_length) if max_length else "-"
            print(f"{col_name:<30} {data_type:<20} {length_str:<10}")
    else:
        print("No se encontraron columnas para catalogo_maestro")
        print("Intentando con mayúsculas...")
        
        # Intentar con mayúsculas
        query2 = """
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'Catalogo_Maestro'
            ORDER BY ordinal_position
        """
        columns2 = conn.run(query2)
        
        if columns2:
            print(f"\n{'Columna':<30} {'Tipo':<20} {'Longitud':<10}")
            print("-" * 80)
            for col_name, data_type, max_length in columns2:
                length_str = str(max_length) if max_length else "-"
                print(f"{col_name:<30} {data_type:<20} {length_str:<10}")
    
    # Intentar ver algunos datos de ejemplo
    print("\n" + "=" * 80)
    print("Primeros 3 registros de la tabla:")
    print("=" * 80)
    
    try:
        # Probar con minúsculas primero
        sample_query = "SELECT * FROM catalogo_maestro LIMIT 3"
        rows = conn.run(sample_query)
        
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"\nRegistro {i}:")
                print(row)
        else:
            print("La tabla está vacía")
            
    except Exception as e:
        # Si falla, probar con el nombre exacto que se ve en pgAdmin
        print(f"Intentando con 'Catalogo_Maestro' (mayúsculas)...")
        try:
            sample_query = 'SELECT * FROM "Catalogo_Maestro" LIMIT 3'
            rows = conn.run(sample_query)
            
            if rows:
                for i, row in enumerate(rows, 1):
                    print(f"\nRegistro {i}:")
                    print(row)
            else:
                print("La tabla está vacía")
        except Exception as e2:
            print(f"Error: {e2}")
    
    conn.close()
    print("\n✓ Conexión cerrada")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona Enter para cerrar...")

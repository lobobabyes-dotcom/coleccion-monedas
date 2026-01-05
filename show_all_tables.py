import pg8000.native

try:
    conn = pg8000.native.Connection(
        user="postgres",
        password="232425",
        host="127.0.0.1",
        port=5432,
        database="ColeccionMonedas"
    )
    
    print("=" * 80)
    print("ESTRUCTURA DE TODAS LAS TABLAS")
    print("=" * 80)
    
    tablas = ['catalogo_maestro', 'coleccion_usuario', 'historial_precios', 'ventas']
    
    for tabla in tablas:
        print(f"\n{'='*80}")
        print(f"TABLA: {tabla.upper()}")
        print(f"{'='*80}")
        
        # Obtener estructura
        query_estructura = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{tabla}'
            ORDER BY ordinal_position
        """
        
        columnas = conn.run(query_estructura)
        
        print("\nColumnas:")
        for col_name, data_type in columnas:
            print(f"  - {col_name} ({data_type})")
        
        # Obtener datos de ejemplo
        print("\nDatos de ejemplo:")
        try:
            query_datos = f"SELECT * FROM {tabla} LIMIT 2"
            rows = conn.run(query_datos)
            
            if rows:
                for i, row in enumerate(rows, 1):
                    print(f"\n  Registro {i}:")
                    for j, (col_name, _) in enumerate(columnas):
                        print(f"    {col_name}: {row[j]}")
            else:
                print("  (Sin datos)")
        except Exception as e:
            print(f"  Error al obtener datos: {e}")
    
    conn.close()
    print("\n" + "=" * 80)
    print("✓ Análisis completo")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

input("\nPresiona Enter para cerrar...")

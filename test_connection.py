import sys
import os

# Configurar variables de entorno ANTES de importar psycopg2
os.environ['PGCLIENTENCODING'] = 'UTF8'
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("Probando conexión a PostgreSQL...")
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print()

try:
    import psycopg2
    print("✓ psycopg2 importado correctamente")
    
    # Intentar conexión con IP numérica (evita resolución DNS)
    print("\nIntentando conectar con 127.0.0.1...")
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="ColeccionMonedas",
        user="postgres",
        password="postgres"
    )
    print("✓ Conexión exitosa!")
    
    # Probar consulta
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM monedas")
    count = cursor.fetchone()[0]
    print(f"✓ Base de datos tiene {count} monedas")
    
    # Probar consulta completa
    cursor.execute("""
        SELECT nombre, anio, estado, precio_compra, precio_venta 
        FROM monedas 
        LIMIT 3
    """)
    monedas = cursor.fetchall()
    print(f"\n✓ Primeras 3 monedas:")
    for i, moneda in enumerate(monedas, 1):
        print(f"  {i}. {moneda[0]} ({moneda[1]})")
    
    cursor.close()
    conn.close()
    print("\n✓ Conexión cerrada correctamente")
    print("\n¡TODO FUNCIONA! La base de datos está lista.")
    
except UnicodeDecodeError as e:
    print(f"\n✗ ERROR DE CODIFICACIÓN:")
    print(f"  {e}")
    print("\nEste error indica un problema con la configuración regional de Windows.")
    print("Posibles soluciones:")
    print("1. Reinstalar PostgreSQL seleccionando 'English' como idioma")
    print("2. Cambiar la configuración regional de Windows a inglés")
    print("3. Usar una herramienta alternativa como pgAdmin o DBeaver")
    
except Exception as e:
    print(f"\n✗ ERROR:")
    print(f"  Tipo: {type(e).__name__}")
    print(f"  Mensaje: {e}")

input("\nPresiona Enter para cerrar...")

import psycopg2

# Conexión a la base de datos
conn = psycopg2.connect(
    host="localhost",
    database="ColeccionMonedas",
    user="postgres",
    password="postgres",
    port="5432"
)

# Crear un cursor
cursor = conn.cursor()

# Ejecutar la consulta
query = """
SELECT nombre, anio, estado, precio_compra, precio_venta 
FROM monedas
"""

cursor.execute(query)

# Obtener todos los resultados
monedas = cursor.fetchall()

# Mostrar los resultados
print("=" * 80)
print("COLECCIÓN DE MONEDAS")
print("=" * 80)
print()

for moneda in monedas:
    nombre, anio, estado, precio_compra, precio_venta = moneda
    print(f"Moneda: {nombre}")
    print(f"Año: {anio}")
    print(f"Estado: {estado}")
    print(f"Precio de Compra: ${precio_compra:,.2f}")
    print(f"Precio de Venta: ${precio_venta:,.2f}")
    print("-" * 80)

print()
print(f"Total de monedas: {len(monedas)}")

# Cerrar cursor y conexión
cursor.close()
conn.close()

print("\n¡Conexión cerrada correctamente!")

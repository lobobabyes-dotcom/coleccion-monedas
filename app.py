import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import yfinance as yf
from datetime import datetime
from fpdf import FPDF
import wikipedia
from duckduckgo_search import DDGS

# Configuración de la página
st.set_page_config(
    page_title="Colección de Monedas",
    page_icon="🪙",
    layout="wide"
)

# Función para conectar a la base de datos usando psycopg2
def conectar_bd():
    try:
        # Obtener connection string de Streamlit secrets
        connection_string = st.secrets["connections"]["DATABASE_URL"]
        
        # Asegurar que el string es texto puro (no bytes)
        if isinstance(connection_string, bytes):
            connection_string = connection_string.decode('utf-8')
        
        # Conectar directamente con psycopg2 y forzar UTF-8
        conexion = psycopg2.connect(
            connection_string,
            options='-c client_encoding=UTF8'
        )
        return conexion, None
    except UnicodeDecodeError as e:
        return None, f"Error de codificación: {str(e)}"
    except Exception as e:
        return None, str(e)


# Función para obtener monedas del catálogo
def obtener_catalogo():
    conexion, error = conectar_bd()
    if conexion is None:
        return [], error
    
    try:
        cursor = conexion.cursor()
        query = """
            SELECT id_moneda, nombre, pais, anio
            FROM catalogo_maestro
            ORDER BY popularidad DESC, nombre ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conexion.close()
        return rows, None
    except Exception as e:
        if conexion:
            try:
                conexion.close()
            except:
                pass
        return [], str(e)

# Función para añadir una nueva moneda a la colección
def añadir_moneda(id_moneda, fecha_compra, precio_compra, estado):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        # Obtener el próximo id_item
        query_max_id = "SELECT COALESCE(MAX(id_item), 0) + 1 FROM coleccion_usuario"
        cursor.execute(query_max_id)
        result = cursor.fetchone()
        nuevo_id = result[0]
        
        # Insertar nueva moneda en la colección
        query_insert = """
            INSERT INTO coleccion_usuario 
            (id_item, id_usuario, id_moneda, estado_conservacion, fecha_compra, precio_compra)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(
            query_insert,
            (nuevo_id, 100, id_moneda, estado, fecha_compra, float(precio_compra))
        )
        
        # Incrementar popularidad de la moneda en el catálogo
        query_update_popularidad = """
            UPDATE catalogo_maestro 
            SET popularidad = popularidad + 1 
            WHERE id_moneda = %s
        """
        cursor.execute(query_update_popularidad, (id_moneda,))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)


# Función para añadir una nueva moneda al catálogo maestro
def crear_referencia_catalogo(nombre, pais, anio, material, peso_gramos, diametro_mm, foto_url=None, origen_web=False):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        # Obtener el próximo id_moneda
        query_max_id = "SELECT COALESCE(MAX(id_moneda), 0) + 1 FROM catalogo_maestro"
        cursor.execute(query_max_id)
        result = cursor.fetchone()
        nuevo_id = result[0]
        
        # Insertar nueva referencia en el catálogo
        query_insert = """
            INSERT INTO catalogo_maestro 
            (id_moneda, nombre, pais, anio, material, peso_gramos, diametro_mm, foto_generica_url, popularidad, origen_web)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(
            query_insert,
            (nuevo_id, nombre, pais, anio, material, 
             float(peso_gramos) if peso_gramos else None,
             float(diametro_mm) if diametro_mm else None,
             foto_url if foto_url else None)
        )
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# Función para obtener precios de mercado en tiempo real
def obtener_precios_mercado():
    try:
        # Obtener datos de Yahoo Finance
        oro = yf.Ticker('GC=F')  # Futuros de Oro
        plata = yf.Ticker('SI=F')  # Futuros de Plata
        
        # Intentar diferentes símbolos para EUR/USD
        try:
            eur_usd = yf.Ticker('EURUSD=X')  # Intentar este primero
            tasa_cambio = eur_usd.fast_info.get('lastPrice', eur_usd.info.get('regularMarketPrice', 0))
        except:
            eur_usd = yf.Ticker('EUR=X')  # Fallback
            tasa_cambio = eur_usd.fast_info.get('lastPrice', eur_usd.info.get('regularMarketPrice', 0))
        
        # Extraer precios actuales (en USD por onza troy)
        precio_oro_usd = oro.fast_info.get('lastPrice', oro.info.get('regularMarketPrice', 0))
        precio_plata_usd = plata.fast_info.get('lastPrice', plata.info.get('regularMarketPrice', 0))
        
        # Validación: si la tasa está muy baja, probablemente está invertida
        # Normalmente 1 EUR = 1.05-1.15 USD
        if tasa_cambio < 1.0 and tasa_cambio > 0:
            # Está invertida (USD/EUR en lugar de EUR/USD), invertir
            tasa_cambio = 1 / tasa_cambio
        
        # Si aún no tenemos una tasa válida, usar valor por defecto
        if tasa_cambio <= 0 or tasa_cambio > 2.0:
            tasa_cambio = 1.10  # Valor típico
        
        # Convertir de USD/onza troy a EUR/gramo
        # 1 onza troy = 31.1035 gramos
        # Para convertir USD a EUR: dividir por tasa_cambio (cuántos USD vale 1 EUR)
        
        oro_gramo_eur = (precio_oro_usd / tasa_cambio) / 31.1035 if precio_oro_usd > 0 and tasa_cambio > 0 else 0
        plata_gramo_eur = (precio_plata_usd / tasa_cambio) / 31.1035 if precio_plata_usd > 0 and tasa_cambio > 0 else 0
        
        return {
            'oro_gramo': oro_gramo_eur,
            'plata_gramo': plata_gramo_eur,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            # Debug info
            'oro_usd_onza': precio_oro_usd,
            'plata_usd_onza': precio_plata_usd,
            'eur_usd_rate': tasa_cambio
        }, None
    except Exception as e:
        return None, str(e)

# ============================================================================
# CLASE Y FUNCIÓN PARA GENERAR PDF
# ============================================================================

class PDF(FPDF):
    def header(self):
        # Encabezado
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Reporte de Boveda Numismatica', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        # Pie de página
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf(dataframe, valor_total, inversion_total):
    """
    Genera un PDF con el reporte de la colección
    """
    # Crear objeto PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Sección de Resumen Financiero
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Resumen Financiero', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 11)
    fecha_hoy = datetime.now().strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 8, f'Fecha del reporte: {fecha_hoy}', 0, 1)
    pdf.cell(0, 8, f'Numero de monedas en cartera: {len(dataframe)}', 0, 1)
    pdf.cell(0, 8, f'Inversion total: {inversion_total:.2f} EUR', 0, 1)
    pdf.cell(0, 8, f'Valor de mercado actual: {valor_total:.2f} EUR', 0, 1)
    
    ganancia = valor_total - inversion_total
    porcentaje = (ganancia / inversion_total * 100) if inversion_total > 0 else 0
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f'Ganancia no realizada: {ganancia:+.2f} EUR ({porcentaje:+.1f}%)', 0, 1)
    
    pdf.ln(5)
    
    # Tabla de monedas
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 10, 'Inventario de Monedas', 0, 1, 'L')
    pdf.ln(2)
    
    # Encabezados de tabla
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(70, 8, 'Moneda', 1, 0, 'C', True)
    pdf.cell(20, 8, 'Ano', 1, 0, 'C', True)
    pdf.cell(55, 8, 'Material', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Valor (EUR)', 1, 1, 'C', True)
    
    # Filas de datos
    pdf.set_font('Arial', '', 8)
    for index, row in dataframe.iterrows():
        nombre = str(row.get('Nombre de la Moneda', ''))[:35]  # Truncar si es muy largo
        anio = str(row.get('Año', ''))
        material = str(row.get('Material', ''))[:27]
        valor = row.get('Valor Estimado (€)', 0)
        
        pdf.cell(70, 7, nombre, 1, 0, 'L')
        pdf.cell(20, 7, anio, 1, 0, 'C')
        pdf.cell(55, 7, material, 1, 0, 'L')
        pdf.cell(35, 7, f'{float(valor):.2f}', 1, 1, 'R')
    
    # Devolver PDF como bytes
    return pdf.output(dest='S').encode('latin-1')

# Función para obtener los datos
def obtener_datos():
    conexion, error = conectar_bd()
    if conexion is None:
        return None, error
    
    try:
        cursor = conexion.cursor()
        # Query que combina todas las tablas
        query = """
            SELECT 
                cm.nombre AS nombre,
                cm.anio AS anio,
                cu.estado_conservacion AS estado,
                cu.precio_compra AS precio_compra,
                COALESCE(v.precio_venta, 0) AS precio_venta,
                cm.pais,
                cm.material,
                cu.fecha_compra,
                cm.foto_generica_url AS foto,
                cm.peso_gramos AS peso,
                cm.diametro_mm AS diametro,
                cm.tirada,
                cm.ceca,
                cm.pureza,
                cm.forma,
                cm.canto,
                cm.es_estimacion
            FROM catalogo_maestro cm
            LEFT JOIN coleccion_usuario cu ON cm.id_moneda = cu.id_moneda
            LEFT JOIN ventas v ON cu.id_item = v.id_item
            WHERE cu.id_item IS NOT NULL
            ORDER BY cm.anio DESC, cm.nombre
        """
        
        # Ejecutar la consulta
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convertir a DataFrame
        df = pd.DataFrame(
            rows,
            columns=[
                "Nombre de la Moneda", 
                "Año", 
                "Estado", 
                "Precio de Compra", 
                "Precio de Venta",
                "País",
                "Material",
                "Fecha de Compra",
                "Foto",
                "Peso (g)",
                "Diámetro (mm)",
                "Tirada",
                "Ceca",
                "Pureza",
                "Forma",
                "Canto",
                "Es Estimación"
            ]
        )
        
        cursor.close()
        conexion.close()
        return df, None
    
    except Exception as e:
        if conexion:
            try:
                conexion.close()
            except:
                pass
        return None, str(e)

# Función para obtener monedas disponibles para venta (no vendidas)
def obtener_monedas_disponibles_venta():
    conexion, error = conectar_bd()
    if conexion is None:
        return [], error
    
    try:
        cursor = conexion.cursor()
        query = """
            SELECT 
                cu.id_item,
                cm.nombre,
                cm.anio,
                cu.precio_compra
            FROM coleccion_usuario cu
            INNER JOIN catalogo_maestro cm ON cu.id_moneda = cm.id_moneda
            WHERE cu.id_item NOT IN (SELECT id_item FROM ventas)
            ORDER BY cm.nombre, cm.anio
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conexion.close()
        return rows, None
    except Exception as e:
        if conexion:
            try:
                conexion.close()
            except:
                pass
        return [], str(e)

# Función para registrar una venta
def registrar_venta(id_item, fecha_venta, precio_venta, comprador, gastos_envio, comision):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, 0, error
    
    try:
        cursor = conexion.cursor()
        # Obtener el precio de compra para calcular ganancia
        query_precio = "SELECT precio_compra FROM coleccion_usuario WHERE id_item = %s"
        cursor.execute(query_precio, (id_item,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conexion.close()
            return False, 0, "No se encontró la moneda en la colección"
        
        precio_compra = float(result[0])
        ganancia = precio_venta - precio_compra - gastos_envio - comision
        
        # Obtener el próximo id_venta
        query_max_id = "SELECT COALESCE(MAX(id_venta), 0) + 1 FROM ventas"
        cursor.execute(query_max_id)
        result_id = cursor.fetchone()
        nuevo_id = result_id[0]
        
        # Insertar venta
        query_insert = """
            INSERT INTO ventas 
            (id_venta, id_item, fecha_venta, precio_venta, comprador, gastos_envio, comision_plataforma)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(
            query_insert,
            (nuevo_id, id_item, fecha_venta, float(precio_venta), comprador, float(gastos_envio), float(comision))
        )
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, ganancia, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, 0, str(e)

# Función para eliminar una moneda de la colección
def eliminar_moneda(id_item):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        # Eliminar el registro de coleccion_usuario
        query_delete = "DELETE FROM coleccion_usuario WHERE id_item = %s"
        cursor.execute(query_delete, (id_item,))
        
        # Verificar si se eliminó algo
        if cursor.rowcount == 0:
            cursor.close()
            conexion.close()
            return False, "No se encontró la moneda con ese ID"
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# Función para actualizar datos de una moneda de la colección
def actualizar_moneda(id_item, nuevo_estado, nuevo_precio, nueva_fecha):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        # Actualizar el registro
        query_update = """
            UPDATE coleccion_usuario 
            SET estado_conservacion = %s,
                precio_compra = %s,
                fecha_compra = %s
            WHERE id_item = %s
        """
        
        cursor.execute(
            query_update,
            (nuevo_estado, float(nuevo_precio), nueva_fecha, id_item)
        )
        
        # Verificar si se actualizó algo
        if cursor.rowcount == 0:
            cursor.close()
            conexion.close()
            return False, "No se encontró la moneda con ese ID"
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# Función para proponer una nueva moneda (enviada a moderación)
def proponer_nueva_referencia(nombre, pais, anio, material, peso_gramos, diametro_mm, foto_url=None):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        # Obtener el próximo id_solicitud
        query_max_id = "SELECT COALESCE(MAX(id_solicitud), 0) + 1 FROM solicitudes_catalogo"
        cursor.execute(query_max_id)
        result = cursor.fetchone()
        nuevo_id = result[0]
        
        # Insertar nueva solicitud
        query_insert = """
            INSERT INTO solicitudes_catalogo 
            (id_solicitud, nombre, pais, anio, material, peso_gramos, diametro_mm, foto_generica_url, usuario_solicitante)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(
            query_insert,
            (nuevo_id, nombre, pais, anio, material, 
             float(peso_gramos) if peso_gramos else None,
             float(diametro_mm) if diametro_mm else None,
             foto_url if foto_url else None,
             100)  # Usuario por defecto
        )
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# Función para obtener solicitudes pendientes de aprobación
def obtener_solicitudes_pendientes():
    conexion, error = conectar_bd()
    if conexion is None:
        return [], error
    
    try:
        cursor = conexion.cursor()
        query = """
            SELECT id_solicitud, nombre, pais, anio, material, 
                   peso_gramos, diametro_mm, fecha_solicitud
            FROM solicitudes_catalogo
            ORDER BY fecha_solicitud DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conexion.close()
        return rows, None
    except Exception as e:
        if conexion:
            try:
                conexion.close()
            except:
                pass
        return [], str(e)

# Función para aprobar una solicitud (moverla al catálogo maestro)
def aprobar_solicitud(id_solicitud):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        
        # Obtener datos de la solicitud
        query_get = """
            SELECT nombre, pais, anio, material, peso_gramos, diametro_mm, foto_generica_url
            FROM solicitudes_catalogo
            WHERE id_solicitud = %s
        """
        cursor.execute(query_get, (id_solicitud,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conexion.close()
            return False, "No se encontró la solicitud"
        
        nombre, pais, anio, material, peso_gramos, diametro_mm, foto_url = result
        
        # Obtener el próximo id_moneda
        query_max_id = "SELECT COALESCE(MAX(id_moneda), 0) + 1 FROM catalogo_maestro"
        cursor.execute(query_max_id)
        result_id = cursor.fetchone()
        nuevo_id = result_id[0]
        
        # Insertar en catalogo_maestro
        query_insert = """
            INSERT INTO catalogo_maestro 
            (id_moneda, nombre, pais, anio, material, peso_gramos, diametro_mm, foto_generica_url, popularidad)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
        """
        
        cursor.execute(
            query_insert,
            (nuevo_id, nombre, pais, anio, material, peso_gramos, diametro_mm, foto_url)
        )
        
        # Eliminar de solicitudes
        query_delete = "DELETE FROM solicitudes_catalogo WHERE id_solicitud = %s"
        cursor.execute(query_delete, (id_solicitud,))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# Función para rechazar una solicitud (eliminarla)
def rechazar_solicitud(id_solicitud):
    conexion, error = conectar_bd()
    if conexion is None:
        return False, error
    
    try:
        cursor = conexion.cursor()
        query_delete = "DELETE FROM solicitudes_catalogo WHERE id_solicitud = %s"
        cursor.execute(query_delete, (id_solicitud,))
        
        if cursor.rowcount == 0:
            cursor.close()
            conexion.close()
            return False, "No se encontró la solicitud"
        
        conexion.commit()
        cursor.close()
        conexion.close()
        return True, None
    except Exception as e:
        if conexion:
            try:
                conexion.rollback()
                conexion.close()
            except:
                pass
        return False, str(e)

# ============================================================================
# BÚSQUEDA WEB ASISTIDA
# ============================================================================

def buscar_candidatos_web(query):
    """
    Búsqueda mejorada que genera VARIANTES de la misma moneda
    En lugar de mostrar 4 monedas diferentes, muestra 4 versiones de la misma
    """
    candidatos = []
    
    # Palabras clave numismáticas
    palabras_coin = ['moneda', 'coin', 'numismatic', 'mint', 'currency', 'onza', 'dólar', 'peso', 'real', 'denario']
    
    # Detectar metales y tamaños comunes
    metales_variantes = {
        'silver': {'nombres': ['silver', 'plata'], 'simbolo': 'Ag', 'color': '🥈'},
        'gold': {'nombres': ['gold', 'oro'], 'simbolo': 'Au', 'color': '🥇'},
        'platinum': {'nombres': ['platinum', 'platino'], 'simbolo': 'Pt', 'color': '⚪'},
        'copper': {'nombres': ['copper', 'cobre'], 'simbolo': 'Cu', 'color': '🟤'}
    }
    
    tamaños_variantes = ['1 oz', '1/2 oz', '1/4 oz', '1/10 oz', '2 oz', '5 oz']
    
    # Identificar el metal buscado
    metal_principal = None
    query_lower = query.lower()
    for metal, info in metales_variantes.items():
        if any(nombre in query_lower for nombre in info['nombres']):
            metal_principal = metal
            break
    
    # Extraer el nombre base de la moneda (sin metal ni tamaño)
    query_base = query_lower
    for metal, info in metales_variantes.items():
        for nombre in info['nombres']:
            query_base = query_base.replace(nombre, '').strip()
    for tamaño in tamaños_variantes:
        query_base = query_base.replace(tamaño, '').strip()
    
    # PASO 1: Buscar el artículo principal en Wikipedia
    try:
        wikipedia.set_lang('en')
        resultados_wiki = wikipedia.search(f"{query} coin", results=3)
        
        articulo_principal = None
        for titulo in resultados_wiki:
            titulo_lower = titulo.lower()
            if any(palabra in titulo_lower for palabra in palabras_coin):
                try:
                    pagina = wikipedia.page(titulo, auto_suggest=False)
                    contenido = pagina.summary[:800].lower()
                    
                    # Verificar que sea numismático
                    if any(p in contenido for p in ['coin', 'mint', 'bullion', 'currency']):
                        articulo_principal = pagina
                        break
                except:
                    continue
        
        if articulo_principal:
            # PASO 2: GENERAR VARIANTES desde el mismo artículo
            contenido_completo = articulo_principal.content.lower()
            
            # Detectar qué metales/tamaños menciona el artículo
            metales_encontrados = []
            for metal, info in metales_variantes.items():
                if any(nombre in contenido_completo for nombre in info['nombres']):
                    metales_encontrados.append(metal)
            
            tamaños_encontrados = []
            for tamaño in tamaños_variantes:
                if tamaño in contenido_completo:
                    tamaños_encontrados.append(tamaño)
            
            # Si no hay tamaños específicos, usar genérico
            if not tamaños_encontrados:
                tamaños_encontrados = ['estándar']
            
            # Obtener imágenes del artículo
            imagenes_disponibles = []
            if articulo_principal.images:
                titulo_words = articulo_principal.title.lower().replace('coin', '').split()
                
                for img in articulo_principal.images[:15]:
                    img_lower = img.lower()
                    if any(skip in img_lower for skip in ['.svg', 'logo', 'icon', 'flag', 'coat', 'emblem']):
                        continue
                    
                    # Determinar qué metal podría ser esta imagen
                    metal_img = None
                    for metal, info in metales_variantes.items():
                        if any(nombre in img_lower for nombre in info['nombres']) or info['simbolo'].lower() in img_lower:
                            metal_img = metal
                            break
                    
                    # Priorizar imágenes con el nombre de la moneda
                    if any(word in img_lower for word in titulo_words if len(word) > 3):
                        imagenes_disponibles.append({'url': img, 'metal': metal_img, 'score': 10})
                    elif any(word in img_lower for word in ['obverse', 'reverse', 'coin']):
                        imagenes_disponibles.append({'url': img, 'metal': metal_img, 'score': 5})
            
            # GENERAR CANDIDATO PARA CADA METAL × TAMAÑO
            variantes_generadas = 0
            
            # Priorizar el metal buscado
            metales_orden = []
            if metal_principal and metal_principal in metales_encontrados:
                metales_orden.append(metal_principal)
            for metal in metales_encontrados:
                if metal not in metales_orden:
                    metales_orden.append(metal)
            
            for metal in metales_orden[:3]:  # Máximo 3 metales
                for tamaño in tamaños_encontrados[:2]:  # Máximo 2 tamaños por metal
                    if variantes_generadas >= 4:
                        break
                    
                    # Buscar imagen apropiada para este metal
                    imagen_variante = None
                    for img_data in imagenes_disponibles:
                        if img_data['metal'] == metal:
                            imagen_variante = img_data['url']
                            break
                    
                    # Si no hay imagen específica del metal, usar la primera disponible
                    if not imagen_variante and imagenes_disponibles:
                        imagen_variante = imagenes_disponibles[0]['url']
                    
                    # Construir título de variante
                    info_metal = metales_variantes[metal]
                    titulo_variante = f"{articulo_principal.title}"
                    detalle_variante = f"{info_metal['color']} {info_metal['nombres'][0].title()}"
                    if tamaño != 'estándar':
                        detalle_variante += f" - {tamaño}"
                    
                    # Resumen adaptado
                    resumen_base = articulo_principal.summary[:200]
                    resumen_variante = f"**{detalle_variante}**\n\n{resumen_base}..."
                    
                    candidatos.append({
                        'titulo': titulo_variante,
                        'resumen': resumen_variante,
                        'fuente': 'Wikipedia (EN)',
                        'imagen_url': imagen_variante,
                        'url': articulo_principal.url,
                        'score': 10 if metal == metal_principal else 5
                    })
                    
                    variantes_generadas += 1
                    
                if variantes_generadas >= 4:
                    break
    
    except Exception as e:
        st.warning(f"Error en búsqueda: {str(e)}")
    
    # Ordenar por score (metal prioritario primero)
    candidatos_sorted = sorted(candidatos, key=lambda x: x.get('score', 0), reverse=True)
    for c in candidatos_sorted:
        c.pop('score', None)
    
    return candidatos_sorted


# ============================================================================
# BARRA LATERAL - PRECIOS DE MERCADO
# ============================================================================

st.sidebar.title("💰 Precios de Mercado")
precios_mercado, error_mercado = obtener_precios_mercado()

if precios_mercado:
    # Mostrar verticalmente para evitar truncamiento
    st.sidebar.metric(
        "🥇 Oro",
        f"€{precios_mercado['oro_gramo']:.2f}/g"
    )
    st.sidebar.metric(
        "🥈 Plata",
        f"€{precios_mercado['plata_gramo']:.2f}/g"
    )
    st.sidebar.caption(f"⌛ {precios_mercado['timestamp']}")
    
    # Mostrar información de debug
    with st.sidebar.expander("🔍 Info de conversión"):
        st.caption(f"Oro: ${precios_mercado.get('oro_usd_onza', 0):.2f}/oz troy")
        st.caption(f"Plata: ${precios_mercado.get('plata_usd_onza', 0):.2f}/oz troy")
        st.caption(f"Tasa EUR/USD: {precios_mercado.get('eur_usd_rate', 0):.4f}")
        st.caption("(1€ = {:.4f}$)".format(precios_mercado.get('eur_usd_rate', 0)))
else:
    st.sidebar.warning("⚠️ No se pudieron cargar los precios")
    if error_mercado:
        st.sidebar.caption(f"Error: {error_mercado}")

st.sidebar.markdown("---")

# ============================================================================
# BARRA LATERAL - NUEVA ADQUISICIÓN
# ============================================================================

st.sidebar.title("🆕 Nueva Adquisición")
st.sidebar.markdown("---")

# Obtener catálogo de monedas
catalogo, error_catalogo = obtener_catalogo()

if error_catalogo:
    st.sidebar.error(f"Error al cargar catálogo: {error_catalogo}")
elif not catalogo:
    st.sidebar.info("📋 No hay monedas en el catálogo maestro")
else:
    # Crear formulario en la barra lateral solo si hay monedas en el catálogo
    with st.sidebar.form("formulario_nueva_moneda", clear_on_submit=True):
        st.subheader("Datos de la Adquisición")
        
        # Crear diccionario de opciones para el selectbox
        opciones_monedas = {}
        opciones_display = []
        
        for id_moneda, nombre, pais, anio in catalogo:
            display_text = f"{nombre} ({pais}, {anio})"
            opciones_monedas[display_text] = id_moneda
            opciones_display.append(display_text)
        
        # Selectbox para elegir moneda
        moneda_seleccionada = st.selectbox(
            "Moneda del Catálogo",
            options=opciones_display,
            help="Selecciona la moneda que compraste"
        )
        
        # Fecha de compra
        fecha_compra = st.date_input(
            "Fecha de Compra",
            help="¿Cuándo compraste esta moneda?"
        )
        
        # Precio de compra
        precio_compra = st.number_input(
            "Precio de Compra ($)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="¿Cuánto pagaste por esta moneda?"
        )
        
        # Estado de conservación
        estado = st.text_input(
            "Estado de Conservación",
            placeholder="Ej: MBC, EBC, SC",
            help="Estado de la moneda según la escala numismática"
        )
        
        # Botón de guardar
        submitted = st.form_submit_button("💾 Guardar", width="stretch")
        
        if submitted:
            # Validar campos
            if not estado:
                st.error("⚠️ Debes especificar el estado de conservación")
            elif precio_compra <= 0:
                st.error("⚠️ El precio debe ser mayor a 0")
            else:
                # Obtener el id_moneda de la moneda seleccionada
                id_moneda_seleccionada = opciones_monedas[moneda_seleccionada]
                
                # Añadir a la base de datos
                exito, error = añadir_moneda(
                    id_moneda_seleccionada,
                    fecha_compra,
                    precio_compra,
                    estado
                )
                
                if exito:
                    st.success(f"✅ ¡Moneda añadida exitosamente!\n\n{moneda_seleccionada}\nPrecio: ${precio_compra:.2f}\nEstado: {estado}")
                    st.balloons()
                    # Forzar recarga de la página para mostrar los nuevos datos
                    st.rerun()
                else:
                    st.error(f"❌ Error al guardar: {error}")

# ============================================================================
# BARRA LATERAL - PROPONER NUEVA MONEDA
# ============================================================================

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 ¿No encuentras tu moneda?")

# Expander para proponer nueva moneda
with st.sidebar.expander("💡 Propón una moneda nueva"):
    st.markdown("**Si no encuentras tu moneda en el catálogo, proponla aquí.**")
    st.caption("Tu propuesta será revisada por el administrador.")
    
    with st.form("formulario_propuesta", clear_on_submit=True):
        prop_nombre = st.text_input("Nombre de la Moneda *", placeholder="Ej: Ducat de Oro")
        prop_pais = st.text_input("País *", placeholder="Ej: Austria")
        
        col_prop1, col_prop2 = st.columns(2)
        with col_prop1:
            prop_anio = st.number_input("Año *", min_value=1, max_value=2100, value=2000, step=1)
        with col_prop2:
            prop_material = st.text_input("Material *", placeholder="Ej: Plata .925")
        
        col_prop3, col_prop4 = st.columns(2)
        with col_prop3:
            prop_peso = st.number_input("Peso (g)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        with col_prop4:
            prop_diametro = st.number_input("Diámetro (mm)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        
        prop_foto = st.text_input("URL de Foto (opcional)", placeholder="https://...")
        
        submit_propuesta = st.form_submit_button("📤 Enviar Propuesta", use_container_width=True)
        
        if submit_propuesta:
            if not prop_nombre or not prop_pais or not prop_material:
                st.error("⚠️ Debes completar los campos obligatorios (*)")
            else:
                exito, error = proponer_nueva_referencia(
                    prop_nombre,
                    prop_pais,
                    prop_anio,
                    prop_material,
                    prop_peso if prop_peso > 0 else None,
                    prop_diametro if prop_diametro > 0 else None,
                    prop_foto if prop_foto else None
                )
                
                if exito:
                    st.success("✅ ¡Tu moneda ha sido enviada a revisión por el administrador!")
                    st.info("📧 Recibirás una notificación cuando sea aprobada.")
                else:
                    st.error(f"❌ Error al enviar: {error}")

st.sidebar.markdown("---")

# Botón de descarga de PDF
st.sidebar.subheader("📊 Reportes")

# Obtener datos para el PDF
df_pdf, _ = obtener_datos()
if df_pdf is not None and not df_pdf.empty:
    df_en_cartera_pdf = df_pdf[df_pdf["Precio de Venta"] == 0].copy()
    
    if not df_en_cartera_pdf.empty:
        # Obtener precios de mercado y calcular valores
        precios_pdf, _ = obtener_precios_mercado()
        
        if precios_pdf:
            # Calcular valor estimado (misma lógica que en tab1)
            def calcular_valor_pdf(row):
                material = str(row.get("Material", "")).lower()
                peso = row.get("Peso (g)", 0)
                precio_compra = row.get("Precio de Compra", 0)
                
                if peso and not pd.isna(peso):
                    peso = float(peso)
                else:
                    peso = 0
                
                if peso == 0:
                    return precio_compra
                
                if "oro" in material or "gold" in material:
                    return peso * precios_pdf['oro_gramo']
                elif "plata" in material or "silver" in material:
                    pureza = 0.9
                    if ".999" in material or "999" in material:
                        pureza = 0.999
                    elif ".925" in material or "925" in material:
                        pureza = 0.925
                    elif ".900" in material or "900" in material:
                        pureza = 0.900
                    elif ".800" in material or "800" in material:
                        pureza = 0.800
                    return peso * precios_pdf['plata_gramo'] * pureza
                else:
                    return precio_compra
            
            df_en_cartera_pdf["Valor Estimado (€)"] = df_en_cartera_pdf.apply(calcular_valor_pdf, axis=1)
        else:
            df_en_cartera_pdf["Valor Estimado (€)"] = df_en_cartera_pdf["Precio de Compra"]
        
        valor_total_pdf = float(df_en_cartera_pdf["Valor Estimado (€)"].sum())
        inversion_total_pdf = float(df_en_cartera_pdf["Precio de Compra"].sum())
        
        # Generar PDF
        try:
            pdf_bytes = generar_pdf(df_en_cartera_pdf, valor_total_pdf, inversion_total_pdf)
            fecha_str = datetime.now().strftime('%Y%m%d')
            
            st.sidebar.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"reporte_coleccion_{fecha_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.sidebar.error(f"⚠️ Error al generar PDF: {str(e)}")
    else:
        st.sidebar.info("⚠️ No hay monedas en cartera para exportar")
else:
    st.sidebar.info("⚠️ No hay datos disponibles")

st.sidebar.markdown("---")
st.sidebar.caption("💡 Añade monedas a tu colección desde aquí")

# ============================================================================
# PÁGINA PRINCIPAL
# ============================================================================

# Título de la aplicación
st.title("🪙 Colección de Monedas")
st.markdown("---")

# Crear pestañas para organizar la aplicación
tab1, tab2, tab3, tab4 = st.tabs([
    "🏛️ Mi Colección", 
    "📚 Gestión del Catálogo", 
    "💸 Registrar Venta",
    "👮 Panel de Admin"
])

# ============================================================================
# PESTAÑA 1: MI COLECCIÓN
# ============================================================================
with tab1:
    # Obtener y mostrar los datos
    with st.spinner("Cargando datos de la colección..."):
        df, error = obtener_datos()

    if df is not None and not df.empty:
        # Separar monedas vendidas de las en cartera
        df_vendidas = df[df["Precio de Venta"] > 0]
        df_en_cartera = df[df["Precio de Venta"] == 0].copy()  # .copy() para evitar warnings
        
        # Calcular valor de mercado estimado para monedas en cartera
        if not df_en_cartera.empty:
            # Obtener precios de mercado
            precios_mercado, _ = obtener_precios_mercado()
            
            if precios_mercado:
                def calcular_valor_estimado(row):
                    material = str(row.get("Material", "")).lower()
                    peso = row.get("Peso (g)", 0)
                    precio_compra = row.get("Precio de Compra", 0)
                    
                    # Convertir peso a float para evitar errores con Decimal
                    if peso and not pd.isna(peso):
                        peso = float(peso)
                    else:
                        peso = 0
                    
                    # Si no hay peso, usar precio de compra
                    if peso == 0:
                        return precio_compra
                    
                    # Detectar si es oro
                    if "oro" in material or "gold" in material:
                        return peso * precios_mercado['oro_gramo']
                    
                    # Detectar si es plata
                    elif "plata" in material or "silver" in material:
                        # Intentar extraer pureza del material
                        pureza = 0.9  # Pureza por defecto
                        
                        if ".999" in material or "999" in material:
                            pureza = 0.999
                        elif ".925" in material or "925" in material:
                            pureza = 0.925
                        elif ".900" in material or "900" in material:
                            pureza = 0.900
                        elif ".800" in material or "800" in material:
                            pureza = 0.800
                        
                        return peso * precios_mercado['plata_gramo'] * pureza
                    
                    # Para otros materiales, usar precio de compra
                    else:
                        return precio_compra
                
                # Aplicar cálculo a cada fila
                df_en_cartera["Valor Estimado (€)"] = df_en_cartera.apply(calcular_valor_estimado, axis=1)
            else:
                # Si no hay precios de mercado, usar precio de compra
                df_en_cartera["Valor Estimado (€)"] = df_en_cartera["Precio de Compra"]
        
        # Mostrar estadísticas básicas (ahora con 4 columnas)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total de Monedas", len(df))
            st.caption(f"🔴 Vendidas: {len(df_vendidas)} | 🟢 En Cartera: {len(df_en_cartera)}")
        
        with col2:
            if "Precio de Compra" in df.columns:
                # Inversión activa = solo monedas no vendidas
                inversion_activa = float(df_en_cartera["Precio de Compra"].sum())
                st.metric("💼 Inversión Activa", f"€{inversion_activa:,.2f}")
                st.caption(f"Dinero en {len(df_en_cartera)} moneda(s) sin vender")
        
        with col3:
            # Valor de mercado actual
            if not df_en_cartera.empty and "Valor Estimado (€)" in df_en_cartera.columns:
                valor_mercado = float(df_en_cartera["Valor Estimado (€)"].sum())
                inversion_activa = float(df_en_cartera["Precio de Compra"].sum())
                ganancia_no_realizada = valor_mercado - inversion_activa
                porcentaje_ganancia = (ganancia_no_realizada / inversion_activa * 100) if inversion_activa > 0 else 0
                
                st.metric(
                    "💎 Valor de Mercado",
                    f"€{valor_mercado:,.2f}",
                    delta=f"{porcentaje_ganancia:+.1f}%"
                )
                st.caption(f"Ganancia no realizada: €{ganancia_no_realizada:,.2f}")
        
        with col4:
            if "Precio de Compra" in df.columns and "Precio de Venta" in df.columns:
                # Ganancia realizada = solo de monedas vendidas
                costo_vendidas = float(df_vendidas["Precio de Compra"].sum())
                ingreso_vendidas = float(df_vendidas["Precio de Venta"].sum())
                ganancia_realizada = ingreso_vendidas - costo_vendidas
                
                # Calcular porcentaje de ganancia
                porcentaje_ganancia = (ganancia_realizada / costo_vendidas * 100) if costo_vendidas > 0 else 0
                
                st.metric(
                    "📈 Ganancia Realizada", 
                    f"€{ganancia_realizada:,.2f}",
                    delta=f"{porcentaje_ganancia:.1f}%"
                )
                st.caption(f"Profit de {len(df_vendidas)} venta(s)")

        
        st.markdown("---")
        
        # Sección de análisis de mercado
        st.subheader("📊 Análisis de Mercado")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Gráfico 1: Distribución por Material (solo monedas en cartera)
            if not df_en_cartera.empty and "Material" in df_en_cartera.columns and "Precio de Compra" in df_en_cartera.columns:
                # Agrupar por material sumando el costo
                df_material = df_en_cartera.groupby("Material")["Precio de Compra"].sum().reset_index()
                df_material.columns = ["Material", "Costo (€)"]
                # Convertir a float para evitar problemas con Decimal
                df_material["Costo (€)"] = df_material["Costo (€)"].astype(float)
                
                # Crear gráfico de pastel (donut)
                fig_material = px.pie(
                    df_material,
                    values="Costo (€)",
                    names="Material",
                    title="Distribución de Inversión por Material",
                    hole=0.4  # Hacer donut
                )
                
                # Actualizar diseño para mejor visualización
                fig_material.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig_material, use_container_width=True)
            else:
                st.info("📊 No hay suficientes datos para mostrar el gráfico de materiales")
        
        with col_graf2:
            # Gráfico 2: Monedas por País (solo monedas en cartera)
            if not df_en_cartera.empty and "País" in df_en_cartera.columns:
                # Contar monedas por país
                df_pais = df_en_cartera["País"].value_counts().reset_index()
                df_pais.columns = ["País", "Cantidad"]
                
                # Crear gráfico de barras
                fig_pais = px.bar(
                    df_pais,
                    x="País",
                    y="Cantidad",
                    title="Cantidad de Monedas por País",
                    labels={"Cantidad": "Número de Monedas", "País": "País"},
                    color="Cantidad",
                    color_continuous_scale="Blues"
                )
                
                # Actualizar diseño
                fig_pais.update_layout(
                    xaxis_tickangle=-45,
                    showlegend=False
                )
                
                st.plotly_chart(fig_pais, use_container_width=True)
            else:
                st.info("📊 No hay suficientes datos para mostrar el gráfico de países")
        
        st.markdown("---")
        
        # Sección de filtros
        st.subheader("🔍 Filtros")
        
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            # Filtro por estado
            if "Estado" in df.columns:
                estados_unicos = df["Estado"].dropna().unique().tolist()
                if estados_unicos:
                    estado_seleccionado = st.multiselect(
                        "Estado de Conservación",
                        options=estados_unicos,
                        default=estados_unicos,
                        key="filtro_estado"
                    )
                    # Si no hay nada seleccionado, mostrar todo
                    if estado_seleccionado:
                        df_filtrado = df[df["Estado"].isin(estado_seleccionado)]
                    else:
                        df_filtrado = df
                else:
                    df_filtrado = df
            else:
                df_filtrado = df
        
        with col_filter2:
            # Filtro por país
            if "País" in df.columns:
                paises_unicos = df["País"].dropna().unique().tolist()
                if paises_unicos:
                    pais_seleccionado = st.multiselect(
                        "País",
                        options=paises_unicos,
                        default=paises_unicos,
                        key="filtro_pais"
                    )
                    # Si no hay nada seleccionado, mostrar todo
                    if pais_seleccionado:
                        df_filtrado = df_filtrado[df_filtrado["País"].isin(pais_seleccionado)]
                    # Si no hay selección, se mantiene df_filtrado como está
        
        st.markdown("---")
        
        # Tabla principal
        st.subheader("📊 Tabla de Monedas")
        
        # Configurar formato de columnas para la visualización
        column_config = {
            "Foto": st.column_config.ImageColumn(
                "Foto",
                help="Vista previa",
                width="small"
            ),
            "Precio de Compra": st.column_config.NumberColumn(
                "Precio de Compra",
                format="$%.2f"
            ),
            "Precio de Venta": st.column_config.NumberColumn(
                "Precio de Venta",
                format="$%.2f"
            ),
            "Fecha de Compra": st.column_config.DateColumn(
                "Fecha de Compra",
                format="DD/MM/YYYY"
            )
        }
        
        # Mostrar la tabla interactiva
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            height=500,
            hide_index=True,
            column_config=column_config
        )
        
        # Información adicional
        st.markdown("---")
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.info(f"📋 Mostrando {len(df_filtrado)} de {len(df)} monedas")
        
        with col_info2:
            if len(df_filtrado) > 0:
                valor_promedio = df_filtrado["Precio de Compra"].mean()
                st.info(f"💎 Valor promedio de compra: ${valor_promedio:,.2f}")
        
        # ============================================================================
        # SECCIÓN DE ESPECIFICACIONES TÉCNICAS
        # ============================================================================
        st.markdown("---")
        st.subheader("🔬 Especificaciones Técnicas Detalladas")
        st.caption("Haz clic en una moneda para ver sus datos completos")
        
        # Mostrar solo monedas en cartera (no vendidas) con datos técnicos
        df_con_detalles = df_en_cartera.copy()
        
        if not df_con_detalles.empty:
            # Agrupar por moneda para mostrar fichas
            for idx, moneda in df_con_detalles.head(10).iterrows():  # Mostrar primeras 10
                es_estimacion = moneda.get('Es Estimación', False)
                nombre = moneda['Nombre de la Moneda']
                anio = moneda['Año']
                
                # Crear expander con advertencia si es estimación
                titulo_expander = f"{'⚠️ ' if es_estimacion else '✅ '}{nombre} ({anio})"
                
                with st.expander(titulo_expander, expanded=False):
                    # Advertencia de estimación
                    if es_estimacion:
                        st.warning("⚠️ **Advertencia Académica**: Algunos datos técnicos de esta moneda son estimaciones basadas en investigación numismática, no registros oficiales.")
                    
                    # Columnas para organizar la información
                    col_spec1, col_spec2 = st.columns(2)
                    
                    with col_spec1:
                        st.markdown("### 📋 Información General")
                        info_general = f"""
                        - **País**: {moneda.get('País', 'N/A')}
                        - **Año**: {moneda.get('Año', 'N/A')}
                        - **Material**: {moneda.get('Material', 'N/A')}
                        - **Forma**: {moneda.get('Forma', 'N/A')}
                        """
                        st.markdown(info_general)
                        
                        st.markdown("### 💰 Datos de Compra")
                        datos_compra = f"""
                        - **Precio Compra**: €{moneda.get('Precio de Compra', 0):,.2f}
                        - **Fecha**: {moneda.get('Fecha de Compra', 'N/A')}
                        - **Estado**: {moneda.get('Estado', 'N/A')}
                        """
                        st.markdown(datos_compra)
                    
                    with col_spec2:
                        st.markdown("### ⚙️ Especificaciones Técnicas")
                        
                        # Peso y diámetro
                        peso = moneda.get('Peso (g)')
                        diametro = moneda.get('Diámetro (mm)')
                        pureza = moneda.get('Pureza')
                        ceca = moneda.get('Ceca')
                        canto = moneda.get('Canto')
                        tirada = moneda.get('Tirada')
                        
                        specs_tecnicas = f"""
                        - **Peso**: {f'{peso:.2f} g' if peso else 'N/A'}
                        - **Diámetro**: {f'{diametro:.1f} mm' if diametro else 'N/A'}
                        - **Pureza**: {f'{pureza:.3f}' if pureza else 'N/A'}
                        - **Ceca**: {ceca if ceca else 'N/A'}
                        - **Canto**: {canto if canto else 'N/A'}
                        """
                        st.markdown(specs_tecnicas)
                        
                        # Tirada con clasificación de rareza
                        if tirada:
                            if tirada < 10000:
                                rareza = "🌟 Extremadamente Rara"
                            elif tirada < 100000:
                                rareza = "⭐ Muy Rara"
                            elif tirada < 500000:
                                rareza = "💫 Rara"
                            elif tirada < 1000000:
                                rareza = "✨ Escasa"
                            else:
                                rareza = "📊 Común"
                            
                            st.markdown(f"**Tirada**: {tirada:,} unidades")
                            st.info(f"**Clasificación**: {rareza}")
                        else:
                            st.markdown("**Tirada**: Desconocida")
                    
                    # Separador visual
                    st.markdown("---")
                    
                    # Indicador de calidad de datos
                    if es_estimacion:
                        st.caption("🔬 Datos de investigación numismática | Estimaciones basadas en fuentes académicas")
                    else:
                        st.caption("✅ Datos oficiales verificados | Fuentes: Casas de moneda y registros históricos")
            
            if len(df_con_detalles) > 10:
                st.info(f"📋 Mostrando las primeras 10 de {len(df_con_detalles)} monedas. Las demás están en la tabla principal.")
        else:
            st.info("📋 No hay monedas con especificaciones técnicas disponibles")
        
        # ============================================================================
        # SECCIÓN DE GESTIÓN DE INVENTARIO
        # ============================================================================
        st.markdown("---")
        st.subheader("🛠️ Gestionar Inventario")
        st.markdown("Edita o elimina monedas de tu cartera")
        
        # Obtener monedas disponibles para editar (solo las no vendidas)
        monedas_editar, error_editar = obtener_monedas_disponibles_venta()
        
        if error_editar:
            st.error(f"Error al cargar monedas: {error_editar}")
        elif not monedas_editar:
            st.info("📋 No hay monedas en tu cartera para gestionar")
        else:
            # Crear diccionario de opciones para el selectbox
            opciones_monedas_editar = {}
            opciones_display_editar = []
            
            for id_item, nombre, anio, precio_compra in monedas_editar:
                display_text = f"ID {id_item} - {nombre} ({anio}) - Compra: €{precio_compra:.2f}"
                opciones_monedas_editar[display_text] = (id_item, nombre, anio, precio_compra)
                opciones_display_editar.append(display_text)
            
            # Selectbox para seleccionar moneda
            moneda_edit_seleccionada = st.selectbox(
                "Selecciona una moneda de tu cartera",
                options=opciones_display_editar,
                help="Selecciona la moneda que deseas editar o eliminar",
                key="selectbox_editar_moneda"
            )
            
            if moneda_edit_seleccionada:
                id_item_seleccionado, nombre_moneda, anio_moneda, precio_actual = opciones_monedas_editar[moneda_edit_seleccionada]
                
                # Obtener datos actuales de la moneda seleccionada
                # Buscar en el dataframe original
                moneda_actual = df_en_cartera[df_en_cartera['Nombre de la Moneda'] == nombre_moneda]
                if not moneda_actual.empty:
                    estado_actual = moneda_actual.iloc[0]['Estado']
                    fecha_actual = moneda_actual.iloc[0]['Fecha de Compra']
                else:
                    estado_actual = "N/A"
                    fecha_actual = datetime.now().date()
                
                st.markdown("---")
                
                # Dos columnas: Editar y Eliminar
                col_editar, col_eliminar = st.columns(2)
                
                # COLUMNA 1: EDITAR
                with col_editar:
                    st.markdown("### ✏️ Editar Datos")
                    
                    with st.form(f"form_editar_{id_item_seleccionado}", clear_on_submit=False):
                        nuevo_precio = st.number_input(
                            "Precio de Compra (€)",
                            min_value=0.0,
                            value=float(precio_actual),
                            step=0.01,
                            format="%.2f",
                            key=f"precio_{id_item_seleccionado}"
                        )
                        
                        nuevo_estado = st.text_input(
                            "Estado de Conservación",
                            value=estado_actual,
                            placeholder="Ej: MBC, EBC, SC",
                            key=f"estado_{id_item_seleccionado}"
                        )
                        
                        nueva_fecha = st.date_input(
                            "Fecha de Compra",
                            value=pd.to_datetime(fecha_actual).date() if pd.notna(fecha_actual) else datetime.now().date(),
                            key=f"fecha_{id_item_seleccionado}"
                        )
                        
                        submit_editar = st.form_submit_button(
                            "💾 Actualizar Datos",
                            use_container_width=True,
                            type="primary"
                        )
                        
                        if submit_editar:
                            if not nuevo_estado:
                                st.error("⚠️ El estado no puede estar vacío")
                            elif nuevo_precio <= 0:
                                st.error("⚠️ El precio debe ser mayor a 0")
                            else:
                                # Actualizar en la base de datos
                                exito, error = actualizar_moneda(
                                    id_item_seleccionado,
                                    nuevo_estado,
                                    nuevo_precio,
                                    nueva_fecha
                                )
                                
                                if exito:
                                    st.success(f"✅ Moneda actualizada exitosamente!")
                                    st.balloons()
                                    # Esperar un momento y recargar
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")
                
                # COLUMNA 2: ELIMINAR (ZONA DE PELIGRO)
                with col_eliminar:
                    st.markdown("### ⚠️ Zona de Peligro")
                    st.warning("**ADVERTENCIA:** Esta acción no se puede deshacer")
                    
                    st.markdown(f"""
                    **Moneda a eliminar:**
                    - 🪙 {nombre_moneda} ({anio_moneda})
                    - 💰 Precio: €{precio_actual:.2f}
                    - 📊 Estado: {estado_actual}
                    """)
                    
                    # Botón de eliminar fuera del form para evitar conflictos
                    if st.button(
                        "🗑️ Eliminar Moneda",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_eliminar_{id_item_seleccionado}"
                    ):
                        # Confirmar eliminación
                        exito, error = eliminar_moneda(id_item_seleccionado)
                        
                        if exito:
                            st.success(f"✅ Moneda eliminada exitosamente!")
                            # Esperar un momento y recargar
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al eliminar: {error}")
        
    elif df is not None and df.empty:
        st.warning("⚠️ No hay monedas en tu colección.")
        st.info("💡 Agrega monedas desde la barra lateral o crea nuevas referencias en la pestaña 'Gestión del Catálogo'.")
    else:
        st.error("❌ No se pudieron cargar los datos de la base de datos PostgreSQL.")
        if error:
            with st.expander("Ver detalles del error"):
                st.code(error, language="text")
        st.info("💡 Verifica que PostgreSQL esté ejecutándose y que la base de datos 'ColeccionMonedas' exista.")

# ============================================================================
# PESTAÑA 2: GESTIÓN DEL CATÁLOGO
# ============================================================================
with tab2:
    st.header("📚 Gestión del Catálogo Maestro")
    st.markdown("Crea nuevas referencias de monedas que luego podrás añadir a tu colección.")
    st.markdown("---")
    
    # Formulario para crear nueva referencia
    with st.form("formulario_catalogo", clear_on_submit=True):
        st.subheader("➕ Nueva Referencia de Moneda")
        
        col_form1, col_form2 = st.columns(2)
        
        with col_form1:
            nombre = st.text_input(
                "Nombre de la Moneda *",
                placeholder="Ej: Dólar Morgan",
                help="Nombre completo de la moneda"
            )
            
            pais = st.text_input(
                "País *",
                placeholder="Ej: EE.UU.",
                help="País de origen"
            )
            
            anio = st.number_input(
                "Año de Acuñación *",
                min_value=1,
                max_value=2100,
                value=2020,
                step=1,
                help="Año en que se acuñó la moneda"
            )
        
        with col_form2:
            material = st.text_input(
                "Material *",
                placeholder="Ej: Plata .900",
                help="Material de fabricación"
            )
            
            peso_gramos = st.number_input(
                "Peso (gramos)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Peso en gramos (opcional)"
            )
            
            diametro_mm = st.number_input(
                "Diámetro (mm)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                format="%.1f",
                help="Diámetro en milímetros (opcional)"
            )
        
        # Campo para URL de foto (fuera de columnas para ocupar todo el ancho)
        st.text_input(
            "URL de la Foto Genérica",
            placeholder="Ej: https://ejemplo.com/moneda.jpg",
            help="URL de la imagen de la moneda (opcional)",
            key="foto_url_input"
        )
        
        st.markdown("---")
        submitted_catalog = st.form_submit_button("💾 Crear Nueva Referencia", use_container_width=True, type="primary")
        
        if submitted_catalog:
            # Validar campos requeridos
            if not nombre:
                st.error("⚠️ El nombre de la moneda es obligatorio")
            elif not pais:
                st.error("⚠️ El país es obligatorio")
            elif not material:
                st.error("⚠️ El material es obligatorio")
            else:
                # Obtener URL de foto
                foto_url = st.session_state.get("foto_url_input", "")
                
                # Crear la referencia en el catálogo
                exito, error = crear_referencia_catalogo(
                    nombre, pais, anio, material, 
                    peso_gramos if peso_gramos > 0 else None,
                    diametro_mm if diametro_mm > 0 else None,
                    foto_url if foto_url else None
                )
                
                if exito:
                    st.success(f"✅ ¡Referencia creada exitosamente!")
                    st.info(f"""
                    **Moneda añadida al catálogo:**
                    - **Nombre**: {nombre}
                    - **País**: {pais}
                    - **Año**: {anio}
                    - **Material**: {material}
                    {f"- **Peso**: {peso_gramos}g" if peso_gramos > 0 else ""}
                    {f"- **Diámetro**: {diametro_mm}mm" if diametro_mm > 0 else ""}
                    
                    💡 Ahora puedes añadirla a tu colección desde la barra lateral.
                    """)
                    st.balloons()
                    # Forzar recarga para actualizar el sidebar
                    st.rerun()
                else:
                    st.error(f"❌ Error al crear la referencia: {error}")
    
    st.markdown("---")
    
    # ============================================================================
    # BÚSQUEDA WEB ASISTIDA
    # ============================================================================
    st.markdown("---")
    st.subheader("🔍 Búsqueda Asistida de Monedas")
    st.caption("Si no encuentras una moneda, búscala en internet y la añadimos al catálogo")
    
    col_busq1, col_busq2 = st.columns([3, 1])
    
    with col_busq1:
        query_web = st.text_input(
            "Buscar moneda en internet",
            placeholder="Ej: Onza Libertad 2020, Morgan Dollar 1921, Denario de Nerón...",
            key="busqueda_web",
            help="Escribe el nombre de la moneda que buscas"
        )
    
    with col_busq2:
        buscar_btn = st.button("🌐 Buscar", type="primary", use_container_width=True)
    
    # Realizar búsqueda
    if buscar_btn and query_web:
        with st.spinner("🔎 Buscando en Wikipedia y web..."):
            candidatos = buscar_candidatos_web(query_web)
        
        if candidatos:
            st.success(f"✅ Encontrados {len(candidatos)} candidatos")
            st.markdown("---")
            st.markdown("### 📋 Resultados de la Búsqueda")
            st.caption("Haz clic en 'Importar' para añadir la moneda al catálogo")
            
            # Mostrar candidatos en tarjetas
            for idx, candidato in enumerate(candidatos):
                with st.expander(f"🔖 {candidato['titulo']} ({candidato['fuente']})", expanded=(idx==0)):
                    col_cand1, col_cand2 = st.columns([2, 3])
                    
                    with col_cand1:
                        # Imagen si está disponible
                        if candidato.get('imagen_url'):
                            try:
                                st.image(candidato['imagen_url'], width=200)
                            except:
                                st.info("🖼️ Imagen no disponible")
                        else:
                            st.info("🖼️ Sin imagen")
                        
                        st.markdown(f"**Fuente**: {candidato['fuente']}")
                        if candidato.get('url'):
                            st.markdown(f"[🔗 Ver fuente]({candidato['url']})")
                    
                    with col_cand2:
                        st.markdown("**Resumen:**")
                        st.write(candidato['resumen'])
                        
                        # Botón para importar
                        if st.button(f"📥 Importar esta moneda", key=f"import_{idx}"):
                            st.session_state[f'importar_candidato_{idx}'] = candidato
                            st.rerun()
                    
                    # Formulario de importación si se clickeó
                    if st.session_state.get(f'importar_candidato_{idx}'):
                        st.markdown("---")
                        st.markdown("### ✏️ Confirmar Datos de Importación")
                        
                        with st.form(f"form_import_{idx}"):
                            st.info("⚠️ Revisa y corrige los datos antes de guardar")
                            
                            col_form1, col_form2 = st.columns(2)
                            
                            with col_form1:
                                nombre_import = st.text_input(
                                    "Nombre de la Moneda *",
                                    value=candidato['titulo'],
                                    key=f"nombre_import_{idx}"
                                )
                                
                                pais_import = st.text_input(
                                    "País *",
                                    value="",
                                    placeholder="Ej: España, México, EE.UU.",
                                    key=f"pais_import_{idx}"
                                )
                                
                                anio_import = st.number_input(
                                    "Año *",
                                    min_value=1,
                                    max_value=2100,
                                    value=2020,
                                    key=f"anio_import_{idx}"
                                )
                            
                            with col_form2:
                                material_import = st.text_input(
                                    "Material *",
                                    value="",
                                    placeholder="Ej: Plata .999, Oro 24k",
                                    key=f"material_import_{idx}"
                                )
                                
                                peso_import = st.number_input(
                                    "Peso (gramos)",
                                    min_value=0.0,
                                    value=0.0,
                                    step=0.01,
                                    format="%.2f",
                                    key=f"peso_import_{idx}"
                                )
                                
                                diametro_import = st.number_input(
                                    "Diámetro (mm)",
                                    min_value=0.0,
                                    value=0.0,
                                    step=0.1,
                                    format="%.1f",
                                    key=f"diametro_import_{idx}"
                                )
                            
                            foto_import = candidato.get('imagen_url', '')
                            
                            col_submit1, col_submit2 = st.columns([1, 1])
                            
                            with col_submit1:
                                submit_import = st.form_submit_button(
                                    "💾 Guardar en Catálogo",
                                    type="primary",
                                    use_container_width=True
                                )
                            
                            with col_submit2:
                                cancel_import = st.form_submit_button(
                                    "❌ Cancelar",
                                    use_container_width=True
                                )
                            
                            if submit_import:
                                if not nombre_import or not pais_import or not material_import:
                                    st.error("⚠️ Completa los campos obligatorios (*)")
                                else:
                                    # Guardar en catálogo maestro con origen_web=TRUE
                                    exito, error = crear_referencia_catalogo(
                                        nombre_import,
                                        pais_import,
                                        anio_import,
                                        material_import,
                                        peso_import if peso_import > 0 else None,
                                        diametro_import if diametro_import > 0 else None,
                                        foto_import if foto_import else None,
                                        origen_web=True  # ← Marcar como importada de web
                                    )
                                    
                                    if exito:
                                        st.success(f"✅ '{nombre_import}' añadida al catálogo!")
                                        st.balloons()
                                        # Limpiar session state
                                        del st.session_state[f'importar_candidato_{idx}']
                                        import time
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Error: {error}")
                            
                            if cancel_import:
                                del st.session_state[f'importar_candidato_{idx}']
                                st.rerun()
        
        else:
            st.warning("🔍 No se encontraron resultados. Intenta con otros términos de búsqueda.")
            st.info("💡 Sugerencias: Usa el nombre completo de la moneda, incluye el año o el país")

    
    # Mostrar catálogo actual
    st.subheader("📖 Catálogo Actual")
    
    # Buscador de monedas
    busqueda = st.text_input(
        "🔍 Buscar en el catálogo",
        placeholder="Escribe nombre, país, año o material...",
        help="Filtra las monedas del catálogo en tiempo real",
        key="busqueda_catalogo"
    )
    
    catalogo_completo, error_cat = obtener_catalogo()
    
    if catalogo_completo and not error_cat:
        # Convertir a DataFrame para mejor visualización
        df_catalogo = pd.DataFrame(
            catalogo_completo,
            columns=["ID", "Nombre", "País", "Año"]
        )
        
        # Aplicar filtro de búsqueda si hay texto
        if busqueda:
            busqueda_lower = busqueda.lower()
            df_catalogo_filtrado = df_catalogo[
                df_catalogo['Nombre'].str.lower().str.contains(busqueda_lower, na=False) |
                df_catalogo['País'].str.lower().str.contains(busqueda_lower, na=False) |
                df_catalogo['Año'].astype(str).str.contains(busqueda_lower, na=False) |
                df_catalogo['ID'].astype(str).str.contains(busqueda_lower, na=False)
            ]
            st.caption(f"🔎 Mostrando {len(df_catalogo_filtrado)} de {len(df_catalogo)} monedas")
        else:
            df_catalogo_filtrado = df_catalogo
            st.caption(f"📊 Total de monedas en catálogo: {len(df_catalogo)}")
        
        st.dataframe(
            df_catalogo_filtrado,
            use_container_width=True,
            height=400,
            hide_index=True
        )
        
        st.caption(f"📚 Total de referencias en el catálogo: {len(catalogo_completo)}")
    else:
        st.info("📋 El catálogo está vacío. Crea tu primera referencia arriba.")

# ============================================================================
# PESTAÑA 3: REGISTRAR VENTA
# ============================================================================
with tab3:
    st.header("💸 Registrar Venta")
    st.markdown("Registra la venta de tus monedas y actualiza tu inventario.")
    st.markdown("---")
    
    # Obtener monedas disponibles para venta
    monedas_disponibles, error_disponibles = obtener_monedas_disponibles_venta()
    
    if error_disponibles:
        st.error(f"Error al cargar monedas disponibles: {error_disponibles}")
    elif not monedas_disponibles:
        st.warning("⚠️ No tienes monedas disponibles para vender.")
        st.info("💡 Todas tus monedas ya han sido vendidas o no tienes monedas en tu colección. Añade nuevas monedas desde la barra lateral.")
    else:
        # Crear formulario de venta
        with st.form("formulario_venta", clear_on_submit=True):
            st.subheader("📝 Detalles de la Venta")
            
            # Crear opciones para el selectbox
            opciones_monedas = {}
            opciones_display = []
            
            for id_item, nombre, anio, precio_compra in monedas_disponibles:
                display_text = f"ID: {id_item} | {nombre} ({anio}) - Comprada a: ${float(precio_compra):.2f}"
                opciones_monedas[display_text] = {
                    'id_item': id_item,
                    'nombre': nombre,
                    'anio': anio,
                    'precio_compra': float(precio_compra)  # Convertir a float para evitar problemas con Decimal
                }
                opciones_display.append(display_text)
            
            # Selectbox para elegir moneda
            moneda_seleccionada = st.selectbox(
                "Moneda a Vender *",
                options=opciones_display,
                help="Selecciona la moneda que deseas vender"
            )
            
            col_venta1, col_venta2 = st.columns(2)
            
            with col_venta1:
                fecha_venta = st.date_input(
                    "Fecha de Venta *",
                    help="¿Cuándo vendiste esta moneda?"
                )
                
                precio_venta = st.number_input(
                    "Precio de Venta ($) *",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="¿A qué precio vendiste la moneda?"
                )
            
            with col_venta2:
                comprador = st.text_input(
                    "Comprador *",
                    placeholder="Ej: Juan Pérez",
                    help="Nombre del comprador"
                )
                
                gastos_envio = st.number_input(
                    "Gastos de Envío ($)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="Costo de envío (opcional)"
                )
            
            comision = st.number_input(
                "Comisión de Plataforma ($)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Comisión cobrada por la plataforma de venta (opcional)"
            )
            
            # Mostrar preview de ganancia estimada
            if moneda_seleccionada and precio_venta > 0:
                datos_moneda = opciones_monedas[moneda_seleccionada]
                ganancia_estimada = precio_venta - datos_moneda['precio_compra'] - gastos_envio - comision
                
                st.info(f"""
                **Vista Previa:**
                - Precio Compra: ${datos_moneda['precio_compra']:.2f}
                - Precio Venta: ${precio_venta:.2f}
                - Gastos Envío: ${gastos_envio:.2f}
                - Comisión: ${comision:.2f}
                - **Ganancia Estimada: ${ganancia_estimada:.2f}** {'✅' if ganancia_estimada > 0 else '⚠️'}
                """)
            
            st.markdown("---")
            submitted_venta = st.form_submit_button("💰 Confirmar Venta", use_container_width=True, type="primary")
            
            if submitted_venta:
                # Validar campos requeridos
                if not comprador:
                    st.error("⚠️ El nombre del comprador es obligatorio")
                elif precio_venta <= 0:
                    st.error("⚠️ El precio de venta debe ser mayor a 0")
                else:
                    # Obtener datos de la moneda seleccionada
                    datos_moneda = opciones_monedas[moneda_seleccionada]
                    
                    # Registrar la venta
                    exito, ganancia, error = registrar_venta(
                        datos_moneda['id_item'],
                        fecha_venta,
                        precio_venta,
                        comprador,
                        gastos_envio,
                        comision
                    )
                    
                    if exito:
                        st.success(f"✅ ¡Venta registrada exitosamente!")
                        st.balloons()
                        
                        # Mostrar resumen de la venta
                        st.info(f"""
                        **Resumen de la Venta:**
                        - **Moneda**: {datos_moneda['nombre']} ({datos_moneda['anio']})
                        - **Comprador**: {comprador}
                        - **Precio de Compra**: ${datos_moneda['precio_compra']:.2f}
                        - **Precio de Venta**: ${precio_venta:.2f}
                        - **Gastos de Envío**: ${gastos_envio:.2f}
                        - **Comisión**: ${comision:.2f}
                        - **Ganancia Calculada**: ${ganancia:.2f} {'🎉' if ganancia > 0 else '📉'}
                        """)
                        
                        # Esperar un momento antes de recargar
                        import time
                        time.sleep(2)
                        
                        # Recargar para actualizar métricas
                        st.rerun()
                    else:
                        st.error(f"❌ Error al registrar la venta: {error}")
        
        st.markdown("---")
        st.caption(f"💡 Tienes {len(monedas_disponibles)} moneda(s) disponible(s) para vender")

# ============================================================================
# PESTAÑA 4: PANEL DE ADMINISTRACIÓN
# ============================================================================
with tab4:
    st.header("👮 Panel de Administración")
    st.markdown("**Gestión de solicitudes de monedas propuestas por la comunidad**")
    st.markdown("---")
    
    # Autenticación simple
    password_input = st.text_input(
        "🔐 Contraseña de Administrador",
        type="password",
        help="Ingresa la contraseña para acceder al panel de administración",
        key="admin_password"
    )
    
    if password_input == "admin123":
        st.success("✅ Acceso concedido")
        st.markdown("---")
        
        # Obtener solicitudes pendientes
        solicitudes, error_solicitudes = obtener_solicitudes_pendientes()
        
        if error_solicitudes:
            st.error(f"❌ Error al cargar solicitudes: {error_solicitudes}")
        elif not solicitudes:
            st.info("📋 No hay solicitudes pendientes de revisión")
            st.balloons()
        else:
            st.subheader(f"📋 Solicitudes Pendientes ({len(solicitudes)})")
            st.caption("Revisa y aprueba las monedas propuestas por los usuarios")
            
            # Mostrar cada solicitud
            for idx, solicitud in enumerate(solicitudes):
                id_sol, nombre, pais, anio, material, peso, diametro, fecha_sol = solicitud
                
                with st.expander(f"**{nombre}** ({pais}, {anio})", expanded=(idx == 0)):
                    # Información de la solicitud
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown(f"""
                        **📋 Información de la Moneda**
                        - **Nombre**: {nombre}
                        - **País**: {pais}
                        - **Año**: {anio}
                        - **Material**: {material}
                        """)
                    
                    with col_info2:
                        st.markdown(f"""
                        **⚙️ Especificaciones Técnicas**
                        - **Peso**: {float(peso) if peso else 'N/A'} g
                        - **Diámetro**: {float(diametro) if diametro else 'N/A'} mm
                        - **Fecha Solicitud**: {fecha_sol}
                        - **ID**: {id_sol}
                        """)
                    
                    st.markdown("---")
                    
                    # Botones de acción
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                    
                    with col_btn1:
                        if st.button(
                            "✅ Aprobar",
                            key=f"aprobar_{id_sol}",
                            type="primary",
                            use_container_width=True
                        ):
                            exito, error = aprobar_solicitud(id_sol)
                            if exito:
                                st.success(f"✅ '{nombre}' ha sido añadida al catálogo maestro!")
                                st.balloons()
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Error al aprobar: {error}")
                    
                    with col_btn2:
                        if st.button(
                            "❌ Rechazar",
                            key=f"rechazar_{id_sol}",
                            use_container_width=True
                        ):
                            exito, error = rechazar_solicitud(id_sol)
                            if exito:
                                st.warning(f"🗑️ Solicitud de '{nombre}' ha sido rechazada y eliminada")
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Error al rechazar: {error}")
                    
                    with col_btn3:
                        st.caption("⚠️ Las acciones son irreversibles")
            
            st.markdown("---")
            st.metric("Total de Solicitudes Pendientes", len(solicitudes))
    
    elif password_input:
        st.error("❌ Contraseña incorrecta. Acceso denegado.")
        st.warning("🔒 Solo los administradores pueden acceder a este panel")
    else:
        st.info("🔐 Ingresa la contraseña de administrador para continuar")
        st.caption("💡 Pista: Para testing usa 'admin123'")


# Pie de página
st.markdown("---")
st.caption("🪙 Aplicación de gestión de colección de monedas • Desarrollado con Streamlit y pg8000")


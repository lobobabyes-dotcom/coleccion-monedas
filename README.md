# 🪙 Colección de Monedas Numismática

Aplicación web para gestionar tu colección de monedas con valoración en tiempo real y reportes PDF.

## Características

- 📚 Gestión de catálogo maestro de monedas
- 🆕 Registro de nuevas adquisiciones
- 💸 Registro de ventas y cálculo de ganancias
- 💰 Valoración en tiempo real con precios de oro y plata
- 📊 Reportes PDF descargables
- ☁️ Base de datos en la nube con Neon PostgreSQL

## Tecnologías

- **Frontend:** Streamlit
- **Base de Datos:** PostgreSQL (Neon)
- **Gráficos:** Plotly
- **PDF:** FPDF
- **Datos de Mercado:** yfinance

## Instalación Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuración

Crea un archivo `.streamlit/secrets.toml` con:

```toml
[connections]
DATABASE_URL = "postgresql://user:pass@host/db"
```

## Despliegue

Desplegado en Streamlit Cloud con conexión segura a Neon PostgreSQL.

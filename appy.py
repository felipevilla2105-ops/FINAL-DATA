import pandas as pd
import streamlit as st
import plotly.express as px
from scipy.signal import find_peaks
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta


# --- 1. Cargar la base de datos ---
url="https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv"
df = pd.read_csv(url)

#mostrar las columnas disponibles
print("Columnas disponibles en el DataFrame:")
print(df.columns.tolist())



# --- 1. Definición de la Función de Análisis (Lógica Central) ---

@st.cache_data
def analizar_procesos(df: pd.DataFrame):
    """Aplica las reglas de negocio al DataFrame y retorna un DataFrame con las alertas."""
    
    # Limpieza de columnas y definición de constantes
    df.columns = df.columns.str.strip()
    
    COL_TIPO_NOTICIA = 'Tipo de Noticia'
    COL_FECHA_HECHOS = 'Fecha de los Hechos'
    COL_FECHA_DENUNCIA = 'Fecha de la denuncia'
    COL_FECHA_ULT_ACTUACION = 'Fecha Última Actuación'
    COL_ULT_ACTUACION = 'Última Actuación'
    
    # Conversión de Fechas a formato datetime (maneja errores en el formato)
    df[COL_FECHA_HECHOS] = pd.to_datetime(df[COL_FECHA_HECHOS], errors='coerce')
    df[COL_FECHA_DENUNCIA] = pd.to_datetime(df[COL_FECHA_DENUNCIA], errors='coerce')
    df[COL_FECHA_ULT_ACTUACION] = pd.to_datetime(df[COL_FECHA_ULT_ACTUACION], errors='coerce')

    # Fecha actual para comparaciones de antigüedad
    fecha_actual = datetime.now()
    limite_dos_meses = fecha_actual - relativedelta(months=+2)
    
    def aplicar_reglas(row):
        mensajes = []
        
        tipo_noticia = row[COL_TIPO_NOTICIA]
        fecha_hechos = row[COL_FECHA_HECHOS]
        fecha_denuncia = row[COL_FECHA_DENUNCIA]
        fecha_ult_actuacion = row[COL_FECHA_ULT_ACTUACION]
        ult_actuacion = row[COL_ULT_ACTUACION]
        
        # --- REGLA 1: Caducidad de la Querella (6 meses entre Hechos y Denuncia) ---
        if tipo_noticia == 'QUERELLABLE' and pd.notna(fecha_hechos) and pd.notna(fecha_denuncia):
            limite_caducidad = fecha_hechos + relativedelta(months=+6)
            if fecha_denuncia > limite_caducidad:
                mensajes.append("🔴 Caducidad de la querella")

        # --- REGLA 2: Actuaciones de Conciliación ---
        if pd.notna(ult_actuacion):
            actuacion = str(ult_actuacion).strip().upper()
            if 'CONCILIACION FRACASADA' in actuacion:
                mensajes.append("➡️ Continuar con el proceso")
            elif 'CONCILIACION CON ACUERDO' in actuacion:
                mensajes.append("✅ Proceder con el archivo")
                
        # --- REGLA 3: Proceso sin nuevas actuaciones en los últimos 2 meses ---
        if pd.notna(fecha_ult_actuacion) and fecha_ult_actuacion < limite_dos_meses:
            # Solo aplicamos el mensaje de "Avanzar" si no hay una acción de archivo/continuar de conciliación previa
            if not any(m in " ".join(mensajes) for m in ["Continuar con el proceso", "Proceder con el archivo"]):
                 mensajes.append("🟡 Avanzar con el proceso")
            
        # --- REGLA 4: Solicitud de información al denunciante hace más de 2 meses ---
        if pd.notna(ult_actuacion) and pd.notna(fecha_ult_actuacion):
            actuacion = str(ult_actuacion).strip().upper()
            if 'SOLICITUD A DENUNCIANTE DE INFORMACIÓN' in actuacion and fecha_ult_actuacion < limite_dos_meses:
                mensajes.append("✅ Se puede proceder con el archivo del caso")

        return ", ".join(mensajes) if mensajes else "🆗 Sin Alertas"

    # Aplicar la función al DataFrame
    df['Análisis Proceso'] = df.apply(aplicar_reglas, axis=1)
    
    # Filtramos y definimos las columnas de salida
    df_alertas = df[df['Análisis Proceso'] != "🆗 Sin Alertas"].copy()
    
    columnas_salida = ['Caso Noticia', 'Artículo', COL_TIPO_NOTICIA, COL_FECHA_HECHOS, 
                        COL_FECHA_DENUNCIA, COL_FECHA_ULT_ACTUACION, COL_ULT_ACTUACION, 
                        'Análisis Proceso']
                        
    # Retornamos solo las columnas de interés que existan en el DataFrame
    return df_alertas[[col for col in columnas_salida if col in df_alertas.columns]]

# --- 2. Configuración y Lógica de Streamlit ---

st.set_page_config(layout="wide")
st.title("🤖 Analizador de Alertas Judiciales")
st.markdown("Carga tu archivo CSV (`carga_ficticia_111.csv`) para ejecutar el análisis de querellas, conciliaciones y antigüedad de actuaciones.")

# Widget de carga de archivo
uploaded_file = st.file_uploader("Sube el archivo CSV", type="csv")

if uploaded_file is not None:
    try:
        # Cargar datos desde el archivo subido
        df_input = pd.read_csv(uploaded_file)
        
        # Ejecutar la lógica de análisis
        df_alertas = analizar_procesos(df_input)
        
        # --- 3. Despliegue de Resultados ---
        
        if not df_alertas.empty:
            st.success(f"✅ Análisis completado. Se encontraron **{len(df_alertas)}** procesos con alertas/acciones sugeridas.")
            
            st.subheader("🚨 Procesos que Requieren Acción o Revisión")
            # Mostrar el DataFrame de alertas
            st.dataframe(df_alertas, use_container_width=True)
            
            # Botón de Descarga
            csv_output = df_alertas.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Descargar Alertas en CSV",
                data=csv_output,
                file_name='alertas_procesos_analizados.csv',
                mime='text/csv',
            )
            
        else:
            st.info("✅ Excelente: No se encontraron procesos que cumplan con las condiciones de alerta/acción.")

    except Exception as e:
        st.error(f"❌ Ocurrió un error durante el procesamiento. Por favor, verifica el formato de tu archivo: {e}")

# ---
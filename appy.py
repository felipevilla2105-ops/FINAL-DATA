import pandas as pd
import numpy as np  
import matplotlib.pyplot as plt
import seaborn as sns       
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

url="https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv"
#leer el df separador ;     
df=pd.read_csv(url,sep=';')


# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="wide", page_title="Análisis de Procesos Judiciales")

st.image('IMG\IMAGEN .jpg', use_container_width=True)


# Nombre del archivo cargado (debe estar en el mismo directorio o se debe proporcionar la ruta completa)
# *Asegúrate de que este nombre coincida con tu archivo cargado*
FILE_PATH = 'https://github.com/felipevilla2105-ops/curso-talento-t/raw/refs/heads/main/carga_ficticia_111.csv' 

try:
    # Cargar el archivo CSV
    df = pd.read_csv(FILE_PATH)

    # Convertir columnas de fechas a datetime
    # Se utiliza 'errors="coerce"' para manejar posibles valores no válidos, convirtiéndolos a NaT (Not a Time)
    df['Fecha de los Hechos'] = pd.to_datetime(df['Fecha de los Hechos'], errors='coerce')
    df['Fecha de la denuncia'] = pd.to_datetime(df['Fecha de la denuncia'], errors='coerce')
    df['Fecha Última Actuación'] = pd.to_datetime(df['Fecha Última Actuación'], errors='coerce')

    # Fecha actual para comparación
    fecha_actual = datetime.now()

    # ======================================================================
    # 1. CADUCIDAD DE LA QUERELLA
    # ======================================================================
    st.header("1. CADUCIDAD DE LA QUERELLA")
    st.markdown("---")

    # Filtrar solo los casos 'QUERELLABLE' (se usa .str.upper() y .str.strip() para robustez)
    df_querellable = df[df['Tipo de Noticia'].str.upper().str.strip() == 'QUERELLA'].copy()

    # Calcular la diferencia en días entre la fecha de la denuncia y la fecha de los hechos
    df_querellable['Diferencia_Dias'] = (df_querellable['Fecha de la denuncia'] - df_querellable['Fecha de los Hechos']).dt.days

    # Aplicar la lógica de caducidad (más de 180 días es aproximadamente 6 meses)
    def check_caducidad(row):
        # La querella debe presentarse DENTRO de los 6 meses (180 días) desde los hechos.
        # Si la diferencia es > 180 (más de 6 meses), hay caducidad.
        if pd.notna(row['Diferencia_Dias']) and row['Diferencia_Dias'] > 180:
            return "❌ Caducidad de la querella"
        elif pd.notna(row['Diferencia_Dias']):
            return "✅ Querella vigente"
        return "⚠️ Datos de fecha incompletos"

    df_querellable['Análisis Caducidad'] = df_querellable.apply(check_caducidad, axis=1)

    # Mostrar resultados en Streamlit
    if not df_querellable.empty:
        df_caducidad_display = df_querellable[
             (df_querellable['Análisis Caducidad'] == "❌ Caducidad de la querella") |
             (df_querellable['Análisis Caducidad'] == "⚠️ Datos de fecha incompletos")
        ]
        
        if not df_caducidad_display.empty:
            st.subheader("Casos con posible Caducidad:")
            st.dataframe(
                df_caducidad_display[['Caso Noticia', 'Tipo de Noticia', 'Fecha de los Hechos', 'Fecha de la denuncia', 'Diferencia_Dias', 'Análisis Caducidad']]
            )
        else:
            st.info("No hay casos querellables que presenten caducidad o fechas incompletas.")
    else:
        st.info("No se encontraron casos con 'Tipo de Noticia' = 'QUERELLA'.")

    # ---
    
    # ======================================================================
    # 2. ÚLTIMAS ACTUACIONES (Inactividad General)
    # ======================================================================
    st.header("2. ÚLTIMAS ACTUACIONES")
    st.markdown("---")

    # Definir el umbral de inactividad (2 meses = 60 días)
    umbral_inactividad_dias = 60
    fecha_limite = fecha_actual - timedelta(days=umbral_inactividad_dias)

    # Casos cuya última actuación es anterior a la fecha límite de 2 meses
    df['Análisis Inactividad'] = df.apply(
        lambda row: "🚨 Avanzar con el proceso"
        if pd.notna(row['Fecha Última Actuación']) and row['Fecha Última Actuación'] < fecha_limite
        else "🟢 Actividad reciente",
        axis=1
    )

    # Filtrar solo los casos que cumplen la condición de inactividad
    df_avanzar = df[df['Análisis Inactividad'] == "🚨 Avanzar con el proceso"].copy()

    # Mostrar resultados
    if not df_avanzar.empty:
        st.subheader(f"Procesos con Inactividad de más de {umbral_inactividad_dias} días (2 meses):")
        st.dataframe(
            df_avanzar[['Caso Noticia', 'Fecha Última Actuación', 'Última Actuación', 'Análisis Inactividad']]
        )
    else:
        st.info("Todos los procesos tienen una 'Fecha Última Actuación' en los últimos 2 meses o la fecha está incompleta.")

    # ---

    # ======================================================================
    # 3. CONCILIACIÓN FRACASADA / CON ACUERDO
    # ======================================================================
    st.header("3. CONCILIACIÓN: Estado del Proceso")
    st.markdown("---")

    # Convertir a mayúsculas y limpiar espacios para asegurar la coincidencia
    df['Última Actuación Limpia'] = df['Última Actuación'].astype(str).str.upper().str.strip().fillna('')

    # Aplicar la lógica de conciliación
    def check_conciliacion(actuacion):
        if 'CONCILIACIÓN FRACASADA' in actuacion:
            return "➡️ Continuar con el proceso (Conciliación Fracasada)"
        elif 'CONCILIACIÓN CON ACUERDO' in actuacion:
            return "💾 Proceder con el archivo (Conciliación con Acuerdo)"
        return "No aplica o estado diferente"

    df['Análisis Conciliación'] = df['Última Actuación Limpia'].apply(check_conciliacion)

    # Filtrar solo los casos relevantes
    df_conciliacion = df[
        (df['Análisis Conciliación'] == "➡️ Continuar con el proceso (Conciliación Fracasada)") |
        (df['Análisis Conciliación'] == "💾 Proceder con el archivo (Conciliación con Acuerdo)")
    ].copy()

    # Mostrar resultados
    if not df_conciliacion.empty:
        st.subheader("Resultados Específicos de Conciliación:")
        st.dataframe(
            df_conciliacion[['Caso Noticia', 'Última Actuación', 'Análisis Conciliación']]
        )
    else:
        st.info("No se encontraron casos con 'Conciliación Fracasada' o 'Conciliación con Acuerdo'.")

    # ---

    # ======================================================================
    # 4. INACTIVIDAD DEL DENUNCIANTE
    # ======================================================================
    st.header("4. INACTIVIDAD DEL DENUNCIANTE")
    st.markdown("---")

    # Definir la actuación específica
    actuacion_buscada = 'SOLICITUD A DENUNCIANTE DE INFORMACIÓN ADICIONAL' # Usamos una parte de la cadena para ser flexibles
    umbral_denunciante_dias = 60 # 2 meses

    # Filtrar casos con la actuación específica
    df_denunciante = df[df['Última Actuación Limpia'].str.contains(actuacion_buscada.upper(), na=False)].copy()

    # Calcular la diferencia en días desde la última actuación
    df_denunciante['Días_Desde_Actuacion'] = (fecha_actual - df_denunciante['Fecha Última Actuación']).dt.days

    # Aplicar la lógica de inactividad del denunciante
    def check_inactividad_denunciante(row):
        if pd.notna(row['Días_Desde_Actuacion']) and row['Días_Desde_Actuacion'] > umbral_denunciante_dias:
            return "📂 Se puede proceder con el archivo del caso (Inactividad del denunciante)"
        elif pd.notna(row['Días_Desde_Actuacion']):
            return f"Pendiente (Han pasado {int(row['Días_Desde_Actuacion'])} días)"
        return "⚠️ Fecha de actuación incompleta"

    df_denunciante['Análisis Inactividad Denunciante'] = df_denunciante.apply(check_inactividad_denunciante, axis=1)

    # Filtrar solo los casos listos para archivo o pendientes
    df_archivo_denunciante = df_denunciante[
        df_denunciante['Análisis Inactividad Denunciante'].str.contains("proceder con el archivo") |
        df_denunciante['Análisis Inactividad Denunciante'].str.contains("Pendiente")
    ].copy()

    # Mostrar resultados
    if not df_archivo_denunciante.empty:
        st.subheader(f"Casos con '{actuacion_buscada}' para seguimiento:")
        st.dataframe(
            df_archivo_denunciante[['Caso Noticia', 'Fecha Última Actuación', 'Última Actuación', 'Días_Desde_Actuacion', 'Análisis Inactividad Denunciante']]
        )
    else:
        st.info(f"No hay casos con la actuación '{actuacion_buscada}' o los datos están incompletos.")


except FileNotFoundError:
    st.error(f"¡Error! El archivo '{FILE_PATH}' no se encontró. Asegúrate de que está en el mismo directorio.")
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
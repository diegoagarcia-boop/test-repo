import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from agents import ejecutar_agentes, ETAPAS
from utils import cargar_archivo, perfil

st.set_page_config(page_title='DataAgents AI', page_icon='📊', layout='wide')
st.title('📊 DataAgents AI')
st.caption('Proyecto integrador · Sistema multiagente de análisis de datos genéricos')
st.info('Versión inicial: análisis descriptivo con Python y 4 agentes Gemini. No reemplaza una auditoría humana.')

archivo = st.file_uploader('Sube CSV, Excel (.xlsx) o JSON (máximo 10 MB)', type=['csv','xlsx','json'])
if archivo is not None:
    try:
        df = cargar_archivo(archivo)
        datos = perfil(df)
    except Exception as exc:
        st.error(f'No se pudo procesar el archivo: {exc}')
        st.stop()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Registros', datos['registros'])
    col2.metric('Columnas', datos['columnas'])
    col3.metric('Datos faltantes', f"{datos['porcentaje_nulos']} %")
    col4.metric('Duplicados exactos', datos['duplicados_exactos'])
    tab1, tab2, tab3 = st.tabs(['Vista previa', 'Calidad de datos', 'Visualización'])
    with tab1:
        st.dataframe(df.head(30), use_container_width=True)
        st.caption('Solo se muestran 30 registros en pantalla; no se envían las filas originales a Gemini.')
    with tab2:
        st.dataframe(pd.DataFrame([{'Columna': c, 'Tipo': t,
                                   'Nulos': datos['nulos_por_columna'][c]}
                                  for c,t in datos['tipos'].items()]), hide_index=True)
        st.json(datos['indicadores_numericos'])
    with tab3:
        nums = datos['columnas_numericas']
        if nums:
            elegido = st.selectbox('Variable numérica', nums)
            st.plotly_chart(px.histogram(df, x=elegido, title=f'Distribución: {elegido}'), use_container_width=True)
        else:
            st.info('No se detectaron columnas numéricas para el histograma.')
    st.download_button('Descargar perfil estadístico (JSON)',
                       json.dumps(datos, indent=2, ensure_ascii=False).encode('utf-8'),
                       'perfil_datos.json', 'application/json')

    st.subheader('🤖 Red multiagente')
    st.caption('Los agentes reciben un resumen calculado, no el archivo original. Evita datos confidenciales.')
    try:
        api_key = st.secrets.get('GEMINI_API_KEY', os.getenv('GEMINI_API_KEY', ''))
    except Exception:
        api_key = os.getenv('GEMINI_API_KEY', '')
    modelo = st.text_input('Modelo Gemini habilitado en tu cuenta', value='gemini-2.5-flash-lite',
                           help='Si el modelo no está disponible en tu nivel gratuito, cámbialo por otro permitido en AI Studio.')
    if not api_key:
        st.warning('Falta configurar GEMINI_API_KEY en los secretos de Streamlit Cloud.')
    if st.button('Ejecutar los cuatro agentes', type='primary', disabled=not bool(api_key)):
        with st.spinner('Consultando Gemini en cuatro etapas; cada etapa consume una solicitud...'):
            try:
                resultado = ejecutar_agentes(datos, api_key, modelo)
                st.session_state['ultimo_informe'] = resultado
                st.session_state['archivo_analizado'] = archivo.name
            except Exception as exc:
                st.error('No se completó el análisis. Comprueba el modelo, la cuota gratuita y los secretos. '
                         + str(exc)[:450])
    resultado = st.session_state.get('ultimo_informe')
    if resultado and st.session_state.get('archivo_analizado') == archivo.name:
        for slug, titulo in ETAPAS:
            with st.expander(titulo, expanded=(slug=='informes')):
                st.markdown(resultado.get(slug, 'Sin respuesta.'))
        st.download_button('Descargar informe ejecutivo (.md)', resultado.get('informes', ''),
                           file_name='informe_dataagents.md', mime='text/markdown')
else:
    st.markdown('### Cómo empezar\nCarga una base de datos de prueba para ver su perfil y activar la red multiagente.')
st.divider()
st.caption('Prototipo académico · No subir datos personales ni información institucional reservada.')

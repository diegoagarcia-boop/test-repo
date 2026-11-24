import os,json,hashlib,io,time
import streamlit as st
import pandas as pd
import plotly.express as px
from agents import ejecutar_agentes,ETAPAS
from utils import cargar_archivo,perfil_avanzado,limpiar
from exports import exportar
st.set_page_config(page_title='DataAgents AI 3.0',page_icon='📊',layout='wide')
st.title('DataAgents AI 3.0'); st.caption('Inteligencia de negocios · Calidad · Analítica multiagente')
def secreto(k):
    try: return st.secrets.get(k,os.getenv(k,''))
    except Exception: return os.getenv(k,'')
claves={'Gemini':secreto('GEMINI_API_KEY'),'Groq':secreto('GROQ_API_KEY')}
with st.sidebar:
    st.header('Configuración')
    for p,k in claves.items(): st.write(p+': '+('Configurado' if k else 'Sin clave'))
    preferencia=st.radio('Proveedor preferido',['Groq','Gemini'])
    g=st.text_input('Modelo Gemini','gemini-3.6-flash'); q=st.text_input('Modelo Groq','openai/gpt-oss-120b')
    gm=[('Gemini',g),('Gemini','gemini-3.5-flash-lite')]; gr=[('Groq',q),('Groq','openai/gpt-oss-20b')]
    modelos=list(dict.fromkeys(gm+gr if preferencia=='Gemini' else gr+gm))
    st.subheader('Depuración')
    region=st.selectbox('Interpretación de fechas con barras',['Conservar ambiguas','Día/mes/año','Mes/día/año'])
    dup=st.checkbox('Eliminar duplicados exactos'); imp=st.checkbox('Imputar nulos numéricos con mediana')
st.warning('Solo datos públicos o ficticios. Los resúmenes se envían a proveedores externos. Las cuotas gratuitas son compartidas.')
a=st.file_uploader('Cargar CSV, XLSX o JSON (máximo 10 MB)',type=['csv','xlsx','json'])
if not a: st.stop()
try:
    original=cargar_archivo(a); df,cambios=limpiar(original,region,dup,imp); antes=perfil_avanzado(original); datos=perfil_avanzado(df); datos['limpieza']=cambios
except Exception as e: st.error('Archivo no procesable: '+str(e)); st.stop()
firma=hashlib.sha256(a.getvalue()+str((region,dup,imp)).encode()).hexdigest()
if st.session_state.get('firma')!=firma:
    st.session_state.firma=firma; st.session_state.estado={'resultados':{},'modelos':{},'eventos':[],'tiempos':{}}
estado=st.session_state.estado
for col,(label,v) in zip(st.columns(4),[('Registros',len(df)),('Variables',len(df.columns)),('Completitud',f"{100-datos['porcentaje_nulos']:.2f}%"),('Duplicados',datos['duplicados_exactos'])]): col.metric(label,v)
consent=st.checkbox('Confirmo que los datos son públicos o ficticios y autorizo enviar resúmenes a la IA')
c1,c2=st.columns(2)
if c2.button('Reiniciar análisis'):
    for v in estado.values(): v.clear()
if c1.button('Ejecutar / continuar análisis integral',type='primary',disabled=not consent or not any(claves.values()) or len(estado['resultados'])==4):
    if time.time()-st.session_state.get('ultima_ejecucion',0)<15: st.warning('Espera 15 segundos entre ejecuciones.')
    else:
        st.session_state.ultima_ejecucion=time.time(); barra=st.progress(len(estado['resultados'])/4); mensaje=st.empty()
        def avance(t,p,m): barra.progress(len(estado['resultados'])/4); mensaje.info(f'{t} · {p} · {m}')
        try:
            ok=ejecutar_agentes(datos,claves,modelos,estado,avance); barra.progress(len(estado['resultados'])/4)
            if ok: mensaje.success('Cuatro agentes completados')
            else: mensaje.warning('Servicio no disponible. Puedes continuar sin repetir etapas completadas.')
        except Exception: mensaje.error('No fue posible iniciar los proveedores.')
st.caption(f"Agentes completados: {len(estado['resultados'])}/4")
t1,t2,t3,t4,t5=st.tabs(['Datos','Calidad','Analítica','Agentes','Informes'])
with t1:
    st.subheader('Datos depurados'); st.dataframe(df.head(100)); st.download_button('Descargar CSV',df.to_csv(index=False).encode('utf-8-sig'),'datos.csv')
    with st.expander('Datos originales'): st.dataframe(original.head(100))
with t2:
    st.subheader('Comparación de calidad'); st.dataframe(pd.DataFrame({'Antes':antes['nulos_por_columna'],'Después':datos['nulos_por_columna']})); st.write(f"Registros: {len(original)} → {len(df)}")
    for c in cambios: st.markdown('- '+c)
    st.plotly_chart(px.bar(x=list(datos['nulos_por_columna']),y=list(datos['nulos_por_columna'].values()),labels={'x':'Variable','y':'Valores faltantes'}),use_container_width=True)
with t3:
    nums=datos['columnas_numericas']; cats=[c for c in datos['columnas_no_numericas'] if 1<df[c].nunique()<=30]
    if nums:
        st.dataframe(pd.DataFrame(datos['indicadores_numericos']).T); st.write('Atípicos por IQR (mínimo 4 observaciones)'); st.dataframe(pd.DataFrame([datos['atipicos_IQR']]))
        n=st.selectbox('Variable numérica',nums); st.plotly_chart(px.histogram(df,x=n,title='Distribución de '+n),use_container_width=True)
        if cats:
            c=st.selectbox('Agrupar por',cats); op=st.radio('Agregación',['sum','mean','count'],horizontal=True,format_func=lambda x:{'sum':'Suma','mean':'Promedio','count':'Conteo'}[x]); agg=df.groupby(c,dropna=True)[n].agg(op).reset_index(); st.plotly_chart(px.bar(agg,x=c,y=n,title='Comparación por '+c),use_container_width=True)
        if len(nums)>1: st.plotly_chart(px.imshow(df[nums[:12]].corr(min_periods=4),zmin=-1,zmax=1,title='Correlación de Pearson (mínimo 4 pares)'),use_container_width=True)
    else: st.info('No hay variables numéricas.')
    for c,f in datos['frecuencias_categoricas'].items():
        if f: st.plotly_chart(px.bar(x=list(f),y=list(f.values()),labels={'x':c,'y':'Frecuencia'},title='Categorías más frecuentes'),use_container_width=True)
with t4:
    for slug,titulo in ETAPAS:
        if slug in estado['resultados']:
            with st.expander(titulo,expanded=True):
                st.caption(estado['modelos'][slug]+' · '+str(estado['tiempos'].get(slug,'—'))+' s (intento exitoso)'); obj=estado['resultados'][slug]; st.write(obj['resumen'])
                for h in obj['hallazgos']: st.markdown('- '+h)
    if estado['eventos']: st.dataframe(pd.DataFrame(estado['eventos']))
with t5:
    if 'informes' in estado['resultados']:
        obj=estado['resultados']['informes']; st.subheader('Resumen ejecutivo'); st.write(obj['resumen'])
        for h in obj['hallazgos']: st.markdown('- '+h)
        try:
            for ext,contenido in exportar(original,df,antes,datos,estado).items(): st.download_button('Descargar '+ext.upper(),contenido,'informe.'+ext)
        except Exception: st.error('No fue posible generar los informes.')
        st.download_button('Resultados técnicos JSON',json.dumps(estado,ensure_ascii=False,indent=2),'resultados.json')
    else: st.info('Ejecuta el análisis integral para generar informes.')

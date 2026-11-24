import os,json,hashlib,io
import streamlit as st
import pandas as pd
import plotly.express as px
from agents import ejecutar_agentes,ETAPAS
from utils import cargar_archivo,perfil,limpiar
from docx import Document
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
st.set_page_config(page_title='DataAgents AI 2.0',page_icon='📊',layout='wide')
st.title('DataAgents AI 2.0'); st.caption('Analítica multiagente · Gemini + Groq')
def secreto(k):
    try: return st.secrets.get(k,os.getenv(k,''))
    except Exception: return os.getenv(k,'')
claves={'Gemini':secreto('GEMINI_API_KEY'),'Groq':secreto('GROQ_API_KEY')}
with st.sidebar:
    st.header('Configuración')
    for p,k in claves.items(): st.write(p+': '+('Configurado' if k else 'Sin clave'))
    preferencia=st.radio('Proveedor preferido',['Gemini','Groq'])
    g=st.text_input('Modelo Gemini','gemini-3.6-flash'); q=st.text_input('Modelo Groq','openai/gpt-oss-120b')
    gm=[('Gemini',g),('Gemini','gemini-3.5-flash-lite')]; gr=[('Groq',q),('Groq','openai/gpt-oss-20b')]
    modelos=list(dict.fromkeys(gm+gr if preferencia=='Gemini' else gr+gm))
st.warning('Usa únicamente datos públicos o ficticios. Los resúmenes pueden incluir categorías textuales y se envían a proveedores externos. Las cuotas gratuitas son compartidas por los visitantes.')
a=st.file_uploader('Cargar CSV, XLSX o JSON (máximo 10 MB)',type=['csv','xlsx','json'])
if not a: st.stop()
try: original=cargar_archivo(a); df,cambios=limpiar(original); datos=perfil(df); datos.pop('advertencia',None); datos['limpieza']=cambios
except Exception as e: st.error('Archivo no procesable: '+str(e)); st.stop()
firma=hashlib.sha256(a.getvalue()).hexdigest()
if st.session_state.get('firma')!=firma:
    st.session_state.firma=firma; st.session_state.estado={'resultados':{},'modelos':{},'eventos':[]}
estado=st.session_state.estado
for col,(label,v) in zip(st.columns(4),[('Registros',len(df)),('Columnas',len(df.columns)),('Nulos (%)',datos['porcentaje_nulos']),('Duplicados',datos['duplicados_exactos'])]): col.metric(label,v)
t1,t2,t3,t4=st.tabs(['Datos','Calidad','Dashboard','Agentes e informe'])
with t1:
    st.dataframe(df.head(100)); st.download_button('Descargar datos depurados CSV',df.to_csv(index=False).encode('utf-8-sig'),'datos.csv')
with t2:
    st.write(cambios); st.json({'antes':perfil(original),'despues':datos})
with t3:
    for c in datos['columnas_numericas'][:4]: st.plotly_chart(px.histogram(df,x=c,title=c),use_container_width=True)
    for c,f in datos['frecuencias_categoricas'].items():
        if f: st.plotly_chart(px.bar(x=list(f),y=list(f.values()),labels={'x':c,'y':'Frecuencia'}),use_container_width=True)
with t4:
    st.caption('Los agentes reciben estadísticas y frecuencias, no todas las filas. No se realiza clasificación exhaustiva de sentimientos en esta versión.')
    if st.button('Reiniciar análisis'): estado['resultados'].clear(); estado['modelos'].clear(); estado['eventos'].clear()
    if st.button('Ejecutar / continuar agentes',disabled=not any(claves.values())):
        barra=st.progress(len(estado['resultados'])/4); mensaje=st.empty()
        def avance(t,p,m): barra.progress(len(estado['resultados'])/4); mensaje.info(f'{t} · {p} · {m}')
        try:
            ok=ejecutar_agentes(datos,claves,modelos,estado,avance); barra.progress(len(estado['resultados'])/4)
            if ok: mensaje.success('Cuatro agentes completados')
            else: mensaje.warning('Servicio no disponible o respuesta inválida. Puedes continuar sin repetir etapas completadas.')
        except Exception: mensaje.error('No fue posible iniciar los proveedores. Revisa la configuración.')
    for slug,titulo in ETAPAS:
        if slug in estado['resultados']:
            with st.expander(titulo,expanded=slug=='informes'):
                st.caption(estado['modelos'][slug]); obj=estado['resultados'][slug]; st.write(obj['resumen']); st.write(obj['hallazgos'])
    if estado['eventos']: st.dataframe(pd.DataFrame(estado['eventos'])); st.download_button('Registro de errores',pd.DataFrame(estado['eventos']).to_csv(index=False),'errores.csv')
    if 'informes' in estado['resultados']:
        obj=estado['resultados']['informes']; lineas=['DataAgents AI — Informe ejecutivo',obj['resumen']]+obj['hallazgos']; doc=Document(); doc.add_heading(lineas[0],0)
        for l in lineas[1:]: doc.add_paragraph(l)
        b=io.BytesIO(); doc.save(b); st.download_button('Informe Word',b.getvalue(),'informe.docx')
        b=io.BytesIO(); styles=getSampleStyleSheet(); SimpleDocTemplate(b).build([Paragraph(escape(l),styles['BodyText']) for l in lineas]); st.download_button('Informe PDF',b.getvalue(),'informe.pdf')
        b=io.BytesIO()
        with pd.ExcelWriter(b,engine='openpyxl') as w:
            df.to_excel(w,index=False,sheet_name='Datos'); pd.DataFrame({'Informe':lineas}).to_excel(w,index=False,sheet_name='Informe')
        st.download_button('Informe Excel',b.getvalue(),'informe.xlsx')
        st.download_button('Resultados JSON',json.dumps(estado,ensure_ascii=False,indent=2),'resultados.json')

import os,json,hashlib,time,io
import pandas as pd
import streamlit as st
import plotly.express as px
from dashboard import generar
from motor import cargar,perfil,relaciones,cruzar
from utils import limpiar
from agents import ejecutar_agentes,ETAPAS
from exports import exportar_libro
st.set_page_config(page_title='DataAgents AI 5.0',layout='wide')
st.title('DataAgents AI 5.0'); st.caption('Analítica relacional · Calidad · Inteligencia multiagente')
def secreto(k):
    try: return st.secrets.get(k,os.getenv(k,''))
    except Exception: return os.getenv(k,'')
claves={p:secreto(p.upper()+'_API_KEY') for p in ['Groq','Gemini']}
with st.sidebar:
    st.header('Configuración'); pref=st.radio('Proveedor preferido',['Groq','Gemini']); q=st.text_input('Modelo Groq','openai/gpt-oss-120b'); g=st.text_input('Modelo Gemini','gemini-3.6-flash');
    gr=[('Groq',q),('Groq','openai/gpt-oss-20b')]; gm=[('Gemini',g),('Gemini','gemini-3.5-flash-lite')]; modelos=list(dict.fromkeys(gr+gm if pref=='Groq' else gm+gr))
    for p,k in claves.items(): st.write(p+': '+('Configurado' if k else 'Sin clave'))
    region=st.selectbox('Fechas con barras',['Conservar ambiguas','Día/mes/año','Mes/día/año']); dup=st.checkbox('Eliminar duplicados exactos')
st.warning('Solo datos públicos o ficticios. Los resúmenes se envían a proveedores externos. Cuotas gratuitas compartidas.')
a=st.file_uploader('Cargar archivo (máximo 10 MB)',type=['xlsx','csv','json']); objetivo=st.text_input('Objetivo del análisis','Análisis integral de calidad y patrones')
if not a: st.stop()
def procesar(raw,nombre,region,dup):
    b=io.BytesIO(raw); b.name=nombre; original=cargar(b); tabs={}; cambios={}
    for k,d in original.items(): tabs[k],cambios[k]=limpiar(d,region,dup,False)
    antes={k:perfil(d) for k,d in original.items()}; perfiles={k:perfil(d) for k,d in tabs.items()}; rel=relaciones(tabs,perfiles); return original,tabs,antes,perfiles,rel,cambios
try: original,tabs,antes,perfiles,rel,cambios=procesar(a.getvalue(),a.name,region,dup)
except Exception as e: st.error('No se pudo procesar: '+str(e)); st.stop()
resumen=pd.DataFrame([{'Tabla':k,'Registros':len(d),'Variables':len(d.columns),'Nulos':sum(perfiles[k]['nulos_por_columna'].values()),'Duplicados':perfiles[k]['duplicados_exactos']} for k,d in tabs.items()]);
for col,(label,v) in zip(st.columns(4),[('Tablas',len(tabs)),('Registros',sum(map(len,tabs.values()))),('Relaciones candidatas',len(rel)),('Nulos',int(resumen.Nulos.sum()))]): col.metric(label,v)
firma=hashlib.sha256(a.getvalue()+str((region,dup,objetivo,modelos)).encode()).hexdigest()
if st.session_state.get('firma')!=firma: st.session_state.firma=firma; st.session_state.estado={'resultados':{},'modelos':{},'eventos':[],'tiempos':{}}
e=st.session_state.estado
consent=st.checkbox('Autorizo enviar resúmenes de datos públicos o ficticios a la IA')
t1,t2,t3,t4,t5,t6=st.tabs(['General','Tablas y calidad','Relaciones','Analítica','Agentes','Informes'])
with t1: st.dataframe(resumen,hide_index=True)
with t2:
    k=st.selectbox('Tabla',list(tabs)); st.dataframe(tabs[k].head(100)); st.dataframe(pd.DataFrame({'Rol':perfiles[k]['roles'],'Nulos antes':antes[k]['nulos_por_columna'],'Nulos después':perfiles[k]['nulos_por_columna'],'Valores únicos':perfiles[k]['unicidad']})); st.dataframe(pd.DataFrame(perfiles[k]['alertas'])); [st.write('• '+str(x)) for x in cambios[k]]
with t3:
    st.caption('Relaciones candidatas por coincidencia de nombres y valores; confirme su significado antes de utilizar cruces.'); st.dataframe(pd.DataFrame(rel));
with t4:
    st.header('Dashboard automático integral')
    st.caption('Visualizaciones por tabla, sin enviar datos a IA. Selección por roles y reglas estadísticas.')
    for nombre,tabla in tabs.items():
        with st.expander(nombre,expanded=True):
            figs=generar(tabla)
            if not figs: st.info('Sin variables adecuadas para gráficos automáticos.')
            for i,fig in enumerate(figs): st.plotly_chart(fig,use_container_width=True,key=f'auto_{nombre}_{i}')
    st.header('Exploración y cruces opcionales')
    k2=st.selectbox('Tabla de análisis',list(tabs)); d=tabs[k2]; rr=[r for r in rel if r['hijo']==k2]; seleccion=st.multiselect('Relaciones autorizadas para cruzar',list(range(len(rr))),format_func=lambda i:f"{rr[i]['hijo']}.{rr[i]['foranea']} → {rr[i]['padre']}.{rr[i]['clave']}")
    if seleccion:
        d=cruzar(tabs,[rr[i] for i in seleccion],k2)
        for i,fig in enumerate(generar(d)): st.plotly_chart(fig,key=f'cruce_{i}')
    p=perfil(d); nums=p['columnas_numericas']; cats=list(p['frecuencias_categoricas']);
    if nums: st.dataframe(pd.DataFrame(p['indicadores_numericos']).T)
    if cats:
        c=st.selectbox('Categoría',cats); f=p['frecuencias_categoricas'][c]; st.write(f"{f['categorias']} categorías; {f['otras']} registros fuera del top 20"); st.plotly_chart(px.bar(x=list(f['top']),y=list(f['top'].values()),labels={'x':c,'y':'Frecuencia'}))
    if nums:
        n=st.selectbox('Medida',nums); st.plotly_chart(px.histogram(d,x=n));
        if cats: st.plotly_chart(px.bar(d.groupby(c)[n].sum(min_count=1).reset_index(),x=c,y=n,title='Suma por categoría'))
        if len(nums)>1: st.dataframe(d[nums].corr(min_periods=4))
        if len(nums)>1:
            x=st.selectbox('Factor A',nums); y=st.selectbox('Factor B',nums,index=1); prod=d[x]*d[y]; st.metric('Suma del producto (A × B)',f'{prod.sum(min_count=1):,.2f}'); st.caption(f'{prod.notna().sum()} filas válidas; no equivale necesariamente a ingresos.');
with t5:
    if st.button('Reiniciar agentes'): [v.clear() for v in e.values()]
    if st.button('Ejecutar / continuar análisis integral',disabled=not consent or not any(claves.values()) or len(e['resultados'])==4):
        if time.time()-st.session_state.get('ultima',0)<15: st.warning('Espera 15 segundos')
        else:
            st.session_state.ultima=time.time(); msg=st.empty(); payload={'objetivo':objetivo,'tablas':perfiles,'relaciones_candidatas':rel,'transformaciones':cambios,'analitica':[]};
            try: ejecutar_agentes(payload,claves,modelos,e,lambda t,p,m:msg.info(f'{t} · {p} · {m} · {len(e["resultados"])}/4'))
            except Exception: st.error('No se pudo conectar con los proveedores.')
    st.write(f"Agentes completados: {len(e['resultados'])}/4")
    for slug,t in ETAPAS:
        if slug in e['resultados']:
            with st.expander(t,expanded=True):
                st.caption(e['modelos'][slug]); st.write(e['resultados'][slug]['resumen']);
                for h in e['resultados'][slug]['hallazgos']: st.write('• '+h)
    st.dataframe(pd.DataFrame(e['eventos'])); st.caption('Tiempo máximo de espera IA: 115 segundos; puedes continuar resultados parciales.')
with t6:
    st.caption('Cifras calculadas por Python; narrativa de IA no verificada automáticamente.'); st.dataframe(resumen)
    if 'informes' in e['resultados']: st.write(e['resultados']['informes']['resumen'])
    if st.button('Preparar informes'):
        for ext,b in exportar_libro(original,tabs,resumen,perfiles,rel,e).items(): st.download_button('Descargar '+ext.upper(),b,'informe.'+ext)

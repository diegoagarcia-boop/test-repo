import os,json,hashlib,time,io
import pandas as pd
import streamlit as st
import plotly.express as px
from dashboard import generar
from discovery import descubrir, normalizar
from motor import cargar,perfil,relaciones,cruzar
from utils import limpiar
from agents import ejecutar_agentes,ETAPAS
from exports import exportar_libro
from bi import calcular, automaticos
from executive import ejecutivo
from agents import solicitar
import asyncio
st.set_page_config(page_title='DataAgents AI 8.0',layout='wide')
st.markdown("""<style>
[data-testid="stSidebar"] {background:#0F172A;color:#F1F5F9}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#E2E8F0}
[data-testid="stMetric"] {background:white;border:1px solid #DCE4EF;border-radius:12px;padding:16px;box-shadow:0 2px 5px #0f172a0b}
[data-testid="stExpander"] {background:white;border-radius:10px}
</style>""",unsafe_allow_html=True)
st.title('DataAgents AI 8.0'); st.caption('Intelligent Business Discovery · Decisiones basadas en evidencia')
def secreto(k):
    try: return st.secrets.get(k,os.getenv(k,''))
    except Exception: return os.getenv(k,'')
claves={p:secreto(p.upper()+'_API_KEY') for p in ['Groq','Gemini']}
with st.sidebar:
    st.header('Configuración'); pref=st.radio('Proveedor preferido',['Groq','Gemini']); q=st.text_input('Modelo Groq','openai/gpt-oss-120b'); g=st.text_input('Modelo Gemini','gemini-3.6-flash');
    gr=[('Groq',q),('Groq','openai/gpt-oss-20b')]; gm=[('Gemini',g),('Gemini','gemini-3.5-flash-lite')]; modelos=list(dict.fromkeys(gr+gm if pref=='Groq' else gm+gr))
    for p,k in claves.items(): st.write(p+': '+('Configurado' if k else 'Sin clave'))
    region=st.selectbox('Fechas con barras',['Conservar ambiguas','Día/mes/año','Mes/día/año']); dup=st.checkbox('Eliminar duplicados exactos'); normal=st.checkbox('Normalizar variantes de mayúsculas/minúsculas')
st.warning('Solo datos públicos o ficticios. Los resúmenes se envían a proveedores externos. Cuotas gratuitas compartidas.')
a=st.file_uploader('Cargar archivo (máximo 10 MB)',type=['xlsx','csv','json']); objetivo=st.text_input('Objetivo del análisis','Identificar oportunidades, riesgos y decisiones a partir de los datos')
if not a: st.stop()
@st.cache_data(show_spinner=False)
def procesar(raw,nombre,region,dup,normal):
    b=io.BytesIO(raw); b.name=nombre; original=cargar(b); tabs={}; cambios={}
    for k,d in original.items():
        tabs[k],cambios[k]=limpiar(d,region,dup,False)
        if normal:
            tabs[k],extra=normalizar(tabs[k]); cambios[k].extend(extra)
    antes={k:perfil(d) for k,d in original.items()}; perfiles={k:perfil(d) for k,d in tabs.items()}; rel=relaciones(tabs,perfiles); return original,tabs,antes,perfiles,rel,cambios
try: original,tabs,antes,perfiles,rel,cambios=procesar(a.getvalue(),a.name,region,dup,normal)
except Exception as e: st.error('No se pudo procesar: '+str(e)); st.stop()
resumen=pd.DataFrame([{'Tabla':k,'Registros':len(d),'Variables':len(d.columns),'Nulos':sum(perfiles[k]['nulos_por_columna'].values()),'Duplicados':perfiles[k]['duplicados_exactos']} for k,d in tabs.items()]);
for col,(label,v) in zip(st.columns(4),[('Tablas',len(tabs)),('Registros',sum(map(len,tabs.values()))),('Relaciones candidatas',len(rel)) if len(tabs)>1 else ('Variables',int(resumen.Variables.sum())),('Nulos',int(resumen.Nulos.sum()))]): col.metric(label,v)
firma=hashlib.sha256(a.getvalue()+str((region,dup,normal,objetivo,modelos)).encode()).hexdigest()
if st.session_state.get('firma')!=firma: st.session_state.firma=firma; st.session_state.estado={'resultados':{},'modelos':{},'eventos':[],'tiempos':{}}; st.session_state.pop('exports8',None)
e=st.session_state.estado
consent=st.checkbox('Autorizo enviar resúmenes de datos públicos o ficticios a la IA')
for k in tabs: perfiles[k]['patrones']=descubrir(tabs[k],perfiles[k])
labels=['Resumen ejecutivo','Calidad de datos']+(['Relaciones'] if len(tabs)>1 else [])+['Analítica','Agentes','Informes','Inteligencia de negocios','Consulta inteligente']
sections=st.tabs(labels); t1,t2=sections[:2]; t3=sections[2] if len(tabs)>1 else None; t4,t5,t6,tbi,tchat=sections[-5:]
with tbi:
    st.header('Indicadores y decisiones')
    base=st.selectbox('Tabla de hechos o análisis',list(tabs),key='bi_base')
    candidatos=[r for r in rel if r['hijo']==base]
    ids=st.multiselect('Autorizar cruces para inteligencia de negocios',range(len(candidatos)),format_func=lambda i:str(candidatos[i]))
    bd=cruzar(tabs,[candidatos[i] for i in ids],base)
    evidencia=automaticos(bd)
    st.caption('Indicadores automáticos descriptivos. Confirme el significado de las medidas antes de tomar decisiones.')
    op=st.selectbox('Construir indicador',['count','distinct','sum','mean','median','product','difference_product','ratio'])
    cols=list(bd.columns); nums=[c for c in cols if pd.api.types.is_numeric_dtype(bd[c])]
    spec={'op':op,'nombre':st.text_input('Nombre del indicador','Indicador personalizado')}
    if op!='count': spec['col']=st.selectbox('Variable',cols if op=='distinct' else nums,index=0 if (cols if op=='distinct' else nums) else None)
    if op in ('product','difference_product','ratio'): spec['factor']=st.selectbox('Segundo factor',nums,index=0 if nums else None)
    if op=='difference_product': spec['costo']=st.selectbox('Costo unitario',nums,index=0 if nums else None)
    spec['grupo']=st.selectbox('Agrupar por (opcional)',[None]+cols)
    if st.checkbox('Incluir indicador personalizado'):
        try: evidencia.insert(0,calcular(bd,spec))
        except Exception as ex: st.warning(str(ex))
    for i,r in enumerate(evidencia):
        with st.expander(r['indicador'],expanded=i<2):
            st.metric(r['indicador'],str(r['valor'])); st.caption(f"Cobertura: {r['validos']}/{r['filas']}")
            if r.get('grupos'): st.plotly_chart(px.bar(pd.DataFrame(r['grupos']),x='grupo',y='valor'),key=f'bi{i}')
    bf=hashlib.sha256(json.dumps([base,ids,evidencia],default=str).encode()).hexdigest()
    if st.session_state.get('bf')!=bf:
        st.session_state.bf=bf; e['resultados'].clear();e['modelos'].clear();e['tiempos'].clear();e['eventos'].clear();st.session_state.pop('exports8',None)
with t1:
    st.dataframe(resumen,hide_index=True)
    for r in evidencia[:4]: st.metric(r['indicador'],str(r['valor']))
    for slug in ('interprete','informes'):
        if slug in e['resultados']: st.write(e['resultados'][slug]['resumen'])
    if 'informes' not in e['resultados']: st.info('Ejecute los agentes para obtener recomendaciones ejecutivas.')
with tchat:
    pregunta=st.text_input('Pregunta sobre los datos')
    if st.button('Consultar evidencia',disabled=not consent or not pregunta or not any(claves.values())):
        for p,m in modelos:
            if not claves[p]: continue
            try:
                r=asyncio.run(solicitar(p,m,claves[p],'Responde solo con evidencia. Si falta un cálculo, indícalo. JSON resumen y hallazgos. Pregunta: '+pregunta+'\n'+json.dumps(evidencia,ensure_ascii=False,default=str)[:24000]));st.write(r['resumen']);st.write(r['hallazgos']);break
            except Exception: continue
        else: st.error('No se obtuvo respuesta del proveedor.')
with t2:
    k=st.selectbox('Tabla',list(tabs)); st.dataframe(tabs[k].head(100)); st.dataframe(pd.DataFrame({'Rol':perfiles[k]['roles'],'Nulos antes':antes[k]['nulos_por_columna'],'Nulos después':perfiles[k]['nulos_por_columna'],'Valores únicos':perfiles[k]['unicidad']})); st.dataframe(pd.DataFrame(perfiles[k]['alertas'])); 
    for x in cambios[k]:
        if x: st.write('• '+str(x))
if t3 is not None:
  with t3:
    st.caption('Relaciones candidatas por coincidencia de nombres y valores; confirme su significado antes de utilizar cruces.'); st.dataframe(pd.DataFrame(rel)) if rel else st.info("No se identificaron relaciones candidatas.")
with t4:
    st.header('Dashboard automático integral')
    st.caption('Visualizaciones por tabla, sin enviar datos a IA. Selección por roles y reglas estadísticas.')
    for nombre,tabla in tabs.items():
        with st.expander(nombre,expanded=True):
            figs=generar(tabla)
            for i,h in enumerate(perfiles[nombre]['patrones'][:8]):
                st.markdown('**'+h['tipo']+'** — '+h['detalle'])
                if 'grupos' in h:
                    g=pd.DataFrame(h['grupos']); st.dataframe(g,hide_index=True); st.plotly_chart(px.bar(g,x='grupo',y='tasa' if 'tasa' in g else 'media',title=h['variable']+' por '+h['categoria']),key=f'pat_{nombre}_{i}')
                else: st.write(' · '.join(f'{k}: {v}' for k,v in h.items() if k not in ['tipo','detalle','prioridad','variable','segunda']))
            if not figs: st.info('Sin variables adecuadas para gráficos automáticos.')
            for i in range(0,len(figs),2):
                for col,j in zip(st.columns(2),range(i,min(i+2,len(figs)))): col.plotly_chart(figs[j],use_container_width=True,key=f'auto_{nombre}_{j}')
    st.header('Exploración y cruces opcionales')
    k2=st.selectbox('Tabla de análisis',list(tabs)); d=tabs[k2]; rr=[r for r in rel if r['hijo']==k2]; seleccion=st.multiselect('Relaciones autorizadas para cruzar',list(range(len(rr))),format_func=lambda i:f"{rr[i]['hijo']}.{rr[i]['foranea']} → {rr[i]['padre']}.{rr[i]['clave']}") if rr else []
    if seleccion:
        d=cruzar(tabs,[rr[i] for i in seleccion],k2)
        for i,fig in enumerate(generar(d)): st.plotly_chart(fig,key=f'cruce_{i}')
    p=perfil(d); nums=p['columnas_numericas']; cats=list(p['frecuencias_categoricas']);
    if nums: st.dataframe(pd.DataFrame(p['indicadores_numericos']).T)
    if cats:
        c=st.selectbox('Categoría',cats); f=p['frecuencias_categoricas'][c]; st.write(f"{f['categorias']} categorías; {f['otras']} registros fuera del top 20"); st.plotly_chart(px.bar(x=list(f['top']),y=list(f['top'].values()),labels={'x':c,'y':'Frecuencia'}))
    if nums:
        n=st.selectbox('Medida',nums); st.plotly_chart(px.histogram(d,x=n));
        if cats:
            agg=st.selectbox('Agregación',['mean','median','sum','count'],format_func=lambda x: {'mean':'Media','median':'Mediana','sum':'Suma','count':'Conteo'}[x]); st.plotly_chart(px.bar(d.groupby(c)[n].agg(agg).reset_index(),x=c,y=n,title='Medida por categoría'))
        if len(nums)>1: st.dataframe(d[nums].corr(min_periods=4))
        if len(nums)>1 and st.checkbox("Construir indicador multiplicativo opcional"):
            x=st.selectbox('Factor A',nums); y=st.selectbox('Factor B',nums,index=1); prod=d[x]*d[y]; st.metric('Suma del producto (A × B)',f'{prod.sum(min_count=1):,.2f}'); st.caption(f'{prod.notna().sum()} filas válidas; no equivale necesariamente a ingresos.');
with t5:
    if st.button('Reiniciar agentes'):
        for v in e.values(): v.clear()
        st.session_state.pop('exports8',None)
    if st.button('Ejecutar / continuar análisis integral',disabled=not consent or not any(claves.values()) or len(e['resultados'])==4):
        if time.time()-st.session_state.get('ultima',0)<15: st.warning('Espera 15 segundos')
        else:
            st.session_state.pop('exports8',None); st.session_state.ultima=time.time(); msg=st.empty(); payload={'objetivo':objetivo,'bi':evidencia,'tablas':perfiles,'relaciones_candidatas':rel,'transformaciones':cambios,'analitica':{k:p['patrones'][:8] for k,p in perfiles.items()}};
            try: ejecutar_agentes(payload,claves,modelos,e,lambda t,p,m:msg.info(f'{t} · {p} · {m} · {len(e["resultados"])}/4'))
            except Exception: st.error('No se pudo conectar con los proveedores.')
    st.write(f"Agentes completados: {len(e['resultados'])}/4")
    for slug,t in ETAPAS:
        if slug in e['resultados']:
            with st.expander(t,expanded=True):
                st.caption(e['modelos'][slug]); st.write(e['resultados'][slug]['resumen']);
                for h in e['resultados'][slug]['hallazgos']: st.write('• '+h)
    if e['eventos']: st.dataframe(pd.DataFrame(e['eventos']))
    if e['tiempos']: st.dataframe(pd.DataFrame([{'Agente':k,'Segundos':v} for k,v in e['tiempos'].items()]),hide_index=True)
    st.caption('Tiempo máximo de espera IA: 115 segundos; puedes continuar resultados parciales.')
with t6:
    st.download_button('Descargar informe ejecutivo DOCX',ejecutivo(a.name,objetivo,evidencia,e),'informe_ejecutivo.docx')
    st.caption('Cifras calculadas por Python; narrativa de IA no verificada automáticamente.'); st.dataframe(resumen)
    if 'informes' in e['resultados']: st.write(e['resultados']['informes']['resumen'])
    if st.button('Preparar informes'):
        st.session_state['exports8']=(firma,exportar_libro(original,tabs,resumen,perfiles,rel,e,objetivo,a.name,cambios))
    if st.session_state.get('exports8',('',{}))[0]==firma:
        for ext,b in st.session_state['exports8'][1].items(): st.download_button('Descargar '+ext.upper(),b,'informe.'+ext)

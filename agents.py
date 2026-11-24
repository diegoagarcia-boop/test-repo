import json,time,asyncio
import httpx
from prompts import PROMPTS
ETAPAS=[('auditor','Auditor de datos'),('analista','Científico de datos'),('interprete','Consultor de inteligencia de negocios'),('informes','Asesor ejecutivo')]
async def solicitar(p,m,k,prompt):
    async with httpx.AsyncClient(timeout=28) as c:
        if p=='Groq':
            r=await c.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':'Bearer '+k},json={'model':m,'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'},'max_completion_tokens':2200}); r.raise_for_status(); raw=r.json()['choices'][0]['message']['content']
        else:
            r=await c.post('https://generativelanguage.googleapis.com/v1beta/models/'+m+':generateContent',headers={'x-goog-api-key':k},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':2200}}); r.raise_for_status(); raw=''.join(x.get('text','') for x in r.json()['candidates'][0]['content']['parts'] if not x.get('thought'))
    obj=json.loads(raw)
    if not isinstance(obj.get('resumen'),str) or not isinstance(obj.get('hallazgos'),list) or not all(isinstance(x,str) for x in obj['hallazgos']): raise ValueError('Formato inválido')
    return obj

def compacto(payload,slug):
    keys={'auditor':['registros','nulos_por_columna','duplicados_exactos','alertas','roles'],'analista':['indicadores_numericos','frecuencias_categoricas','correlaciones'],'interprete':['roles','unicidad','frecuencias_categoricas','indicadores_numericos','correlaciones'],'informes':['registros','nulos_por_columna','duplicados_exactos','indicadores_numericos']}[slug]
    return {'objetivo':payload['objetivo'],'indicadores_negocio':payload.get('bi',[])[:12] if slug in ('interprete','informes') else [],'relaciones':payload['relaciones_candidatas'],'tablas':{n:{k:p[k] for k in keys if k in p} for n,p in payload['tablas'].items()},'analitica':payload.get('analitica',[]),'transformaciones':payload['transformaciones'] if slug=='auditor' else {}}

def ejecutar_agentes(resumen,claves,modelos,estado,progreso=lambda *a:None):
    async def run():
        sem=asyncio.Semaphore(1)
        async def uno(slug,titulo):
            if slug in estado['resultados']: return
            data=compacto(resumen,slug)
            if slug in ('interprete','informes'): data['anteriores']={k:v['resumen'] for k,v in estado['resultados'].items()}; data['oportunidades']=resumen.get('oportunidades',[])
            raw=json.dumps(data,ensure_ascii=False,default=str)
            if len(raw)>55000:
                estado['eventos'].append({'agente':titulo,'error':'Resumen excede presupuesto; análisis local disponible'}); return
            prompt=PROMPTS[slug]+' Devuelve JSON con resumen (texto) y hallazgos (lista de textos). No inventes cifras.\n'+raw
            async with sem:
                for p,m in [(p,m) for p,m in modelos if claves.get(p)][:4]:
                    progreso(titulo,p,m); t=time.monotonic()
                    try:
                        obj=await asyncio.wait_for(solicitar(p,m,claves[p],prompt),30)
                        estado['resultados'][slug]=obj; estado['modelos'][slug]=p+' / '+m; estado['tiempos'][slug]=round(time.monotonic()-t,2); progreso(titulo,'Completado',m); return
                    except Exception as ex:
                        estado['eventos'].append({'agente':titulo,'proveedor':p,'modelo':m,'error':getattr(getattr(ex,'response',None),'status_code',None) or type(ex).__name__,'segundos':round(time.monotonic()-t,2)})
                        if getattr(getattr(ex,'response',None),'status_code',None)==429:
                            try: espera=float(ex.response.headers.get('retry-after','3'))
                            except ValueError: espera=3
                            await asyncio.sleep(min(15,max(1,espera)))
        await asyncio.gather(*(uno(*x) for x in ETAPAS[:2]))
        await uno(*ETAPAS[2])
        await uno(*ETAPAS[3])
    try: asyncio.run(asyncio.wait_for(run(),180))
    except asyncio.TimeoutError: estado['eventos'].append({'error':'Tiempo global agotado; resultados parciales conservados'})
    return len(estado['resultados'])==4

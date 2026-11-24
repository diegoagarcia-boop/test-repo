import json,time,asyncio,re
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone
import httpx
from prompts import PROMPTS
ETAPAS=[('auditor','Auditor de datos'),('analista','Científico de datos'),('interprete','Consultor de inteligencia de negocios'),('informes','Asesor ejecutivo')]
def normalizar_respuesta(raw):
    if not isinstance(raw,str) or not raw.strip(): raise ValueError('Respuesta vacía del modelo')
    raw=raw.strip(); raw=re.sub(r'^```(?:json)?\s*|\s*```$', '',raw,flags=re.I)
    try: obj=json.loads(raw)
    except json.JSONDecodeError as ex:
        try: obj=json.JSONDecoder().raw_decode(raw[raw.index('{'):])[0]
        except (ValueError,json.JSONDecodeError): raise ValueError(f'JSON incompleto o inválido (posición {ex.pos})') from None
    if not isinstance(obj,dict): raise ValueError('Se esperaba un objeto JSON')
    resumen=obj.get('resumen',obj.get('summary',''))
    hallazgos=obj.get('hallazgos',obj.get('findings',[]))
    if isinstance(hallazgos,str): hallazgos=[x.strip(' -•') for x in hallazgos.splitlines() if x.strip()]
    if not isinstance(hallazgos,list): hallazgos=[hallazgos]
    def texto(x):
        if isinstance(x,str): return x.strip()
        if isinstance(x,dict): return '; '.join(f'{k}: {texto(v)}' for k,v in x.items())
        if isinstance(x,list): return '; '.join(texto(v) for v in x)
        return '' if x is None else str(x)
    resumen=texto(resumen); hallazgos=[texto(x) for x in hallazgos]; hallazgos=[x for x in hallazgos if x]
    if not resumen and not hallazgos: raise ValueError('JSON sin resumen ni hallazgos reconocibles')
    return {'resumen':resumen or 'El modelo entregó hallazgos sin resumen.', 'hallazgos':hallazgos}

async def solicitar(p,m,k,prompt,tokens=4000):
    async with httpx.AsyncClient(timeout=28) as c:
        if p=='Groq':
            r=await c.post('https://api.groq.com/openai/v1/chat/completions',headers={'Authorization':'Bearer '+k},json={'model':m,'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'},'max_completion_tokens':tokens}); r.raise_for_status(); raw=r.json()['choices'][0]['message']['content']
        else:
            r=await c.post('https://generativelanguage.googleapis.com/v1beta/models/'+m+':generateContent',headers={'x-goog-api-key':k},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':tokens}}); r.raise_for_status(); raw=''.join(x.get('text','') for x in r.json()['candidates'][0]['content']['parts'] if not x.get('thought'))
    return normalizar_respuesta(raw)

def compacto(payload,slug):
    keys={'auditor':['registros','nulos_por_columna','duplicados_exactos','alertas','roles'],'analista':['indicadores_numericos','frecuencias_categoricas','correlaciones'],'interprete':['roles','unicidad','frecuencias_categoricas','indicadores_numericos','correlaciones'],'informes':['registros','nulos_por_columna','duplicados_exactos','indicadores_numericos']}[slug]
    return {'objetivo':payload['objetivo'],'indicadores_negocio':payload.get('bi',[])[:12] if slug in ('interprete','informes') else [],'relaciones':payload['relaciones_candidatas'],'tablas':{n:{k:p[k] for k in keys if k in p} for n,p in payload['tablas'].items()},'analitica':payload.get('analitica',[]),'transformaciones':payload['transformaciones'] if slug=='auditor' else {}}

def ejecutar_agentes(resumen,claves,modelos,estado,progreso=lambda *a:None,solo=None):
    async def run():
        bloqueados={}
        for slug,titulo in ETAPAS:
            if solo and slug!=solo: continue
            if slug in estado['resultados']: continue
            data=compacto(resumen,slug)
            if slug in ('interprete','informes'):
                data['anteriores']={k:v['resumen'] for k,v in estado['resultados'].items()}
                data['oportunidades']=resumen.get('oportunidades',[])
                data['agentes_previos_faltantes']=[k for k,_ in ETAPAS[:3 if slug=='informes' else 2] if k not in estado['resultados']]
            raw=json.dumps(data,ensure_ascii=False,default=str)
            if len(raw)>55000:
                estado['eventos'].append({'agente':titulo,'error':'Resumen excede presupuesto; análisis local disponible'}); continue
            prompt=PROMPTS[slug]+' Devuelve JSON con resumen (texto) y hallazgos (lista de textos). No inventes cifras. Si faltan agentes previos, declara el alcance parcial.\n'+raw
            for p,m in [(p,m) for p,m in modelos if claves.get(p)][:4]:
                if bloqueados.get((p,m),0)>time.monotonic(): continue
                for intento in range(2):
                    progreso(titulo,p,m); t=time.monotonic()
                    try:
                        obj=await asyncio.wait_for(solicitar(p,m,claves[p],prompt,6000 if slug in ('interprete','informes') else 4000),32)
                        estado['resultados'][slug]=obj; estado['modelos'][slug]=p+' / '+m; estado['tiempos'][slug]=round(time.monotonic()-t,2)
                        if slug!='informes' and 'informes' in estado['resultados']:
                            for campo in ('resultados','modelos','tiempos'): estado[campo].pop('informes',None)
                        progreso(titulo,'Completado',m); break
                    except Exception as ex:
                        resp=getattr(ex,'response',None); status=getattr(resp,'status_code',None)
                        detalle=str(ex)[:350] if isinstance(ex,ValueError) else (f'HTTP {status}' if status else type(ex).__name__)
                        estado['eventos'].append({'agente':titulo,'proveedor':p,'modelo':m,'error':status or type(ex).__name__,'detalle':detalle,'intento':intento+1,'segundos':round(time.monotonic()-t,2)})
                        if status==429:
                            h=resp.headers.get('retry-after','15')
                            try: espera=float(h)
                            except ValueError:
                                try: espera=(parsedate_to_datetime(h)-datetime.now(timezone.utc)).total_seconds()
                                except Exception: espera=15
                            bloqueados[(p,m)]=time.monotonic()+max(1,espera)
                            break
                        if intento==0 and (status==503 or isinstance(ex,(httpx.TimeoutException,asyncio.TimeoutError))):
                            await asyncio.sleep(2); continue
                        break
                if slug in estado['resultados']: break
    try: asyncio.run(asyncio.wait_for(run(),180))
    except asyncio.TimeoutError: estado['eventos'].append({'error':'Tiempo global agotado; resultados parciales conservados'})
    return len(estado['resultados'])==4

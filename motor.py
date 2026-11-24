import io,re,unicodedata,json
import pandas as pd
from utils import cargar_archivo,limpiar,perfil_avanzado

def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',str(s).strip().casefold()) if c.isalnum())
def cargar(a):
    if len(a.getvalue())>10_000_000: raise ValueError('Máximo 10 MB')
    if a.name.lower().endswith('.xlsx'):
        tabs=pd.read_excel(io.BytesIO(a.getvalue()),sheet_name=None,engine='openpyxl')
        for d in tabs.values(): d.columns=[str(c) for c in d.columns]
        return tabs
    return {'Datos':cargar_archivo(a)}
def rol(c,s):
    c=str(c).split('.')[-1]; n=norm(c); v=s.dropna(); u=v.nunique()
    if re.search(r'^(id|codigo|code|key|identificador)|(_id|id)$',str(c),re.I) or n.startswith(('codigo','identificador')): return 'Identificador'
    if 'fecha' in n or 'date' in n or pd.api.types.is_datetime64_any_dtype(s): return 'Fecha'
    if pd.api.types.is_numeric_dtype(s): return 'Medida'
    if len(v) and u/len(v)>.8 and u>10: return 'Texto descriptivo'
    return 'Categoría'
def perfil(d):
    roles={c:rol(c,d[c]) for c in d}; p=perfil_avanzado(d); p['roles']=roles; p['frecuencias_categoricas']={}; p['unicidad']={}; p['alertas']=[]
    for c,r in roles.items():
        s=d[c].dropna(); p['unicidad'][c]=int(s.nunique())
        if r!='Medida': p['indicadores_numericos'].pop(c,None); p['atipicos_IQR'].pop(c,None)
        if r=='Identificador': p['alertas'].append({'variable':c,'tipo':'Repeticiones de identificador (no necesariamente error)','cantidad':int(s.duplicated().sum())})
        if r=='Categoría':
            f=s.astype(str).value_counts(); top=f.head(20); p['frecuencias_categoricas'][c]={'categorias':int(len(f)),'validos':len(s),'mostradas':int(top.sum()),'otras':int(f.iloc[20:].sum()),'top':{str(k):int(v) for k,v in top.items()}}
            grupos={}
            for k in f.index: grupos.setdefault(norm(k),[]).append(k)
            variantes=[v for v in grupos.values() if len(v)>1]
            if variantes: p['alertas'].append({'variable':c,'tipo':'Variantes de etiquetas (revisar)','cantidad':len(variantes),'variantes':variantes})
        if r=='Fecha':
            def valida(x):
                if isinstance(x,str) and re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}',x): return any(pd.notna(pd.to_datetime(x,format=f,errors='coerce')) for f in ('%d/%m/%Y','%m/%d/%Y'))
                return pd.notna(pd.to_datetime(x,errors='coerce'))
            p['alertas'].append({'variable':c,'tipo':'Fechas inválidas','cantidad':int(sum(not valida(x) for x in s))})
        if r=='Medida': p['alertas'].append({'variable':c,'tipo':'Negativos (revisar significado)','cantidad':int((s<0).sum())})
    nums=[c for c,r in roles.items() if r=='Medida']; p['columnas_numericas']=nums; p['correlaciones']=json.loads(d[nums[:12]].corr(min_periods=4).to_json()); return p

def relaciones(tabs,profiles):
    out=[]
    for padre,d in tabs.items():
        for c,r in profiles[padre]['roles'].items():
            if r!='Identificador' or d.empty or d[c].isna().any() or not d[c].is_unique: continue
            for hijo,h in tabs.items():
                if hijo==padre: continue
                for k in h:
                    if norm(k)!=norm(c): continue
                    s=h[k].dropna(); ok=s.isin(d[c]);
                    if not len(s) or not ok.any(): continue
                    out.append({'padre':padre,'clave':c,'hijo':hijo,'foranea':k,'cardinalidad':'1:1' if s.is_unique else '1:N','sin_correspondencia':int((~ok).sum()),'nulos':int(h[k].isna().sum()),'coincidencias':int(ok.sum())})
    return out

def cruzar(tabs,rels,hijo):
    d=tabs[hijo].copy()
    for r in rels:
        if r['hijo']!=hijo: continue
        p=tabs[r['padre']].copy(); key=r['clave']; p=p.rename(columns={c:f"{r['padre']}.{c}" for c in p}); d=d.merge(p,left_on=r['foranea'],right_on=f"{r['padre']}.{key}",how='left',validate='many_to_one')
    return d

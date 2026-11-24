import pandas as pd
import numpy as np
from itertools import combinations
from motor import perfil, norm

def normalizar(d):
    d=d.copy(); cambios=[]; perfil_roles=perfil(d)['roles']
    for c in d:
        if perfil_roles[c]!='Categoría' or not pd.api.types.is_string_dtype(d[c]): continue
        f=d[c].dropna().astype(str).value_counts(); groups={}
        for v in f.index: groups.setdefault(v.strip().casefold(),[]).append(v)
        for vs in groups.values():
            if len(vs)>1:
                m={v:vs[0] for v in vs[1:]}; count=int(d[c].isin(m).sum()); d[c]=d[c].replace(m); cambios.append(f'{c}: {count} etiquetas normalizadas a {vs[0]}')
    return d,cambios

def descubrir(d,p=None):
    p=p or perfil(d); nums=p['columnas_numericas'][:20]; cats=[c for c in p['frecuencias_categoricas'] if 2<=d[c].nunique()<=30][:20]; out=[]
    def add(tipo,score,detalle,**kw): out.append(dict(tipo=tipo,prioridad=round(float(score),4),detalle=detalle,**kw))
    for n in d.columns:
        missing=d[n].isna(); total=int(missing.sum())
        if not total or total==len(d): continue
        for c in cats:
            if c==n: continue
            g=pd.DataFrame({'grupo':d[c],'ausente':missing}).groupby('grupo',observed=True)['ausente'].agg(['size','sum','mean']); g=g[g['size']>=5]
            if len(g)<2: continue
            diff=float(g['mean'].max()-g['mean'].min())
            if diff>=.5:
                add('Ausencia condicionada',diff,f'{n}: ausencia asociada a {c}; no implica error ni autoriza imputación.',variable=n,categoria=c,grupos=[{'grupo':str(i),'n':int(r['size']),'nulos':int(r['sum']),'tasa':round(float(r['mean']),4)} for i,r in g.iterrows()])
    for n in nums:
        s=pd.to_numeric(d[n],errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
        if len(s)<8: continue
        q1,q3=s.quantile([.25,.75]); iqr=q3-q1; med=s.median(); mad=(s-med).abs().median(); lo=hi=None
        if iqr>0: lo,hi=q1-1.5*iqr,q3+1.5*iqr; method='IQR'
        elif mad>0: lo,hi=med-3.5*mad/0.67449,med+3.5*mad/0.67449; method='MAD'
        elif s.std()>0: lo,hi=s.mean()-3*s.std(),s.mean()+3*s.std(); method='Z'
        if lo is not None:
            mask=(s<lo)|(s>hi); count=int(mask.sum())
            if count: add('Atípicos',.8,f'{n}: {count} valores fuera de límites {method}; revisar significado.',variable=n,metodo=method,n=len(s),cantidad=count,inferior=float(lo),superior=float(hi),minimo=float(s.min()),maximo=float(s.max()),mediana=float(med))
        for c in cats:
            g=d.groupby(c,observed=True)[n].agg(['count','mean','median']); g=g[g['count']>=5]
            if len(g)<2 or not s.std(): continue
            effect=float((g['mean'].max()-g['mean'].min())/s.std())
            if effect>=.35: add('Comparación de grupos',min(effect/2,1),f'{n} presenta diferencias descriptivas entre categorías de {c}.',variable=n,categoria=c,grupos=[{'grupo':str(i),'n':int(r['count']),'media':round(float(r['mean']),4),'mediana':round(float(r['median']),4)} for i,r in g.iterrows()])
    for a,b in combinations(nums,2):
        s=d[[a,b]].replace([np.inf,-np.inf],np.nan).dropna()
        if len(s)<8 or min(s.nunique())<2: continue
        pear=float(s[a].corr(s[b])); spear=float(s[a].rank().corr(s[b].rank())); score=max(abs(pear),abs(spear))
        if score>=.3: add('Asociación numérica',score,f'{a} y {b}: asociación descriptiva, no causalidad.',variable=a,segunda=b,n=len(s),pearson=round(pear,4),spearman=round(spear,4))
    return sorted(out,key=lambda x:-x['prioridad'])[:30]

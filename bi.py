import pandas as pd
from motor import rol, cruzar

def calcular(d, spec):
    op=spec['op']; c=spec.get('col'); b=spec.get('factor'); group=spec.get('grupo'); x=pd.Series(1.,index=d.index) if op=='count' else d[c]
    if op in ('sum','mean','median','product','difference_product','ratio'):
        if not pd.api.types.is_numeric_dtype(x): raise ValueError('Medida no numérica')
    if op in ('product','difference_product','ratio'):
        y=d[b]; x=x*y if op=='product' else (x-d[spec['costo']])*y if op=='difference_product' else x/y.where(y!=0)
    agg={'count':'sum','distinct':'nunique','sum':'sum','mean':'mean','median':'median','product':'sum','difference_product':'sum','ratio':'mean'}[op]
    def reduce(s): return s.sum(min_count=1) if agg=='sum' else getattr(s,agg)()
    val=reduce(x); out={'indicador':spec.get('nombre',op),'formula':spec,'valor':None if pd.isna(val) else float(val),'validos':int(x.notna().sum()),'filas':len(d)}
    if group:
        z=x.groupby(d[group],dropna=False).apply(reduce).sort_values(ascending=False).head(15); out['grupos']=[{'grupo':str(k),'valor':None if pd.isna(v) else float(v)} for k,v in z.items()]
    return out

def automaticos(d):
    roles={c:rol(c,d[c]) for c in d}; nums=[c for c,r in roles.items() if r=='Medida']; cats=[c for c,r in roles.items() if r=='Categoría' and 1<d[c].nunique()<=50]; specs=[{'nombre':'Registros analizados','op':'count'}]
    for c in nums[:8]:
        specs.append({'nombre':'Promedio de '+c,'op':'mean','col':c})
        for g in cats[:3]: specs.append({'nombre':c+' por '+g,'op':'mean','col':c,'grupo':g})
    for g in cats[:4]: specs.append({'nombre':'Registros por '+g,'op':'count','grupo':g})
    return [calcular(d,s) for s in specs]

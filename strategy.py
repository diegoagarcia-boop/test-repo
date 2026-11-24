import pandas as pd
import numpy as np
from motor import perfil
from discovery import descubrir

def oportunidades(d):
    p=perfil(d); out=[]
    for h in descubrir(d,p):
        if h['tipo']=='Comparación de grupos':
            g=sorted(h['grupos'],key=lambda x:x['media']); a,b=g[0],g[-1]
            out.append({'tipo':'Brecha entre segmentos','variable':h['variable'],'categoria':h['categoria'],'detalle':f"{b['grupo']}: {b['media']:.2f} (n={b['n']}); {a['grupo']}: {a['media']:.2f} (n={a['n']}). Brecha: {b['media']-a['media']:.2f}.",'accion':'Validar qué dirección representa mejor desempeño e investigar diferencias de composición.','prioridad':h['prioridad']})
        elif h['tipo']=='Asociación numérica':
            out.append({'tipo':'Asociación','variable':h['variable'],'detalle':f"{h['variable']} / {h['segunda']}: Pearson {h['pearson']}, Spearman {h['spearman']}, n={h['n']}.",'accion':'Evaluar hipótesis mediante comparación controlada; no asumir causalidad.','prioridad':h['prioridad']})
    return out[:12]

def tendencia(d,fecha,medida=None):
    f=pd.to_datetime(d[fecha].astype(str),format='%Y-%m-%d',errors='coerce'); z=pd.DataFrame({'mes':f.dt.to_period('M').astype(str),'valor':1 if medida is None else d[medida]}); z=z[f.notna()]; g=z.groupby('mes')['valor'].agg(['count','sum','mean']).reset_index(); g['valor']=g['count'] if medida is None else g['mean']; g['variacion_pct']=g['valor'].pct_change(fill_method=None).mul(100).replace([np.inf,-np.inf],np.nan); return g

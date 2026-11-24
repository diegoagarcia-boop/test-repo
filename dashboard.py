import pandas as pd
import plotly.express as px
from motor import perfil

def generar(d):
    p=perfil(d); nums=p['columnas_numericas']; cats=list(p['frecuencias_categoricas']); figs=[]
    for c in cats[:2]:
        f=p['frecuencias_categoricas'][c]; labels=list(f['top']); vals=list(f['top'].values());
        if f['otras']: labels.append('Otras categorías (agrupadas)'); vals.append(f['otras'])
        if len(vals)<2 or (len(set(vals))==1 and f['otras']==0): continue
        x=pd.DataFrame({'Categoría':labels,'Frecuencia':vals})
        figs.append(px.pie(x,names='Categoría',values='Frecuencia',hole=.55,title='Composición: '+c) if 2<=len(x)<=8 else px.bar(x,x='Frecuencia',y='Categoría',orientation='h',title='Frecuencias: '+c))
    for n in nums[:2]:
        figs.extend([px.histogram(d,x=n,title='Distribución: '+n),px.box(d,y=n,title='Dispersión y extremos: '+n)])
    if len(nums)>1:
        figs.append(px.scatter(d.head(3000),x=nums[0],y=nums[1],title='Relación (primeras 3.000 filas)'))
        co=d[nums[:10]].corr(min_periods=4); figs.append(px.imshow(co,zmin=-1,zmax=1,color_continuous_scale='RdBu_r',title='Correlaciones de Pearson'))
    dates=[c for c,r in p['roles'].items() if r=='Fecha']
    if dates:
        c=dates[0]; dt=pd.to_datetime(d[c].astype(str).str[:10],format='%Y-%m-%d',errors='coerce'); f=dt.dropna().dt.to_period('M').astype(str).value_counts().sort_index()
        if len(f): figs.append(px.line(x=f.index,y=f.values,markers=True,labels={'x':'Mes','y':'Registros'},title=f'Evolución mensual: {c} ({dt.notna().sum()} fechas ISO válidas)'))
    if cats and nums:
        c,n=cats[0],nums[0]; f=d.groupby(c)[n].mean().dropna().nlargest(15); figs.append(px.bar(x=f.values,y=f.index.astype(str),orientation='h',labels={'x':'Media de '+n,'y':c},title='Media por categoría (top 15)'))
    for fig in figs: fig.update_layout(height=320,margin=dict(l=35,r=20,t=55,b=35),paper_bgcolor="white",plot_bgcolor="white")
    return figs

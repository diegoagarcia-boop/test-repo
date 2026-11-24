import io
import json
import re
import pandas as pd


def cargar_archivo(archivo):
    nombre = archivo.name.lower()
    contenido = archivo.getvalue()
    if len(contenido) > 10_000_000:
        raise ValueError("Archivo superior a 10 MB. Prueba con una muestra anonimiz ada".replace("anonimiz ada", "anonimizada"))
    if nombre.endswith('.csv'):
        errores = []
        for codificacion in ('utf-8-sig', 'latin-1'):
            try:
                df = pd.read_csv(io.BytesIO(contenido), sep=None, engine='python', encoding=codificacion)
                break
            except Exception as e:
                errores.append(str(e))
        else:
            raise ValueError("No fue posible interpretar el CSV: " + errores[-1])
    elif nombre.endswith('.xlsx'):
        df = pd.read_excel(io.BytesIO(contenido), engine='openpyxl')
    elif nombre.endswith('.json'):
        obj = json.loads(contenido.decode('utf-8-sig'))
        if isinstance(obj, dict):
            if len(obj) == 1 and isinstance(next(iter(obj.values())), list):
                obj = next(iter(obj.values()))
            else:
                obj = [obj]
        if not isinstance(obj, list):
            raise ValueError("El JSON debe contener una lista de registros o un objeto.")
        df = pd.json_normalize(obj)
    else:
        raise ValueError("Formato no compatible. Utiliza CSV, XLSX o JSON.")
    if df.empty:
        raise ValueError("La base de datos no contiene registros.")
    # Conservar datos originales y evitar nombres de columna vacíos o repetidos.
    nombres = []
    usados = set()
    for i, c in enumerate(df.columns):
        original = str(c).strip()
        if not original or original.lower().startswith('unnamed:'):
            original = f'columna_{i+1}'
        base = re.sub(r'\s+', '_', original)
        nombre_col = base
        n = 2
        while nombre_col in usados:
            nombre_col = f'{base}_{n}'
            n += 1
        usados.add(nombre_col)
        nombres.append(nombre_col)
    df.columns = nombres
    return df


def perfil(df):
    filas = len(df)
    columnas = len(df.columns)
    missing = df.isna().sum()
    tipos = {c: str(t) for c, t in df.dtypes.items()}
    numericas = list(df.select_dtypes(include='number').columns)
    categorias = [c for c in df.columns if c not in numericas]
    resumen_num = {}
    for c in numericas[:12]:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(s):
            resumen_num[c] = {'conteo': int(s.count()), 'media': round(float(s.mean()), 4),
                              'mediana': round(float(s.median()), 4), 'min': round(float(s.min()), 4),
                              'max': round(float(s.max()), 4), 'suma': round(float(s.sum()), 4)}
    frecuencia = {}
    for c in categorias[:8]:
        # Sólo frecuencias de categorías cortas, nunca muestras de texto libre.
        val = df[c].dropna().astype(str)
        if len(val) and val.str.len().median() <= 45:
            frecuencia[c] = {str(k)[:60]: int(v) for k,v in val.value_counts().head(5).items()}
    return {'registros': filas, 'columnas': columnas, 'tipos': tipos,
            'columnas_numericas': numericas, 'columnas_no_numericas': categorias,
            'nulos_por_columna': {str(k): int(v) for k,v in missing.items()},
            'porcentaje_nulos': round(100 * int(missing.sum()) / max(1, filas*columnas), 2),
            'duplicados_exactos': int(df.duplicated().sum()),
            'indicadores_numericos': resumen_num, 'frecuencias_categoricas': frecuencia,
            'advertencia': 'Las fechas en formato texto y números con caracteres mixtos requieren validación adicional.'}


# Limpieza conservadora, con política regional explícita.
def limpiar(df, region='Conservar ambiguas', duplicados=False, imputar=False):
    df=df.copy(); cambios=[]
    for c in df.select_dtypes(include=['object','string']).columns:
        s=df[c].map(lambda x:x.strip() if isinstance(x,str) else x).replace('',pd.NA)
        df[c]=s
        if re.search(r'fecha|date',c,re.I):
            formatos=set(); pendientes=0; convertidas=0
            def convertir(x):
                nonlocal pendientes,convertidas
                if pd.isna(x): return x
                x=str(x); fmt=None
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}',x): fmt='%Y-%m-%d'
                elif re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}',x):
                    a,b,_=map(int,x.split('/')); formatos.add('Con barras')
                    if region=='Día/mes/año' or a>12: fmt='%d/%m/%Y'
                    elif region=='Mes/día/año' or b>12: fmt='%m/%d/%Y'
                if fmt:
                    formatos.add('ISO' if fmt=='%Y-%m-%d' else 'Con barras')
                    t=pd.to_datetime(x,format=fmt,errors='coerce')
                    if pd.notna(t):
                        y=t.strftime('%Y-%m-%d'); convertidas+=int(y!=x); return y
                pendientes+=1; return x
            df[c]=s.map(convertir)
            cambios.append(f'{c}: {len(formatos)} formatos reconocidos; {convertidas} conversiones; {pendientes} fechas pendientes.')
    cambios.append('Espacios recortados y cadenas vacías convertidas a nulos.')
    if duplicados:
        n=len(df); df=df.drop_duplicates(); cambios.append(f'Duplicados eliminados: {n-len(df)}.')
    if imputar:
        for c in df.select_dtypes(include='number'):
            n=int(df[c].isna().sum()); m=df[c].median()
            if n and pd.notna(m): df[c]=df[c].astype(float).fillna(m); cambios.append(f'{c}: {n} nulos imputados con mediana {m}.')
    return df,cambios

def perfil_avanzado(df):
    p=perfil(df); p.pop('advertencia',None); p['atipicos_IQR']={}
    for c in p['columnas_numericas'][:12]:
        s=df[c].dropna(); q1,q3=s.quantile([.25,.75]); d=q3-q1
        p['atipicos_IQR'][c]=int(((s<q1-1.5*d)|(s>q3+1.5*d)).sum()) if len(s)>=4 else None
    corr=df[p['columnas_numericas'][:12]].corr(min_periods=4)
    p['correlaciones']=json.loads(corr.to_json())
    return p

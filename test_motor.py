import sys,io
from pathlib import Path
from motor import cargar,perfil,relaciones,cruzar
from utils import limpiar
if __name__=='__main__':
    p=Path(sys.argv[1]); b=io.BytesIO(p.read_bytes()); b.name=p.name
    t=cargar(b); ps={k:perfil(d) for k,d in t.items()}; r=relaciones(t,ps)
    assert len(t)==4 and sum(map(len,t.values()))==15588
    assert sum(sum(p['nulos_por_columna'].values()) for p in ps.values())==11
    assert sum(p['duplicados_exactos'] for p in ps.values())==6
    assert len(r)==3 and sorted(x['sin_correspondencia'] for x in r)==[4,5,9]
    assert ps['Clientes']['unicidad']['IdCliente']==500
    assert ps['Clientes']['frecuencias_categoricas']['Ciudad']['mostradas']==500
    assert len(cruzar(t,r,'Ventas'))==15000
    print('Pruebas Brújula correctas:',r)

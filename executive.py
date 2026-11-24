import io
from docx import Document
from docx.shared import RGBColor

def ejecutivo(nombre,objetivo,bi,estado):
    d=Document(); d.add_heading('DataAgents AI 8.0 | Informe ejecutivo',0); d.add_paragraph(nombre); d.add_paragraph(objetivo)
    d.add_heading('Decisiones y hallazgos',1)
    for k in ('interprete','informes'):
        r=estado['resultados'].get(k)
        if r:
            d.add_heading(k.capitalize(),2); d.add_paragraph(r['resumen'])
            for h in r['hallazgos']: d.add_paragraph(h,style='List Bullet')
    if 'informes' not in estado['resultados']: d.add_paragraph('Síntesis IA pendiente; resultados parciales.')
    d.add_heading('Evidencia calculada',1)
    for r in bi:
        d.add_heading(r['indicador'],2); d.add_paragraph(f"Valor: {r['valor']} | Cobertura: {r['validos']}/{r['filas']} | Operación: {r['formula']}")
        if r.get('grupos'):
            t=d.add_table(rows=1,cols=2); t.style='Light Shading Accent 1'; t.rows[0].cells[0].text='Grupo'; t.rows[0].cells[1].text='Valor'
            for g in r['grupos']:
                c=t.add_row().cells;c[0].text=g['grupo'];c[1].text=str(g['valor'])
    d.add_paragraph('Interpretaciones IA sujetas a validación. Indicadores derivados dependen de las definiciones y cruces autorizados.'); b=io.BytesIO();d.save(b);return b.getvalue()

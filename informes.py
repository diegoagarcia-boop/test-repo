import io, datetime
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def documentos(resumen,perfiles,rel,estado,objetivo,archivo,cambios):
    doc=Document(); sec=doc.sections[0]; sec.header.paragraphs[0].text='DATAAGENTS AI 6.0  |  INTELIGENCIA DE DATOS'; sec.footer.paragraphs[0].text='DataAgents AI  •  Informe analítico'
    sec.left_margin=sec.right_margin=Inches(.8)
    doc.styles['Normal'].font.name='Calibri'; doc.styles['Normal'].font.size=Pt(10)
    styles=getSampleStyleSheet(); styles['Heading1'].textColor=colors.HexColor('#173650'); story=[]
    def clean(x): return escape(str(x).replace('−','-').replace('‑','-').replace('→',' a ').replace(' ',' ').replace('≈','aprox. '))
    def text(x):
        doc.add_paragraph(str(x)); story.extend([Paragraph(clean(x),styles['BodyText']),Spacer(1,5)])
    def heading(x):
        doc.add_heading(x,1); story.append(Paragraph(clean(x),styles['Heading1']))
    def table(headers,rows,widths):
        if not rows: text('Sin registros para mostrar.'); return
        t=doc.add_table(rows=1,cols=len(headers)); t.style='Light Shading Accent 1'
        for c,v in zip(t.rows[0].cells,headers): c.text=str(v)
        from docx.oxml import OxmlElement
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for row in rows:
            for c,v in zip(t.add_row().cells,row): c.text=str(v)
        data=[[Paragraph(clean(v),styles['BodyText']) for v in row] for row in [headers]+rows]
        tb=Table(data,colWidths=widths,repeatRows=1); tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE8F5')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F5F9')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#2563EB'))])); story.extend([tb,Spacer(1,10)])
    def chart(labels,values,title):
        if not labels:return
        fig,ax=plt.subplots(figsize=(7, max(2.4,min(5,len(labels)*.32+1)))); ax.barh(labels,values,color='#2563EB'); ax.invert_yaxis(); ax.set_title(title); fig.tight_layout(); b=io.BytesIO(); fig.savefig(b,format='png',dpi=140); plt.close(fig); png=b.getvalue(); doc.add_picture(io.BytesIO(png),width=Inches(6)); story.extend([Image(io.BytesIO(png),width=460,height=460*fig.get_figheight()/7),Spacer(1,8)])
    title='Informe integral de análisis de datos'; doc.add_heading(title,0); story.append(Paragraph(title,styles['Title'])); text('DataAgents AI 6.0 | Professional BI'); text(archivo); text(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')); text('Objetivo: '+objetivo); text('Resultados calculados localmente. Las relaciones son candidatas y las interpretaciones de IA requieren validación.'); doc.add_page_break(); story.append(PageBreak())
    heading('1. Resumen ejecutivo'); text(f"{len(resumen)} tablas, {int(resumen.Registros.sum()):,} registros, {int(resumen.Nulos.sum())} celdas nulas y {int(resumen.Duplicados.sum())} duplicados exactos adicionales.")
    if 'informes' in estado['resultados']: text(estado['resultados']['informes']['resumen'])
    heading('2. Caracterización de datos'); table(list(resumen.columns),resumen.values.tolist(),[150,80,75,75,85]); chart(resumen.Tabla.astype(str).tolist()[:15],resumen.Registros.tolist()[:15],'Registros por tabla (hasta 15)')
    heading('3. Hallazgos de calidad'); rows=[]
    for k,p in perfiles.items():
        for c,n in p['nulos_por_columna'].items():
            if n: rows.append([k,c,'Valores nulos',n])
        if p['duplicados_exactos']: rows.append([k,'Fila completa','Duplicados exactos adicionales',p['duplicados_exactos']])
        for a in p['alertas']:
            if a['cantidad']: rows.append([k,a['variable'],a['tipo'],a['cantidad']])
    table(['Tabla','Variable','Hallazgo','Cantidad'],rows,[95,100,215,55]); text('Las incidencias pueden solaparse. Las repeticiones de claves foráneas no son necesariamente errores.')
    for k,p in perfiles.items():
        for a in p['alertas']:
            if a.get('variantes'): text(k+' / '+a['variable']+': '+'; '.join(' / '.join(g) for g in a['variantes']))
    heading('4. Integridad referencial'); table(['Origen','Destino','Cardinalidad','Coinciden','Sin relación','Nulos'],[[r['padre']+'.'+r['clave'],r['hijo']+'.'+r['foranea'],r['cardinalidad'],r['coincidencias'],r['sin_correspondencia'],r['nulos']] for r in rel],[110,110,65,65,65,50])
    heading('5. Estadísticas descriptivas')
    for k,p in perfiles.items():
        if p['indicadores_numericos']:
            text(k); table(['Variable','Indicador','Valor'],[[c,m,round(v,4) if isinstance(v,float) else v] for c,stats in p['indicadores_numericos'].items() for m,v in stats.items()],[150,150,165])
        for c,f in list(p['frecuencias_categoricas'].items())[:2]:
            labels=list(f['top']); vals=list(f['top'].values());
            if f['otras']: labels.append('Otras'); vals.append(f['otras'])
            if 2<=len(labels)<=20 and len(set(vals))>1: chart(labels,vals,k+' / '+c)
    heading('6. Transformaciones aplicadas')
    for k,items in cambios.items():
        for item in items:
            if item: text(k+': '+str(item))
    heading('7. Interpretación y recomendaciones de IA'); text('Narrativa no verificada automáticamente. No aplicar cambios destructivos sin autorización.')
    names={'auditor':'Calidad de datos','analista':'Interpretación estadística','interprete':'Contexto','informes':'Recomendaciones consolidadas'}; seen=set()
    for k in names:
        v=estado['resultados'].get(k)
        if not v: continue
        heading(names[k]);
        if k!='informes': text(v['resumen'])
        for h in v['hallazgos']:
            key=h.strip().casefold()
            if key not in seen: text('• '+h); seen.add(key)
    heading('8. Trazabilidad'); table(['Agente','Proveedor y modelo','Segundos'],[[names.get(k,k),v,estado.get('tiempos',{}).get(k,'—')] for k,v in estado['modelos'].items()],[145,240,80]); text(f"Agentes completados: {len(estado['resultados'])}/4.")
    b=io.BytesIO(); doc.save(b); out={'docx':b.getvalue()}; b=io.BytesIO()
    def footer(canvas,d): canvas.setFont('Helvetica',9); canvas.setFillColor(colors.HexColor('#173650')); canvas.drawString(65,35,'DataAgents AI 6.0'); canvas.drawRightString(530,35,str(d.page))
    SimpleDocTemplate(b,pagesize=A4,leftMargin=65,rightMargin=65,topMargin=48,bottomMargin=50).build(story,onFirstPage=footer,onLaterPages=footer); out['pdf']=b.getvalue(); return out

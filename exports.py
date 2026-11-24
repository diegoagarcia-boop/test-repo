import io,datetime
import pandas as pd
from docx import Document
from docx.shared import Inches
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from xml.sax.saxutils import escape
from openpyxl.styles import Font,PatternFill
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def exportar(original,df,antes,datos,estado):
    obj=estado['resultados']['informes']; fecha=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    titulo='DataAgents AI 3.0 — Informe ejecutivo'; filas=[['Indicador','Antes','Después'],['Registros',len(original),len(df)],['Nulos (%)',antes['porcentaje_nulos'],datos['porcentaje_nulos']],['Duplicados',antes['duplicados_exactos'],datos['duplicados_exactos']]]
    fig,ax=plt.subplots(figsize=(7,2.8)); n=pd.Series(datos['nulos_por_columna']).head(20); ax.bar(n.index,n.values); ax.set_ylabel('Nulos'); ax.tick_params(axis='x',rotation=35); fig.tight_layout(); img=io.BytesIO(); fig.savefig(img,format='png',dpi=120); plt.close(fig); png=img.getvalue()
    modelos=[f'{k}: {v}' for k,v in estado['modelos'].items()]; secciones=[('Resumen ejecutivo',[obj['resumen']]),('Hallazgos y recomendaciones',obj['hallazgos']),('Transformaciones',datos['limpieza']),('Trazabilidad',modelos)]
    doc=Document(); doc.add_heading(titulo,0); doc.add_paragraph(fecha); t=doc.add_table(rows=0,cols=3); t.style='Light Shading Accent 1'
    for fila in filas:
        for c,v in zip(t.add_row().cells,fila): c.text=str(v)
    doc.add_picture(io.BytesIO(png),width=Inches(6))
    for h,ls in secciones:
        doc.add_heading(h,1)
        for l in ls: doc.add_paragraph(l)
    b=io.BytesIO(); doc.save(b); out={'docx':b.getvalue()}
    styles=getSampleStyleSheet(); clean=lambda s: escape(str(s).replace('\u202f',' ').replace('\u2011','-').replace('\u2013','-').replace('\u2014','-'))
    t=Table(filas); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183653')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.3,colors.grey)])); story=[Paragraph(clean(titulo),styles['Title']),Paragraph(fecha,styles['Normal']),Spacer(1,12),t,Image(io.BytesIO(png),width=420,height=168)]
    for h,ls in secciones:
        story.append(Paragraph(clean(h),styles['Heading2']))
        for l in ls: story.extend([Paragraph(clean(l),styles['BodyText']),Spacer(1,5)])
    b=io.BytesIO(); SimpleDocTemplate(b).build(story); out['pdf']=b.getvalue(); b=io.BytesIO()
    with pd.ExcelWriter(b,engine='openpyxl') as w:
        sheets={'Resumen':pd.DataFrame(filas[1:],columns=filas[0]),'Original':original,'Depurados':df,'Calidad':pd.DataFrame({'Antes':antes['nulos_por_columna'],'Después':datos['nulos_por_columna']}).rename_axis('Variable').reset_index(),'Estadísticas':pd.DataFrame(datos['indicadores_numericos']).T.rename_axis('Variable').reset_index(),'Agentes':pd.DataFrame([{'Agente':k,'Modelo':estado['modelos'][k],'Resumen':v['resumen'],'Hallazgos':'\n'.join(v['hallazgos'])} for k,v in estado['resultados'].items()]),'Eventos':pd.DataFrame(estado['eventos'])}
        for name,data in sheets.items():
            data.to_excel(w,index=False,sheet_name=name); ws=w.sheets[name]; ws.freeze_panes='A2'
            for row in ws.iter_rows():
                for cell in row:
                    if cell.data_type=='f': cell.data_type='s'
                    if cell.row==1: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='183653')
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width=min(65,max(14,max(len(str(c.value or '')) for c in col)+2))
    out['xlsx']=b.getvalue(); return out

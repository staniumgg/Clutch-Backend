import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, BaseDocTemplate, PageTemplate, Frame
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import re
import json

class BlackBackgroundDocTemplate(SimpleDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        template = PageTemplate(id='black_bg', frames=[frame], onPage=self.draw_custom_background)
        self.addPageTemplates([template])
    def draw_custom_background(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(HexColor('#253151'))  # Fondo azul personalizado en todas las páginas
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        # Encabezado arriba a la derecha en todas las páginas
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(HexColor('#FDFEFE'))
        jugador = getattr(doc, 'jugador', '')
        user_id = getattr(doc, 'user_id', '')
        fecha_analisis = getattr(doc, 'fecha_analisis', '')
        header_text = f"Jugador: {jugador}   ID: {user_id}   Fecha: {fecha_analisis}"
        canvas.drawRightString(doc.pagesize[0] - 40, doc.pagesize[1] - 30, header_text)
        canvas.restoreState()

def create_analysis_pdf(analysis_text, structured_analysis, username, user_id, fecha_analisis=None, output_path=None):
    """
    Genera un PDF con fondo negro y encabezado en todas las páginas, letras blancas y títulos corregidos.
    """
    # Asegurar que structured_analysis sea dict para métricas y string para regex
    structured_analysis_dict = {}
    structured_analysis_str = ''
    if isinstance(structured_analysis, str):
        try:
            structured_analysis_dict = json.loads(structured_analysis)
        except (json.JSONDecodeError, TypeError):
            structured_analysis_dict = {}
        structured_analysis_str = structured_analysis
    elif isinstance(structured_analysis, dict):
        structured_analysis_dict = structured_analysis
        structured_analysis_str = json.dumps(structured_analysis)
    else:
        structured_analysis_dict = {}
        structured_analysis_str = str(structured_analysis)

    if output_path is None:
        from io import BytesIO
        buffer = BytesIO()
        doc = BlackBackgroundDocTemplate(buffer, pagesize=A4)
    else:
        doc = BlackBackgroundDocTemplate(output_path, pagesize=A4)
    # Guardar datos para encabezado en todas las páginas
    doc.jugador = username
    doc.user_id = user_id
    doc.fecha_analisis = fecha_analisis if fecha_analisis else datetime.now().strftime("%d/%m/%Y - %H:%M")

    styles = getSampleStyleSheet()
    # Estilos adaptados para fondo negro y formato solicitado
    title_style = ParagraphStyle('Title', fontSize=32, alignment=TA_CENTER, textColor=HexColor('#FFFFFF'), spaceAfter=18, fontName='Helvetica-Bold', case='upper')
    subtitle_style = ParagraphStyle('Subtitle', fontSize=17, alignment=TA_LEFT, textColor=HexColor('#FFFFFF'), spaceAfter=10, spaceBefore=18, fontName='Helvetica-Bold', case='upper')
    normal_style = ParagraphStyle('Normal', fontSize=12, alignment=TA_JUSTIFY, leading=16, spaceAfter=8, textColor=HexColor('#FFFFFF'), fontName='Helvetica')
    card_style = ParagraphStyle('Card', fontSize=12, alignment=TA_LEFT, textColor=HexColor('#FFFFFF'), spaceAfter=4, fontName='Helvetica')
    highlight_style = ParagraphStyle('Highlight', fontSize=12, alignment=TA_JUSTIFY, textColor=HexColor('#F7DC6F'), backColor=HexColor('#212121'), fontName='Helvetica-Bold')
    meta_style = ParagraphStyle('Meta', fontSize=9, alignment=TA_CENTER, textColor=HexColor('#BFC9CA'), fontName='Helvetica')
    conclusion_style = ParagraphStyle('Conclusion', fontSize=14, alignment=TA_CENTER, textColor=HexColor('#58D68D'), spaceBefore=16, spaceAfter=10, fontName='Helvetica-Bold')

    story = []

    # 1. Portada visual
    logo_path = os.path.join(os.path.dirname(__file__), 'Logo Esports (1500 x 1440 px).png')
    equipo_logo_path = None
    avatar_path = None
    # Buscar logo de equipo/jugador y avatar si están en el input
    if 'equipo_logo' in structured_analysis_dict:
        equipo_logo_path = structured_analysis_dict['equipo_logo']
    if 'avatar' in structured_analysis_dict:
        avatar_path = structured_analysis_dict['avatar']
    # Portada: Logo Clutch + logo equipo/jugador
    portada_imgs = []
    if os.path.exists(logo_path):
        portada_imgs.append(Image(logo_path, width=120, height=115))
    if equipo_logo_path and os.path.exists(equipo_logo_path):
        portada_imgs.append(Image(equipo_logo_path, width=80, height=80))
    story.append(Table([[portada_imgs]], hAlign='CENTER', style=[('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(Spacer(1, 20))

    # Descripción introductoria
    intro_text = f"""¡Hola, <b>{username}</b>!<br/><br/>
He analizado cómo te comunicaste en la última partida. Este informe va más allá de un simple reporte: está diseñado para entender cómo tu personalidad se refleja en el juego.<br/><br/>
Te mostraré tus fortalezas que aportan al equipo y las áreas donde puedes mejorar para crecer aún más. Con cada partida aprendo más sobre ti y adapto mis recomendaciones para que se ajusten a tu estilo único.<br/><br/>
Además, podrás acceder a métricas clave como las palabras más repetidas, palabras por minuto, volumen durante la partida y mucho más en <a href='http://www.platform.clutch.cl' color='white'>www.platform.clutch.cl</a>.<br/><br/>
Este análisis es una herramienta personalizada creada para ayudarte a sacar lo mejor de ti."""
    story.append(Paragraph(intro_text, normal_style))
    story.append(Spacer(1, 20))

    # 2. Resumen rápido (match stats)
    metricas = structured_analysis_dict.get('metricas', [])
    if metricas:
        tabla_data = [["Métrica clave", "Valor", "Estado"]] + [[m.get('nombre', ''), m.get('valor', ''), m.get('estado', '')] for m in metricas]
        story.append(Table(tabla_data, colWidths=[160, 80, 80], style=[('BACKGROUND', (0,0), (-1,0), HexColor('#34495E')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('TEXTCOLOR', (0,1), (-1,-1), colors.white), ('FONTSIZE', (0,0), (-1,-1), 12), ('GRID', (0,0), (-1,-1), 0.5, colors.white)]))
    else:
        story.append(Paragraph("No se encontraron métricas específicas.", normal_style))
    story.append(Spacer(1, 10))

    # 3. Fortalezas
    story.append(Paragraph("FORTALEZAS", subtitle_style))
    fortalezas = extract_fortalezas(analysis_text)
    for fort in fortalezas:
        story.append(Paragraph(f"✅ {fort}", normal_style))
    story.append(Spacer(1, 10))

    # 4. Áreas de mejora
    story.append(Paragraph("ÁREAS DE MEJORA", subtitle_style))
    mejoras = extract_mejoras(structured_analysis_str)
    for idx, mejora in enumerate(mejoras, 1):
        icono = "❌" if "crítico" in mejora.lower() or idx == 1 else "⚠"
        story.append(Paragraph(f"{icono} {mejora}", normal_style))
    story.append(Spacer(1, 10))

    # 5. Recomendaciones específicas
    story.append(Paragraph("RECOMENDACIONES ESPECÍFICAS", subtitle_style))
    recomendaciones = extract_recomendaciones(structured_analysis_str)
    for rec in recomendaciones:
        story.append(Paragraph(f"💡 {rec}", normal_style))
    story.append(Spacer(1, 10))

    # 6. Observaciones de la IA
    story.append(Paragraph("OBSERVACIONES DE LA IA", subtitle_style))
    obs = clean_text_for_pdf(analysis_text)
    obs = highlight_keywords(obs, ['comunicación', 'callout', 'equipo', 'frustración', 'soluciones', 'coordinación'])
    story.append(Paragraph(obs, highlight_style))
    story.append(Spacer(1, 10))

    # 7. Cierre motivacional
    story.append(Paragraph("CIERRE MOTIVACIONAL", subtitle_style))
    story.append(Paragraph("En el campo, tu voz es tan importante como tu puntería. <br/><b>#Clutch</b>", conclusion_style))
    story.append(Spacer(1, 10))

    # Pie de Página
    story.append(Spacer(1, 20))
    disclaimer = "Este análisis es generado automáticamente por IA y no reemplaza la evaluación profesional."
    story.append(Paragraph(disclaimer, meta_style))
    clutch_url = "https://clutch.cl"
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=40, height=40))
    story.append(Paragraph(f"Más información en <a href='{clutch_url}' color='white'>{clutch_url}</a>", meta_style))

    doc.build(story)
    if output_path is None:
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    else:
        return output_path

def get_general_evaluation(analysis_text):
    """Devuelve una evaluación general simple basada en el texto."""
    text = analysis_text.lower()
    if any(w in text for w in ['excelente', 'muy bien', 'positivo', 'buena comunicación']):
        return "Positivo"
    if any(w in text for w in ['mejorar', 'frustración', 'desacuerdo', 'problema', 'necesita trabajo']):
        return "Necesita trabajo"
    return "Neutro"

def extract_fortalezas(analysis_text):
    """Extrae fortalezas del análisis (simulado, puedes mejorar el algoritmo)."""
    # Simulación: busca frases positivas
    frases = re.findall(r'(?:buena comunicación|callout específico|tono positivo|apoyo|coordinación|soluciones)', analysis_text, re.IGNORECASE)
    if not frases:
        frases = ["Buena disposición para mejorar", "Capacidad de reconocer aportes del equipo", "Interés en la coordinación"]
    return frases[:5]

def extract_mejoras(structured_analysis):
    """Extrae áreas de mejora del análisis estructurado."""
    aspectos = []
    match = re.search(r'"Aspectos a mejorar":\s*(.*?)(?="Cómo mejorarlos"|$)', structured_analysis, re.DOTALL | re.IGNORECASE)
    if match:
        aspectos_text = match.group(1)
        aspectos = re.findall(r'[-•]\s*(.+?)(?=\n[-•]|\n\n|$)', aspectos_text, re.DOTALL)
    if not aspectos:
        aspectos = ["Evitar expresiones de frustración", "Ser más específico en los callouts", "Mantener información clara"]
    return [clean_text_for_pdf(a) for a in aspectos]

def extract_recomendaciones(structured_analysis):
    """Extrae recomendaciones del análisis estructurado."""
    recomendaciones = []
    match = re.search(r'"Cómo mejorarlos":\s*(.*?)(?="Análisis detallado"|$)', structured_analysis, re.DOTALL | re.IGNORECASE)
    if match:
        rec_text = match.group(1)
        recomendaciones = re.findall(r'[-•]\s*(.+?)(?=\n[-•]|\n\n|$)', rec_text, re.DOTALL)
    if not recomendaciones:
        recomendaciones = [
            "Post-partida: anotar 1 jugada positiva y 1 lección aprendida.",
            "Mid-game: mantener un ratio 2:1 de comentarios positivos/negativos.",
            "Pre-match: definir objetivos de comunicación claros."
        ]
    return [clean_text_for_pdf(r) for r in recomendaciones]

def highlight_keywords(text, keywords):
    """Resalta palabras clave en el texto usando HTML tags para PDF."""
    for kw in keywords:
        text = re.sub(rf'({kw})', r'<b>\1</b>', text, flags=re.IGNORECASE)
    return text

def clean_text_for_pdf(text):
    if not text:
        return ""
    text = text.replace('…', '...').replace('—', '-').replace('–', '-')
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'[^\w\s\.,;:!?¿¡()\-"\'áéíóúñüÁÉÍÓÚÑÜ✅⭐]', '', text)
    return text.strip()

def main():
    try:
        # Leer datos desde stdin como bytes y decodificar como UTF-8 para manejar tildes
        input_bytes = sys.stdin.buffer.read()
        input_data = ""
        if input_bytes:
            input_data = input_bytes.decode('utf-8')

        if not input_data.strip() and len(sys.argv) > 1:
            input_data = sys.argv[1]
        
        if not input_data.strip():
            sys.stderr.write("[ERROR] No se recibieron datos de entrada\n")
            return
        
        data = json.loads(input_data)
        analysis_text = data.get('analysis_text', '')
        structured_analysis = data.get('structured_analysis', '')
        username = data.get('username', 'Usuario Desconocido')
        user_id = data.get('user_id', 'ID_Desconocido')
        fecha_analisis = data.get('fecha_analisis', datetime.now().strftime("%d/%m/%Y - %H:%M"))
        
        pdf_bytes = create_analysis_pdf(
            analysis_text=analysis_text,
            structured_analysis=structured_analysis,
            username=username,
            user_id=user_id,
            fecha_analisis=fecha_analisis,
            output_path=None
        )
        sys.stdout.buffer.write(pdf_bytes)
        sys.stderr.write(f"[OK] PDF generado exitosamente para {username} ({len(pdf_bytes)} bytes)\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[ERROR] Error parseando JSON: {e}\n")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Error generando PDF: {e}\n")
        sys.stderr.write(f"[ERROR] Stack trace: {str(e)}\n")

if __name__ == "__main__":
    main()

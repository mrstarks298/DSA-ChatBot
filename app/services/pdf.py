from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import re
from io import BytesIO

def extract_text_from_html(html_content: str) -> list:
    """Extract text content from HTML for PDF generation"""
    if not html_content or not isinstance(html_content, str):
        return []
        
    # Remove HTML tags and extract text
    text_content = []
    
    # Split by message divs
    messages = re.findall(r'<div class="message ([^"]*)-message">(.*?)</div>', html_content, re.DOTALL)
    
    for msg_type, content in messages:
        # Extract text from message content
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            text_content.append((msg_type, text))
    
    return text_content

def generate_pdf_from_html(html_content: str) -> bytes:
    """Generate PDF from HTML content using ReportLab"""
    if not html_content or not isinstance(html_content, str):
        raise ValueError("Invalid HTML content provided")
        
    if not html_content.strip():
        raise ValueError("Empty HTML content provided")
        
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=HexColor('#1B7EFE'),
        alignment=1  # Center
    )
    
    user_style = ParagraphStyle(
        'UserMessage',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20,
        textColor=HexColor('#1F2937'),
        backColor=HexColor('#E5E7EB')
    )
    
    bot_style = ParagraphStyle(
        'BotMessage',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20,
        textColor=HexColor('#1F2937')
    )
    
    # Build PDF content
    story = []
    
    # Add title
    story.append(Paragraph("DSA Mentor Chat Export", title_style))
    story.append(Spacer(1, 20))
    
    # Extract and add messages
    messages = extract_text_from_html(html_content)
    
    for msg_type, text in messages:
        if msg_type == 'user':
            story.append(Paragraph(f"<b>You:</b> {text}", user_style))
        else:
            story.append(Paragraph(f"<b>DSA Mentor:</b> {text}", bot_style))
        story.append(Spacer(1, 10))
    
    # Build PDF
    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import re
import time
from io import BytesIO

def extract_text_from_html(html_content: str) -> list:
    """Extract text content from HTML for PDF generation with better parsing"""
    if not html_content or not isinstance(html_content, str):
        return []
        
    text_content = []
    
    # Multiple patterns to catch different HTML structures
    patterns = [
        # Pattern 1: Standard message divs
        r'<div class="message ([^"]*)-message"[^>]*>(.*?)</div>',
        # Pattern 2: Message content divs
        r'<div class="message-content"[^>]*>(.*?)</div>',
        # Pattern 3: Any div with message class
        r'<div[^>]*class="[^"]*message[^"]*"[^>]*>(.*?)</div>',
        # Pattern 4: Paragraph tags
        r'<p[^>]*>(.*?)</p>',
        # Pattern 5: Any text content
        r'>([^<]+)<'
    ]
    
    # Try each pattern
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    msg_type, content = match
                else:
                    content = match
                    # Try to determine message type from context
                    msg_type = 'assistant'  # Default to assistant
                
                # Clean the text
                text = re.sub(r'<[^>]+>', '', content)
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Skip empty or very short content
                if text and len(text) > 3:
                    text_content.append((msg_type, text))
            
            # If we found content with this pattern, break
            if text_content:
                break
    
    # If no patterns worked, try to extract any meaningful text
    if not text_content:
        # Remove all HTML tags and get clean text
        clean_text = re.sub(r'<[^>]+>', ' ', html_content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if clean_text and len(clean_text) > 10:
            # Split by common separators and create messages
            parts = re.split(r'[.!?]\s+', clean_text)
            for i, part in enumerate(parts[:10]):  # Limit to 10 parts
                if part.strip() and len(part.strip()) > 5:
                    text_content.append(('assistant', part.strip()))
    
    return text_content

def generate_pdf_from_html(html_content: str) -> bytes:
    """Generate beautiful PDF from HTML content using ReportLab"""
    if not html_content or not isinstance(html_content, str):
        raise ValueError("Invalid HTML content provided")
        
    if not html_content.strip():
        raise ValueError("Empty HTML content provided")
        
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create beautiful custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=HexColor('#1B7EFE'),
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=HexColor('#6B7280'),
        alignment=1,  # Center
        fontName='Helvetica'
    )
    
    user_style = ParagraphStyle(
        'UserMessage',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=15,
        leftIndent=30,
        rightIndent=30,
        textColor=HexColor('#1F2937'),
        backColor=HexColor('#F3F4F6'),
        borderWidth=1,
        borderColor=HexColor('#E5E7EB'),
        borderPadding=10,
        borderRadius=8,
        fontName='Helvetica'
    )
    
    bot_style = ParagraphStyle(
        'BotMessage',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=15,
        leftIndent=30,
        rightIndent=30,
        textColor=HexColor('#1F2937'),
        backColor=HexColor('#FFFFFF'),
        borderWidth=1,
        borderColor=HexColor('#D1D5DB'),
        borderPadding=10,
        borderRadius=8,
        fontName='Helvetica'
    )
    
    timestamp_style = ParagraphStyle(
        'Timestamp',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=5,
        textColor=HexColor('#9CA3AF'),
        alignment=2,  # Right
        fontName='Helvetica-Oblique'
    )
    
    # Build PDF content
    story = []
    
    # Add beautiful header
    story.append(Paragraph("🚀 DSA Mentor Chat Export", title_style))
    story.append(Paragraph(f"Generated on {time.strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
    story.append(Spacer(1, 30))
    
    # Extract and add messages with better parsing
    messages = extract_text_from_html(html_content)
    
    if not messages:
        # Fallback: try to extract any text content
        fallback_text = re.sub(r'<[^>]+>', '', html_content)
        fallback_text = re.sub(r'\s+', ' ', fallback_text).strip()
        if fallback_text:
            story.append(Paragraph("Chat Content:", bot_style))
            story.append(Paragraph(fallback_text, bot_style))
    
    for i, (msg_type, text) in enumerate(messages):
        # Add message number
        story.append(Paragraph(f"<b>Message {i+1}</b>", timestamp_style))
        
        if msg_type == 'user':
            story.append(Paragraph(f"<b>👤 You:</b> {text}", user_style))
        else:
            story.append(Paragraph(f"<b>🤖 DSA Mentor:</b> {text}", bot_style))
        
        story.append(Spacer(1, 10))
    
    # Add footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("--- End of Chat Export ---", timestamp_style))
    
    # Build PDF
    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content

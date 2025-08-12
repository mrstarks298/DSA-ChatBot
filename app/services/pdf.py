from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

PDF_CSS = """
body { font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: #1F2937; }
.concept-title { font-size: 22px; font-weight: 700; color: #1B7EFE; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 3px solid #E5E7EB; }
.concept-explanation { font-size: 15px; line-height: 1.8; color: #4B5563; margin-bottom: 20px; }
"""

def generate_pdf_from_html(html_content: str) -> bytes:
    font_config = FontConfiguration()
    html = HTML(string=f"<!doctype html><html><body>{html_content}</body></html>")
    css = CSS(string=PDF_CSS, font_config=font_config)
    return html.write_pdf(stylesheets=[css], font_config=font_config)

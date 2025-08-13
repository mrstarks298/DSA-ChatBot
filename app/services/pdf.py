from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import re

PDF_CSS = """
body {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 14px;
    color: #1F2937;
}

.concept-title {
    font-size: 22px;
    font-weight: 700;
    color: #1B7EFE;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 3px solid #E5E7EB;
}

.concept-explanation {
    font-size: 15px;
    line-height: 1.8;
    color: #4B5563;
    margin-bottom: 20px;
}

.video-card {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}

.video-card:hover {
    background-color: #F9FAFB;
}
"""

def process_html_for_pdf(html_content: str) -> str:
    # Convert video cards with onclick to clickable links
    # Matches: <div class="video-card" onclick="openVideoModal('URL', 'TITLE')" ...>INNER</div>
    pattern = re.compile(
        r'<div\s+class="video-card"[^>]*onclick="openVideoModal\s*\'([^\']+)\'[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL
    )
    
    def repl(m):
        url = m.group(1)
        inner = m.group(2)
        return f'<a href="{url}" target="_blank" style="display:block;text-decoration:none;color:inherit;">{inner}</a>'
    
    return pattern.sub(repl, html_content)

def generate_pdf_from_html(html_content: str) -> bytes:
    processed_html = process_html_for_pdf(html_content)
    font_config = FontConfiguration()
    html = HTML(string=f"<!doctype html><html><body>{processed_html}</body></html>")
    css = CSS(string=PDF_CSS, font_config=font_config)
    return html.write_pdf(stylesheets=[css], font_config=font_config)

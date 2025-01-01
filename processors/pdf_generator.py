# processors/pdf_generator.py
import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import TIMES_NEW_ROMAN_FONT_PATH, PDF_DIR
from utils.logger import log, log_exception
from utils.errors import FileProcessingError

def process_and_save_articles(input_json_path, output_pdf_path):
    """Generates a PDF from a JSON file containing articles."""
    log(f"Starting PDF Generation from {input_json_path} and saving to {output_pdf_path}")
    try:
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)

        # PDF setup
        pdfmetrics.registerFont(TTFont("Times-Roman", TIMES_NEW_ROMAN_FONT_PATH))
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        story = []

        # Title Page
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Times-Roman",
            fontSize=28,
            alignment=1,  # Center alignment
            spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            fontName="Times-Italic",
            fontSize=16,
            alignment=1,  # Center alignment
            spaceAfter=40
        )
        story.append(Spacer(1, 2 * inch))  # Add vertical spacing
        story.append(Paragraph("UK Crime Chronicles", title_style))
        story.append(Paragraph("A Deep Dive into Recent Headlines and Stories", subtitle_style))
        story.append(PageBreak())  # Move to the next page

        # Styles for content
        headline_style = ParagraphStyle(
            name="HeadlineStyle",
            fontName="Times-Bold",
            fontSize=16,
            alignment=1,  # Center alignment
            leading=18,
            spaceAfter=12
        )
        content_style = ParagraphStyle(
            name="ContentStyle",
            fontName="Times-Roman",
            fontSize=12,
            alignment=4,  # Justify alignment
            leading=14,
            spaceAfter=20
        )

        for article in articles:
            headline = article.get("headline", "")
            content = article.get("content", "")

            # Skip articles where the headline is missing or "N/A"
            if not headline or headline == "N/A":
                continue

            # Add headline and content
            story.append(Paragraph(headline, headline_style))
            story.append(Paragraph(content, content_style))
            story.append(Spacer(1, 0.5 * inch))  # Add spacing between articles

        def add_footer(canvas, doc):
            """Adds a footer with the page number."""
            canvas.saveState()
            canvas.setFont("Times-Roman", 10)
            page_num = doc.page
            text = f"Page {page_num}"
            canvas.drawCentredString(letter[0] / 2.0, 0.5 * inch, text)
            canvas.restoreState()

        doc.build(story, onLaterPages=add_footer)
        log(f"PDF generated successfully at {output_pdf_path}")

    except Exception as e:
        log_exception(e, f"Error during PDF generation: {e}")
        raise FileProcessingError(f"Error during PDF generation: {e}")
import os
import re
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import blue, black
from datetime import datetime
from config import TIMES_NEW_ROMAN_FONT_PATH, PDF_DIR
from utils.logger import log, log_exception
from utils.errors import FileProcessingError

# Register the Times New Roman font
pdfmetrics.registerFont(TTFont('Times-Roman', TIMES_NEW_ROMAN_FONT_PATH))

def process_and_save_articles(input_json_path, output_pdf_path):
    """Reads JSON, rewrites articles with Gemini, saves to a PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} to {output_pdf_path}")
    try:
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)

        # PDF setup
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        page_width, page_height = letter
        margin = inch
        story = []

        # Title Page Styling
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Times-Bold",
            fontSize=36,
            alignment=TA_CENTER,
            textColor=black,
            spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            fontName="Times-Italic",
            fontSize=18,
            alignment=TA_CENTER,
            textColor=blue,
            spaceAfter=40
        )
        date_style = ParagraphStyle(
            name="DateStyle",
            fontName="Times-Roman",
            fontSize=14,
            alignment=TA_CENTER,
            textColor=black,
            spaceAfter=30
        )

        # Title page content
        title = Paragraph("UK Crime Chronicles 2025", title_style)
        subtitle = Paragraph("A Deep Dive into Recent Headlines and Stories", subtitle_style)
        current_date = Paragraph(datetime.now().strftime("%B %d, %Y"), date_style)

        # Add title page elements
        story.append(Spacer(1, 2 * inch))  # Add space before title
        story.append(title)
        story.append(subtitle)
        story.append(current_date)
        story.append(Spacer(1, 4 * inch))  # Add space after the date
        story.append(PageBreak())

        # Content Styling
        headline_style = ParagraphStyle(
            name="HeadlineStyle",
            fontName="Times-Bold",
            fontSize=16,
            alignment=TA_JUSTIFY,
            leading=18,
            spaceAfter=12
        )
        content_style = ParagraphStyle(
            name="ContentStyle",
            fontName="Times-Roman",
            fontSize=12,
            alignment=TA_JUSTIFY,
            leading=14,
            spaceAfter=20
        )
        link_style = ParagraphStyle(
            name="LinkStyle",
            fontName="Times-Roman",
            fontSize=10,
            alignment=TA_JUSTIFY,
            leading=12,
            spaceAfter=12,
            textColor=blue,
            underline=True,
        )

        for article in articles:
            headline = article.get("headline", "")
            content = article.get("content", "")
            source = article.get("source", "original")
            url = article.get("url", "")

            if not headline or headline == "N/A":
                continue

            # Add headline
            story.append(Paragraph(headline, headline_style))

            # Add content paragraphs
            paragraphs = content.split('\n\n')  # Split content into paragraphs
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    story.append(Paragraph(paragraph, content_style))

            # Add source link
            if source != "original" and url:
                url = url.replace("http://http", "http")  # Fix extra http issue
                source_link = f"<a href='{url}'>Source</a>"
                story.append(Paragraph(source_link, link_style))
            story.append(Spacer(1, 0.5 * inch))

        # Build PDF with header and footer
        def add_header_and_footer(canvas, doc, page_num):
            """Adds a footer with the page number."""
            canvas.saveState()
            canvas.setFont("Times-Roman", 10)
            canvas.drawCentredString(doc.width / 2, 0.5 * inch, f"Page {page_num}")
            canvas.restoreState()

        doc.build(
            story,
            onFirstPage=lambda canvas, doc: add_header_and_footer(canvas, doc, 1),
            onLaterPages=lambda canvas, doc: add_header_and_footer(canvas, doc, doc.page)
        )

        log(f"PDF saved to {output_pdf_path}")
        log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
        log_exception(e, f"Error during PDF generation: {e}")
        raise FileProcessingError(f"Error during PDF generation: {e}")
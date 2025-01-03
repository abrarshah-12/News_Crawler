import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import TIMES_NEW_ROMAN_FONT_PATH, PDF_DIR
from utils.logger import log, log_exception
from utils.errors import FileProcessingError


def process_and_save_articles(input_json_path, output_pdf_path):
    """Reads JSON, rewrites articles with Gemini, saves to a PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} to {output_pdf_path}")
    try:
        # Load articles from JSON file
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)

        # Register the font
        pdfmetrics.registerFont(TTFont('Times-Roman', TIMES_NEW_ROMAN_FONT_PATH))

        # Setup the PDF document
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
        story = []

        # Styles for the content
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Times-Roman",
            fontSize=28,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            name="SubtitleStyle",
            fontName="Times-Italic",
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=40
        )
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

        # Title Page
        title = Paragraph("UK Crime Chronicles", title_style)
        subtitle = Paragraph("A Deep Dive into Recent Headlines and Stories", subtitle_style)
        story.append(title)
        story.append(subtitle)
        story.append(PageBreak())

        # Add articles
        for article in articles:
            headline = article.get("headline", "")
            content = article.get("content", "")

            # Skip articles with missing or invalid headlines
            if not headline or headline == "N/A":
                continue

            # Add headline and content
            story.append(Paragraph(headline, headline_style))
            paragraphs = content.split('\n')
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    story.append(Paragraph(paragraph, content_style))

            story.append(Spacer(1, 0.5 * inch))  # Space between articles

        # Function to add page numbers at the bottom center
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont("Times-Roman", 10)
            page_number_text = f"Page {doc.page}"
            canvas.drawCentredString(letter[0] / 2, 0.5 * inch, page_number_text)
            canvas.restoreState()

        # Build the PDF with page numbering
        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)

        log(f"PDF saved to {output_pdf_path}")
        log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
        log_exception(e, f"Error during PDF generation: {e}")
        raise FileProcessingError(f"Error during PDF generation: {e}")

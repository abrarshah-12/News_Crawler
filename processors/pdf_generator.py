# processors/pdf_generator.py
import os
import re
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import blue, black
from reportlab.lib.utils import simpleSplit
from reportlab.lib.styles import StyleSheet1
from reportlab.lib.colors import black
from config import TIMES_NEW_ROMAN_FONT_PATH, PDF_DIR
from utils.logger import log, log_exception
from utils.errors import FileProcessingError
import glob
import datetime

def process_and_save_articles(input_json_path, output_pdf_path):
    """Reads JSON, rewrites articles with Gemini, saves to a PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} to {output_pdf_path}")
    try:
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)

        # PDF setup
        pdfmetrics.registerFont(TTFont('Times-Roman', TIMES_NEW_ROMAN_FONT_PATH))
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
        page_width, page_height = letter
        margin = inch
        story = []

        def add_header_and_footer(canvas, doc, page_num):
            """Adds a footer with the page number."""
            canvas.saveState()
            canvas.setFont("Times-Roman", 10)
            canvas.drawCentredString(doc.width / 2, 0.5 * inch, f"{page_num}")
            canvas.restoreState()

        def on_page(canvas, doc, page_num):
            add_header_and_footer(canvas, doc, page_num)
        
        # Title page
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="TitleStyle",
            fontName="Times-Bold",
            fontSize=28,
            alignment=TA_CENTER,
             spaceAfter = 10
        )
        subtitle_style = ParagraphStyle(
            name="SubTitleStyle",
            fontName="Times-Italic",
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter = 20
        )
        title = Paragraph("UK Crime Chronicles 2025", title_style)
        subtitle = Paragraph("A Deep Dive into Recent Headlines and Stories", subtitle_style)
        story.append(title)
        story.append(subtitle)
        story.append(Spacer(1, 2 * inch)) # Add space after subtitle
        story.append(PageBreak())

        # Styles for content
        styles = getSampleStyleSheet()
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
             leading = 12,
             spaceAfter=12,
            textColor=blue,
            underline = True,

        )
        normal_style = ParagraphStyle(
            name="normal",
            fontName = "Times-Roman",
            fontSize = 10,
            textColor=black
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

              # Split the content into paragraphs by looking for newlines
              paragraphs = content.split('\n\n')
              for paragraph in paragraphs:
                  paragraph = paragraph.strip()
                  if paragraph:
                      content_para = Paragraph(paragraph, content_style)
                      story.append(content_para)

              # Add the link to the source
              if source != "original" and url:
                  source_link = f"<a href='{url}'>Source</a>"
                  source_link_para = Paragraph(f"{source_link}", link_style)
                  story.append(source_link_para)
              story.append(Spacer(1, 0.5 * inch))
        
        # Save the new PDF
        doc.build(story, onFirstPage=lambda canvas, doc: on_page(canvas, doc, 1),
                onLaterPages=lambda canvas, doc: on_page(canvas, doc, doc.page))

        log(f"PDF saved to {output_pdf_path}")
        
    
        all_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")), key=os.path.getctime, reverse=True)
         # Maintain only 5 most recent files
        if len(all_files) > 5:
            for file_to_remove in all_files[5:]:
                try:
                   os.remove(file_to_remove)
                   log(f"Removed old pdf report {file_to_remove}")
                except Exception as e:
                    log_exception(e, f"Error deleting file {file_to_remove}")

        log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
        log_exception(e, f"Error during PDF generation: {e}")
        raise FileProcessingError(f"Error during PDF generation: {e}")
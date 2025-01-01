# processors/pdf_generator.py
import os
import re
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.utils import simpleSplit

from utils.logger import log
from config import JSON_DIR, PDF_DIR, TIMES_NEW_ROMAN_FONT_PATH
from utils.errors import FileProcessingError

def process_and_save_articles(input_json_path, output_pdf_path):
    """Reads JSON, rewrites articles with Gemini, saves to a PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} to {output_pdf_path}")
    try:
      with open(input_json_path, "r", encoding="utf-8") as json_file:
          articles = json.load(json_file)
      
      # PDF Generation
      log(f"Starting generation of PDF file")
      c = canvas.Canvas(output_pdf_path, pagesize=letter)
      pdfmetrics.registerFont(TTFont('Times-Roman', TIMES_NEW_ROMAN_FONT_PATH))
      styles = getSampleStyleSheet()

      h_style = styles['h1']
      h_style.fontName = 'Times-Roman'
      h_style.fontSize = 16
      h_style.alignment = TA_CENTER
      
      c_style = styles['Normal']
      c_style.fontName = 'Times-Roman'
      c_style.fontSize = 12
      c_style.alignment = TA_JUSTIFY

      title_style = styles['h1']
      title_style.fontName = 'Times-Roman'
      title_style.fontSize = 20
      title_style.alignment = TA_CENTER

      def add_header_and_footer(c, page_num, total_pages):
        c.saveState()
        c.setFont('Times-Roman', 10)
        c.drawCentredString(letter[0]/2, .5*inch, f'Page: {page_num}/{total_pages}')
        c.restoreState()
      
      total_pages = len(articles)
      y_position = 750
      
      pdf_title = "Shocking UK Crime Stories"
      title_para = Paragraph(pdf_title, title_style)
      title_para.wrapOn(c, letter[0] - 2*inch, 10)
      title_height = title_para.height
      title_para.drawOn(c, inch, y_position)
      y_position -= title_height + 0.5 * inch

      for i, article in enumerate(articles):
          if article.get("source") == "gemini":
            headline = article.get("headline", "N/A")
            content = article.get("content", "")

            h_para = Paragraph(headline, h_style)
            h_para.wrapOn(c, letter[0] - 2*inch, 10)
            h_height = h_para.height

            if y_position - h_height < inch:
                add_header_and_footer(c, i+1, total_pages)
                c.showPage()
                y_position = 750

            h_para.drawOn(c, inch, y_position)
            y_position -= h_height + 0.2*inch

            # Split the content into manageable lines
            available_width = letter[0] - 2 * inch
            lines = simpleSplit(content, c_style.fontName, c_style.fontSize, available_width)
            
            for line in lines:
                c_para = Paragraph(line, c_style)
                c_para.wrapOn(c, available_width, letter[1])
                c_height = c_para.height
                
                if y_position - c_height < inch:
                  add_header_and_footer(c, i+1, total_pages)
                  c.showPage()
                  y_position = 750

                c_para.drawOn(c, inch, y_position)
                y_position -= c_height
           
            y_position -= 0.5 * inch
      add_header_and_footer(c, total_pages, total_pages)
      c.save()

      log(f"PDF saved to {output_pdf_path}")
      log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
      raise FileProcessingError(f"Error generating PDF file: {e}")
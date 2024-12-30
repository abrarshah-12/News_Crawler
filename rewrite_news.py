import os
import re
import csv
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from Persona import PERSONA
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = 'gemini-pro'
model = genai.GenerativeModel(MODEL_NAME)


# Directory structure
OUTPUT_DIR = "output"
JSON_DIR = os.path.join(OUTPUT_DIR, "json")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")

# Ensure directories exist
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Logging
log_entries = []

def log(message):
    """Logs a message to the console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    log_entries.append(log_entry)

def save_logs():
    """Saves logs to a log file."""
    with open(LOG_FILE, "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(log_entries))

# Sanitize filenames
def sanitize_filename(name):
    """Sanitizes a string to use as a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# Rewrite articles using Gemini, chunking requests
def rewrite_articles_with_gemini(text, initial_delay = 1, max_delay = 16):
  rewritten_text = ""
  delay = initial_delay
  retries = 0
  start_time = time.time()
  while True:
      try:
          response = model.generate_content(
              [PERSONA, text]
          )
          if response.text:
              rewritten_text = response.text
              end_time = time.time()
              time_taken = end_time - start_time
              log(f"Gemini API returned text. Time taken: {time_taken:.2f}s Retries: {retries}")
              break # Exit the retry loop if successful
          else:
            log(f"Gemini API returned no text. Retries: {retries}")
            break
      except Exception as e:
          log(f"Error with Gemini API: {e}. Retries: {retries}")
          if '429' in str(e):
              log(f"Rate limit hit. Retrying in {delay} seconds...")
              time.sleep(delay)
              delay = min(delay * 2, max_delay) # exponential backoff
              retries += 1
          else:
              log(f"Unexpected Gemini API error, not retrying. {e}")
              break
  return rewritten_text.strip()

def process_and_save_rewritten_articles(input_json_path, output_json_path, output_pdf_path):
    """Reads the JSON file, rewrites articles, and saves as a new JSON and PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} and save as json to {output_json_path} and as PDF to {output_pdf_path}")
    with open(input_json_path, "r", encoding="utf-8") as json_file:
        articles = json.load(json_file)

    rewritten_articles = []
    for article in articles:
        heading = article.get("heading", "")
        content = article.get("content", "")
        if heading and content:
            rewritten_heading = rewrite_articles_with_gemini(heading)
            rewritten_content = rewrite_articles_with_gemini(content)
            if rewritten_content:
              rewritten_articles.append({"heading": rewritten_heading, "content": rewritten_content})
              log(f"Rewrote article: {heading}")
            else:
               log(f"Could not rewrite content of the article due to Gemini API issues: {heading}, saving original content.")
               rewritten_articles.append({"heading": heading, "content": content})
        else:
             log(f"Skipping article due to missing heading or content. Article: {article}")

    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(rewritten_articles, json_file, indent=4)
        log(f"Saved rewritten articles to {output_json_path}")


    # Generate PDF
    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    pdfmetrics.registerFont(TTFont('Times-Roman', 'times.ttf'))
    styles = getSampleStyleSheet()
    h_style = styles['h1']
    h_style.fontName = 'Times-Roman'
    h_style.fontSize = 14
    h_style.alignment = TA_CENTER
    c_style = styles['Normal']
    c_style.fontName = 'Times-Roman'
    c_style.fontSize = 12
    c_style.alignment = TA_JUSTIFY
    log(f"Starting generation of PDF file")

    def add_header_and_footer(c, page_num, total_pages):
        c.saveState()
        c.setFont('Times-Roman', 10)
        c.drawCentredString(letter[0]/2, .5*inch, f'Page: {page_num}/{total_pages}')
        c.restoreState()
    
    total_pages = len(rewritten_articles) # Calculate total number of pages based on number of articles
    y_position = 750

    for i, article in enumerate(rewritten_articles):
      heading = article["heading"]
      content = article["content"]

      h_para = Paragraph(heading, h_style)
      h_para.wrapOn(c, letter[0] - 2*inch, 10)
      h_height = h_para.height

      if y_position - h_height < inch:
          add_header_and_footer(c, i+1, total_pages)
          c.showPage()
          y_position = 750

      h_para.drawOn(c, inch, y_position)
      y_position -= h_height

      c_para = Paragraph(content, c_style)
      c_para.wrapOn(c, letter[0] - 2*inch, letter[1] ) # Wrap text to fit page
      c_height = c_para.height

      if y_position - c_height < inch:
          add_header_and_footer(c, i+1, total_pages)
          c.showPage()
          y_position = 750

      c_para.drawOn(c, inch, y_position)

      y_position -= c_height + 0.5*inch
    
    add_header_and_footer(c, total_pages, total_pages)
    c.save()

    log(f"PDF saved to {output_pdf_path}")
    log(f"Finished generating PDF file")
    log(f"Finished processing all articles from {input_json_path}")


# Main function
def main():
    # Get file paths
    input_json_path = os.path.join(JSON_DIR, "cleaned_articles.json")
    output_json_path = os.path.join(JSON_DIR, "rewritten_articles.json")
    output_pdf_path = os.path.join(PDF_DIR, "rewritten_articles.pdf")

    log(f"Starting main function with input path {input_json_path}")
    process_and_save_rewritten_articles(input_json_path, output_json_path, output_pdf_path)

    # Save logs
    save_logs()
    log(f"Finished main function")

if __name__ == "__main__":
    main()
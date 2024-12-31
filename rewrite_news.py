import os
import re
import csv
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.utils import simpleSplit
import random

# Load environment variables
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = 'gemini-pro'
MODEL = genai.GenerativeModel(MODEL_NAME)

# Directory structure
OUTPUT_DIR = "output"
CONTENT_MD_DIR = os.path.join(OUTPUT_DIR, "content_md_files")
JSON_DIR = os.path.join(OUTPUT_DIR, "json")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")
TIMES_NEW_ROMAN_FONT_PATH = 'fonts\\timr45w.ttf'

# Ensure directories exist
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Logging
LOG_ENTRIES = []

def log(message):
    """Logs a message to the console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    LOG_ENTRIES.append(log_entry)

def save_logs():
    """Saves logs to a log file."""
    with open(LOG_FILE, "w", encoding="utf-8") as log_file:
        log_file.write("\n".join(LOG_ENTRIES))

# Sanitize filenames
def sanitize_filename(name):
    """Sanitizes a string to use as a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

PERSONA = """1. Sensationalist Tone
Style: Articles often use eye-catching headlines, sometimes exaggerated, to grab attention.
Purpose: Maximise clicks and engagement by appealing to emotions like curiosity, outrage, or excitement.

2. Audience-Centric Approach
Demographic: Primarily middle-class readers with conservative or right-leaning values.
Focus: Topics that resonate with their audience, including immigration, crime, celebrities, health, and royal family news.

3. Human-Interest Angle
Style: Personal stories, anecdotes, and "real-life" drama are often central to articles.
Purpose: Engage readers by making the news relatable and emotionally compelling.

4. Moral Perspective
Style: Articles often include implicit or explicit judgments, aligning with traditional British values or conservative viewpoints.
Purpose: Reinforce the readers' worldview and create a sense of shared values.

5. Visual & Formatting Emphasis
Style: Heavy use of photos, videos, and bullet points to break down content for easy scanning.
Purpose: Cater to readers who prefer quick, visually engaging content.

6. Provocative Framing
Style: Articles often pose questions or create controversy, e.g., "Is this the end of [X]?" or "Outrage as [Y] happens."
Purpose: Encourage debate and social media sharing.

7. Quick Turnaround
Style: Prioritise speed in covering breaking news, even if it means occasional corrections later.
Purpose: Stay competitive in the fast-paced media landscape.

8. Celebrity and Lifestyle Focus
Style: Blend hard news with soft topics like fashion, relationships, and pop culture.
Purpose: Broaden appeal and maintain interest across a diverse readership.

9. Clickbait Techniques
Style: Use of phrases like "You’ll never guess what happened next" or "What [X] said will shock you."
Purpose: Drive higher engagement and encourage readers to click through.

10. Critical or Alarmist Headlines
Style: Highlight potential risks, scandals, or failures, often with a negative slant.
Purpose: Appeal to readers’ fears and sense of urgency.

The Daily Mail editor persona operates with the primary goal of engaging a broad yet specific audience by combining sensationalism, relatability, and visual storytelling with a strong editorial slant."""


# Rewrite articles using Gemini, chunking requests
def rewrite_articles_with_gemini(text, initial_delay=1, max_delay=16):
    """Rewrites text using Gemini with retry logic and throttling."""
    rewritten_text = ""
    delay = initial_delay
    retries = 0
    start_time = time.time()

    while True:
        try:
            prompt = f"""{PERSONA}
            Given this news article content:
            {text}
            Analyze the article content to identify the main news. Then rewrite the main news into a catchy headline and a compelling, engaging article in a Daily Mail style. Remove any links, images, and markdown-like formatting. Do not use bullet points in the rewritten article, just a coherent and attractive narrative.
            """
            response = MODEL.generate_content(prompt)
            if response.text:
                rewritten_text = response.text.strip()
                end_time = time.time()
                time_taken = end_time - start_time
                log(f"Gemini API returned text. Time taken: {time_taken:.2f}s. Retries: {retries}")
                break  # Exit the retry loop if successful
            else:
                log(f"Gemini API returned no text. Retries: {retries}")
                break
        except Exception as e:
            log(f"Error with Gemini API: {e}. Retries: {retries}")
            if '429' in str(e):
                log(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)  # exponential backoff
                retries += 1
            elif "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, but none were returned." not in str(e):
                 log(f"Unexpected Gemini API error, not retrying. {e}")
                 break
            elif "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, but none were returned."  in str(e) :
                log(f"Gemini API blocked content: {e}. Saving original content.")
                return "BLOCKED_CONTENT"
        finally:
            # Add random delay to prevent rate limiting
            time.sleep(random.uniform(0.5, 1.5))
    return rewritten_text


def process_and_save_rewritten_articles(content_md_dir, output_json_path, output_pdf_path):
    """Reads MD files, rewrites articles with Gemini, saves to JSON and PDF."""
    log(f"Starting to process and save rewritten articles from {content_md_dir}")

    rewritten_articles = []
    
    for filename in os.listdir(content_md_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(content_md_dir, filename)
            with open(filepath, "r", encoding="utf-8") as md_file:
                content = md_file.read()
                # Split the file into articles based on the presence of a heading
                articles = re.split(r'(?=\n#\s)', content)
                
                for article_content in articles:
                  article_content = article_content.strip()
                  if article_content:
                      # Extract heading from content
                      heading_match = re.search(r'#\s*(.+)', article_content)
                      heading = heading_match.group(1).strip() if heading_match else "N/A"
                      
                      #Remove the heading
                      article_content = re.sub(r'#\s*(.+)', '', article_content, 1).strip()
                      if heading and article_content:
                         rewritten_content = rewrite_articles_with_gemini(article_content)
                         if rewritten_content and rewritten_content != "BLOCKED_CONTENT":
                           rewritten_articles.append({"heading": rewritten_content.split("\n", 1)[0] if rewritten_content.count("\n") > 0 else heading , "content": rewritten_content.split("\n",1)[1]  if rewritten_content.count("\n") > 0 else rewritten_content})
                           log(f"Rewrote article: {heading}")
                         else:
                            log(f"Could not rewrite content of the article due to Gemini API issues or blocked content: {heading}, saving original content.")
                            rewritten_articles.append({"heading": heading, "content": article_content})
                      else:
                            log(f"Skipping row due to missing URL or Heading: {article_content}")

    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(rewritten_articles, json_file, indent=4)
        log(f"Saved rewritten articles to {output_json_path}")

    # PDF Generation
    log(f"Starting generation of PDF file")
    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    pdfmetrics.registerFont(TTFont('Times-Roman', TIMES_NEW_ROMAN_FONT_PATH))
    styles = getSampleStyleSheet()

    h_style = styles['h1']
    h_style.fontName = 'Times-Roman'
    h_style.fontSize = 16  # Increased Heading Font size
    h_style.alignment = TA_CENTER
    
    c_style = styles['Normal']
    c_style.fontName = 'Times-Roman'
    c_style.fontSize = 12
    c_style.alignment = TA_JUSTIFY

    def add_header_and_footer(c, page_num, total_pages):
        c.saveState()
        c.setFont('Times-Roman', 10)
        c.drawCentredString(letter[0]/2, .5*inch, f'Page: {page_num}/{total_pages}')
        c.restoreState()

    total_pages = len(rewritten_articles)
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
    log(f"Finished processing all articles from {content_md_dir}")

# Main function
def main():
    """Main function to orchestrate the scraping, extraction, and saving."""
    # Get file paths
    input_md_dir = os.path.join(OUTPUT_DIR, "content_md_files")
    output_json_path = os.path.join(JSON_DIR, "rewritten_articles.json")
    output_pdf_path = os.path.join(PDF_DIR, "rewritten_articles.pdf")

    log(f"Starting main function with input path {input_md_dir}")
    process_and_save_rewritten_articles(input_md_dir, output_json_path, output_pdf_path)

    # Save logs
    save_logs()
    log(f"Finished main function")

if __name__ == "__main__":
    main()
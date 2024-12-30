import os
import re
import csv
import json
import time
from datetime import datetime
from fpdf import FPDF
from dotenv import load_dotenv
import google.generativeai as genai
from Persona import PERSONA

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
def rewrite_articles_with_gemini(text, max_chunk_size=5000, overlap=500, initial_delay = 1, max_delay = 16):
  rewritten_text = ""
  text_len = len(text)
  start = 0
  delay = initial_delay

  while start < text_len:
    end = min(start + max_chunk_size, text_len)
    chunk = text[start:end]

    while True:
        try:
            response = model.generate_content(
                [PERSONA, chunk]
            )
            if response.text:
                rewritten_text += response.text + " "
                break # Exit the retry loop if successful
            else:
               log(f"Gemini API returned no text for chunk starting at {start}")
               break

        except Exception as e:
            log(f"Error with Gemini API for chunk at {start}: {e}")
            if '429' in str(e):
                log(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay) # exponential backoff
            else:
                log(f"Unexpected Gemini API error, not retrying. {e}")
                break

    start = end - overlap  # Move start with overlap
    delay = initial_delay # reset the delay for the next chunk

  return rewritten_text.strip()



def process_and_save_rewritten_articles(input_json_path, output_json_path, output_pdf_path):
    """Reads the JSON file, rewrites articles, and saves as a new JSON and PDF file."""
    log(f"Starting to process and save rewritten articles from {input_json_path} and save as json to {output_json_path} and as PDF to {output_pdf_path}")
    with open(input_json_path, "r", encoding="utf-8") as json_file:
        articles = json.load(json_file)

    rewritten_articles = []
    for article in articles:
        heading = article.get("Heading", "")
        content = article.get("URL", "")
        if heading and content:
            rewritten_content = rewrite_articles_with_gemini(content)
            if rewritten_content:
              rewritten_articles.append({"heading": heading, "content": rewritten_content})
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
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    log(f"Starting generation of PDF file")

    for article in rewritten_articles:
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, article["heading"], ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, f"{article['content']}\n\n")
        pdf.ln(10)

    pdf.output(output_pdf_path)
    log(f"PDF saved to {output_pdf_path}")
    log(f"Finished generating PDF file")
    log(f"Finished processing all articles from {input_json_path}")
    
    
# Main function
def main():
    # Get file paths
    input_json_path = os.path.join(JSON_DIR, "top_articles.json")
    output_json_path = os.path.join(JSON_DIR, "rewritten_articles.json")
    output_pdf_path = os.path.join(PDF_DIR, "rewritten_articles.pdf")

    log(f"Starting main function with input path {input_json_path}")
    process_and_save_rewritten_articles(input_json_path, output_json_path, output_pdf_path)

    # Save logs
    save_logs()
    log(f"Finished main function")

if __name__ == "__main__":
    main()
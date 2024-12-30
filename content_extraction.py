import os
import re
import csv
import json
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Load environment variables
load_dotenv()

firecrawl_api_key = os.getenv("FIRE_CRAWL_API")

# Directory structure
OUTPUT_DIR = "output"
CONTENT_MD_DIR = os.path.join(OUTPUT_DIR, "content_md_files")
JSON_DIR = os.path.join(OUTPUT_DIR, "json")
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")

# Ensure directories exist
os.makedirs(CONTENT_MD_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)

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

# Scrape data from a URL
def scrape_data(url):
    try:
        app = FirecrawlApp(api_key=firecrawl_api_key)
        scraped_data = app.scrape_url(url)
        if "markdown" in scraped_data:
            log(f"Successfully scraped data from {url}")
            return scraped_data["markdown"]
        else:
            raise KeyError("The key 'markdown' does not exist in the scraped data!")
    except Exception as e:
        log(f"Error scraping {url}: {e}")
        return ""

def extract_heading_content(markdown_content):
     """Extracts heading and content from markdown content."""
     heading_match = re.search(r'#\s*(.+)', markdown_content)
     if heading_match:
         heading = heading_match.group(1).strip()
         content = markdown_content.replace(f'# {heading}', '', 1).strip()
         return heading, content
     else:
         return "", markdown_content.strip()

def save_articles(top_articles_path, content_md_dir, output_json_path):
    """Saves the content of top articles to markdown and json files"""
    all_articles = []
    log(f"Starting to save all articles from {top_articles_path} to markdown and json files")
    with open(top_articles_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            url = row["URL"]
            heading = row["Heading"]
            if url and heading:
                content = scrape_data(url)
                if content:
                  heading, content = extract_heading_content(content)
                  filename = sanitize_filename(heading) + ".md"
                  md_path = os.path.join(content_md_dir, filename)
                  with open(md_path, "w", encoding="utf-8") as md_file:
                    md_file.write(f"# {heading}\n\n")
                    md_file.write(f"{content}\n")
                  log(f"Saved content markdown file: {md_path}")
                  all_articles.append({"heading": heading, "content": content, "url": url})
                else:
                  log(f"Could not scrape data from {url}, skipping this article")
            else:
                log(f"Skipping row due to missing URL or Heading: {row}")
    
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(all_articles, json_file, indent=4)
        log(f"Saved all articles to {output_json_path}")
    log(f"Finished saving all the articles to {content_md_dir} and {output_json_path}")

# Main function
def main():
   # Step 1: Get the list of urls from the csv
    top_articles_path = os.path.join(CSV_DIR, "top_articles.csv")
    output_json_path = os.path.join(JSON_DIR, "top_articles.json")
    log(f"Starting main function with top articles path: {top_articles_path}")
    save_articles(top_articles_path, CONTENT_MD_DIR, output_json_path)


    # Save logs
    save_logs()
    log(f"Finished main function")

if __name__ == "__main__":
    main()
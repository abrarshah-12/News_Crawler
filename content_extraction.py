import os
import re
import csv
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Load environment variables
load_dotenv()

FIRE_CRAWL_API_KEY = os.getenv("FIRE_CRAWL_API")

# Directory structure
OUTPUT_DIR = "output"
CONTENT_MD_DIR = os.path.join(OUTPUT_DIR, "content_md_files")
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")

# Ensure directories exist
os.makedirs(CONTENT_MD_DIR, exist_ok=True)

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

# Scrape data from a URL
def scrape_data(url):
    """Scrapes content from a given URL using Firecrawl."""
    try:
        app = FirecrawlApp(api_key=FIRE_CRAWL_API_KEY)
        scraped_data = app.scrape_url(url)
        if "markdown" in scraped_data:
            log(f"Successfully scraped data from {url}")
            return scraped_data["markdown"]
        else:
            raise KeyError(f"The key 'markdown' does not exist in the scraped data from {url}")
    except Exception as e:
        log(f"Error scraping {url}: {e}")
        return ""

def extract_heading_content(markdown_content):
    """Extracts heading and content from markdown content."""
    heading_match = re.search(r'#\s*(.+)', markdown_content)
    if heading_match:
        heading = heading_match.group(1).strip()
        content = re.sub(r'!?\[.*?\]\(.*?\)', '', markdown_content.replace(f'# {heading}', '', 1)).strip()
        return heading, content
    else:
        return "", markdown_content.strip()

def save_articles_to_md(top_articles_path, content_md_dir):
    """Saves the content of top articles to markdown files."""
    log(f"Starting to save articles from {top_articles_path} to markdown files")
    with open(top_articles_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            url = row["URL"]
            heading = row["Heading"]
            if url and heading:
                content = scrape_data(url)
                if content:
                  heading, content = extract_heading_content(content)
                  sanitized_heading = sanitize_filename(heading)
                  output_file_path = os.path.join(content_md_dir, f"{sanitized_heading}.md")
                  
                  with open(output_file_path, "w", encoding="utf-8") as md_file:
                      md_file.write(f"# {heading}\n\n{content}")
                  log(f"Saved article to {output_file_path}")
                else:
                    log(f"Could not scrape data from {url}, skipping this article")
            else:
               log(f"Skipping row due to missing URL or Heading: {row}")
    log(f"Finished saving all the articles to {content_md_dir}")

# Main function
def main():
    """Main function to orchestrate the scraping and saving process."""
    # Step 1 & 2: Load the top articles from CSV
    top_articles_path = os.path.join(CSV_DIR, "top_articles.csv")

    # Step 3 & 4: Save markdown content
    save_articles_to_md(top_articles_path, CONTENT_MD_DIR)

    # Save logs
    save_logs()
    log(f"Finished main function")

if __name__ == "__main__":
    main()
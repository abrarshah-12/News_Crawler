import os
import re
import csv
from utils.logger import log, log_exception
from config import INITIAL_MD_DIR, CONTENT_MD_DIR
from utils.helpers import sanitize_filename
from scrapers.firecrawl_scraper import scrape_data
from utils.errors import FileProcessingError, FirecrawlError
import shutil
import urllib.parse  # Retained from the second branch

def save_markdown(markdown_content, base_name):
    """Saves scraped data to a Markdown file."""
    try:
        file_path = os.path.join(INITIAL_MD_DIR, f"{base_name}.md")
        with open(file_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        log(f"Saved markdown content to {file_path}")
    except Exception as e:
        raise FileProcessingError(f"Error during markdown saving: {e}")


def extract_heading_content(markdown_content):
    """Extracts heading and content from markdown content."""
    heading_match = re.search(r'#\s*(.+)', markdown_content)
    if heading_match:
        heading = heading_match.group(1).strip()
        content = re.sub(r'!?\[.*?\]\(.*?\)', '', markdown_content.replace(f'# {heading}', '', 1)).strip()
        return heading, content
    else:
        return "", markdown_content.strip()


def save_articles_to_md(top_articles_path):
    """Saves the content of top articles to markdown files."""
    log(f"Starting to save articles from {top_articles_path} to markdown files")
    try:
        # Clear the content_md_dir before adding content
        if os.path.exists(CONTENT_MD_DIR):
            log(f"Clearing existing content from directory {CONTENT_MD_DIR}")
            shutil.rmtree(CONTENT_MD_DIR)

        os.makedirs(CONTENT_MD_DIR, exist_ok=True)

        with open(top_articles_path, "r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                url = row["URL"]
                heading = row["Heading"]
                source = row["Main Source"]
                if url and heading:
                    try:
                        content = scrape_data(url)
                        if content:
                            heading, content = extract_heading_content(content)

                            # Keep both changes: sanitized_heading and sanitized_url
                            sanitized_heading = sanitize_filename(heading)
                            sanitized_url = sanitize_filename(url)

                            # Save using sanitized URL
                            output_file_path = os.path.join(CONTENT_MD_DIR, f"{sanitized_url}.md")
                            with open(output_file_path, "w", encoding="utf-8") as md_file:
                                md_file.write(f"# {heading}\n\n{content}")
                            log(f"Saved article to {output_file_path}")

                            # Save using sanitized heading
                            output_file_path_heading = os.path.join(CONTENT_MD_DIR, f"{sanitized_heading}.md")
                            with open(output_file_path_heading, "w", encoding="utf-8") as md_file:
                                md_file.write(f"# {heading}\n\n{content}")
                            log(f"Saved article to {output_file_path_heading}")

                        else:
                            log(f"Could not scrape data from {url}, skipping this article")
                    except FirecrawlError as e:
                        log_exception(e, f"Error during firecrawl scraping for article with url: {url}, skipping")
                        continue

                else:
                    log(f"Skipping row due to missing URL or Heading: {row}")
        log(f"Finished saving all the articles to {CONTENT_MD_DIR}")
    except Exception as e:
        raise FileProcessingError(f"Error during saving article to md files: {e}")
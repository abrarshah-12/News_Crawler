import os
import re
import csv
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Load environment variables
load_dotenv()

# Access the Firecrawl API key
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_api_key:
    print("Error: FIRECRAWL_API_KEY not found in environment variables.")
    exit()

# Directory structure
OUTPUT_DIR = "output"
INITIAL_MD_DIR = os.path.join(OUTPUT_DIR, "initial_md_files")
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")

# Ensure directories exist
os.makedirs(INITIAL_MD_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

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

def extract_article_links(content):
    """Extracts article links from markdown content, formatted as [title](url)
    """
    article_links_regex = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
    matches = article_links_regex.findall(content)
    return [(match[0], match[1]) for match in matches]


# Save articles in Markdown, JSON, and CSV formats
def save_markdown(markdown_content, base_name):
    """Saves scraped data to a Markdown file."""
    file_path = os.path.join(INITIAL_MD_DIR, f"{base_name}.md")
    with open(file_path, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
    log(f"Saved markdown content to {file_path}")

def save_all_articles_to_csv(all_articles, base_name):
    """Saves all extracted articles to a CSV file."""
    csv_path = os.path.join(CSV_DIR, f"{base_name}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Main Source", "URL", "Heading"])  # Header row
        for source, url, heading in all_articles:
            writer.writerow([source, url, heading])
        log(f"Saved all articles to CSV file: {csv_path}")

def clean_csv(input_csv_path, output_csv_path):
    """Cleans the CSV file to contain only rows with news headings."""
    log(f"Starting cleaning CSV from {input_csv_path} and saving to {output_csv_path}")
    non_news_patterns = [
        re.compile(r'bookmark', re.IGNORECASE),
        re.compile(r'sign up', re.IGNORECASE),
        re.compile(r'^page \d+', re.IGNORECASE),
        re.compile(r'comments', re.IGNORECASE),
        re.compile(r'^[!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~ ]*$', re.IGNORECASE),  # Only special chars
        re.compile(r'^\d+$', re.IGNORECASE), # Only numbers
        re.compile(r'^\w+$', re.IGNORECASE), #Only one word
        re.compile(r'iframe', re.IGNORECASE),
        re.compile(r'^(\w+\s*){0,4}$', re.IGNORECASE) # 4 or less words
    ]
    non_article_url_patterns = [
        re.compile(r'newsletter-preference-centre', re.IGNORECASE),
        re.compile(r'reachplc.com/about-us/our-brands', re.IGNORECASE),
        re.compile(r'privacy-notice', re.IGNORECASE),
        re.compile(r'cookie-policy', re.IGNORECASE),
        re.compile(r'/all-about/', re.IGNORECASE),

    ]
    cleaned_articles = []
    with open(input_csv_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader) # Skip the header row
        for row in reader:
            source, url, heading = row
            if not any(pattern.search(heading) for pattern in non_news_patterns) and not any(pattern.search(url) for pattern in non_article_url_patterns):
                cleaned_articles.append(row)

    with open(output_csv_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header) # Write the header back into the new csv
        writer.writerows(cleaned_articles) # Write the cleaned data to the file
    log(f"Cleaned CSV file saved to {output_csv_path}")

def select_and_save_top_articles(input_csv_path, output_csv_path):
    """Selects the top 5 articles for each main source and saves them to a CSV."""
    log(f"Starting selection and save of top articles from {input_csv_path} and save to {output_csv_path}")
    top_articles = {}
    with open(input_csv_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            source = row["Main Source"]
            if source not in top_articles:
                top_articles[source] = []
            if len(top_articles[source]) < 5:
                 top_articles[source].append(row)
    
    with open(output_csv_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Main Source", "URL", "Heading"]) # Header row
        for source, articles in top_articles.items():
            for article in articles:
              writer.writerow([article["Main Source"], article["URL"], article["Heading"]])
              log(f"Saved article: {article['Heading']} for source: {source}")
    log(f"Finished saving top articles to {output_csv_path}")
    

# Main function
def main():
    # Step 1: URLs to scrape (crime sections)
    source_urls = [
        ("MyLondon", "https://www.mylondon.news/all-about/crime"),
        ("BirminghamLive", "https://www.birminghammail.co.uk/all-about/crime"),
        ("ManchesterEveningNews", "https://www.manchestereveningnews.co.uk/all-about/crime"),
        ("LiverpoolEcho", "https://www.liverpoolecho.co.uk/all-about/crime"),
        ("WalesOnline", "https://www.walesonline.co.uk/all-about/crime"),
    ]

    all_articles = []

    # Step 2: Scrape, save to MD, and extract articles
    for source_name, source_url in source_urls:
        log(f"Starting to scrape data from: {source_url}")
        markdown_content = scrape_data(source_url)
        if markdown_content:
           
            # Save to MD
            sanitized_name = sanitize_filename(source_name)
            save_markdown(markdown_content, sanitized_name)
           
           # Extract articles
            article_links = extract_article_links(markdown_content)
            for title, url in article_links:
               all_articles.append((source_name, url, title))
        else:
          log(f"No content returned from: {source_url}")


    # Step 3: Save articles to CSV
    if all_articles:
        base_name = "all_articles"
        save_all_articles_to_csv(all_articles, base_name)
    else:
        log("No articles were found during the scraping.")

    # Step 4: Clean the CSV file
    input_csv_path = os.path.join(CSV_DIR, "all_articles.csv")
    output_csv_path = os.path.join(CSV_DIR, "cleaned_articles.csv")
    clean_csv(input_csv_path, output_csv_path)

    # Step 5: Select top articles and save them to the top articles file
    input_csv_path = os.path.join(CSV_DIR, "cleaned_articles.csv")
    output_csv_path = os.path.join(CSV_DIR, "top_articles.csv")
    select_and_save_top_articles(input_csv_path, output_csv_path)

    # Save logs
    save_logs()

if __name__ == "__main__":
    main()
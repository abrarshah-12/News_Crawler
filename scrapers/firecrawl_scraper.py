import time
import re
from firecrawl import FirecrawlApp
from utils.logger import log
from config import FIRECRAWL_API_KEY
from utils.errors import FirecrawlError
import random


def scrape_data(url, initial_delay=1, max_delay=16):
    """Scrapes content from a given URL using Firecrawl with retry logic."""
    delay = initial_delay
    retries = 0
    try:
        if not FIRECRAWL_API_KEY:
          raise FirecrawlError("Firecrawl API Key is missing")
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        while True:
            try:
                scraped_data = app.scrape_url(url)
                if "markdown" in scraped_data:
                    log(f"Successfully scraped data from {url}")
                    return scraped_data["markdown"]
                else:
                   raise FirecrawlError(f"The key 'markdown' does not exist in the scraped data from {url}")
            except Exception as e:
                log(f"Error scraping {url}: {e}. Retries: {retries}")
                if "429" in str(e) or "Rate limit" in str(e):
                    log(f"Rate limit hit. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)  # exponential backoff
                    retries += 1
                else:
                   raise FirecrawlError(f"Error during firecrawl scraping: {e}")
            finally:
                time.sleep(random.uniform(0.5, 1.5))

    except Exception as e:
        log(f"Error during firecrawl scraping {url}: {e}")
        raise FirecrawlError(f"Error during firecrawl scraping: {e}")



def extract_article_links(content):
    """Extracts article links from markdown content, formatted as [title](url)"""
    article_links_regex = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
    matches = article_links_regex.findall(content)
    return [(match[0], match[1]) for match in matches]
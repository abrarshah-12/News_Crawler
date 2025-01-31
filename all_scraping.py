import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
import pytz
import logging
import json
from tenacity import retry, stop_after_attempt, wait_fixed
from httpx import RemoteProtocolError
from typing import List, Dict, ClassVar
from pydantic import BaseModel, Field
from crewai_tools import BaseTool
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScrapingToolInput(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to scrape.")

class ScrapingToolOutput(BaseModel):
    data: List[Dict] = Field(..., description="Extracted articles with raw HTML content and link.")

class WebScrapingTool(BaseTool):
    name: str = "Web Scraping Tool"
    description: str = "Scrapes web pages, extracting entire HTML content and link."

    headers: ClassVar[dict] = {  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    }

    def _run(self, urls: List[str]) -> ScrapingToolOutput:
        links = self._extract_links(urls)
        data = self._scrape_data(links)

        # Filter only URLs with numbers at the end and optionally a fragment like #comments-wrapper
        filtered_data = [article for article in data if self._is_valid_link(article['link'])]

        return ScrapingToolOutput(data=filtered_data)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=lambda e: isinstance(e, RemoteProtocolError))
    def _extract_links(self, urls: List[str]) -> List[str]:
        """Extract article links from homepage."""
        links = set()  # Use a set to avoid duplicates
        for url in urls:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    if "/news/" in a['href'] or "/article/" in a['href']:  # Adjust based on actual site structure
                        full_link = a['href'] if a['href'].startswith('http') else url.rstrip('/') + a['href']
                        links.add(full_link)  # Add to set (removes duplicates)
            except Exception as e:
                logging.error(f"Error fetching links from {url}: {str(e)}")
        return list(links)  # Convert set back to list

    def _scrape_data(self, links: List[str]) -> List[Dict]:
        """Scrape and filter articles."""
        data = []
        for link in links:
            try:
                article_data = self._scrape_article(link)
                if article_data and self._is_today(article_data['date']):
                    data.append(article_data)
            except Exception as e:
                logging.error(f"Error scraping {link}: {str(e)}")
        return data

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=lambda e: isinstance(e, RemoteProtocolError))
    def _scrape_article(self, url: str) -> Dict:
        """Extract raw HTML content of the article and publication date."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract the entire HTML content
            raw_html = str(soup)

            # Extract the publication date (if available)
            date = self._extract_date(soup)

            # Log the date extracted for debugging purposes
            logging.info(f"Extracted date for {url}: {date}")

            # Store the entire HTML content and date as a dictionary
            return {
                "content": raw_html,
                "link": url,
                "date": date
            }

        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return None

    def _extract_date(self, soup) -> str:
        """Extract the publication date of the article."""
        date_formats = ["article:published_time", "datePublished", "dateModified"]

        for fmt in date_formats:
            date_tag = soup.find('meta', {"property": fmt}) or soup.find('meta', {"name": fmt})
            if date_tag and date_tag.get('content'):
                return date_tag['content']

        # Look for <time> tag
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            return time_tag['datetime']

        # Try to find date within text
        for tag in soup.find_all(['span', 'p', 'div']):
            text = tag.get_text()
            if any(char.isdigit() for char in text):  
                try:
                    parsed_date = parser.parse(text, fuzzy=True)
                    return parsed_date.strftime("%Y-%m-%d")
                except:
                    continue  

        return "No date available"

    def _is_today(self, date_string: str) -> bool:
        """Check if date is today (UK timezone)."""
        if not date_string or date_string == "No date available":
            return False

        try:
            uk_tz = pytz.timezone("Europe/London")
            article_date = parser.parse(date_string, fuzzy=True)

            # Log the parsed date for debugging purposes
            logging.info(f"Parsed date for comparison: {article_date}")

            if article_date.tzinfo is None:
                article_date = pytz.utc.localize(article_date).astimezone(uk_tz)
            else:
                article_date = article_date.astimezone(uk_tz)

            # Log the final date for comparison
            logging.info(f"Article date (in UK timezone): {article_date}")

            # Compare the article date with today's date
            return article_date.date() == datetime.now(uk_tz).date()

        except Exception as e:
            logging.error(f"Date parsing issue: {date_string}, Error: {e}")
            return False

    def _is_valid_link(self, link: str) -> bool:
        """Check if the link ends with a number and optionally has a #fragment."""
        pattern = r'\d+$'  # Match links with numbers at the end, optionally followed by a fragment
        match = re.search(pattern, link)
        # if match:
        #     logging.info(f"Valid link: {link}")  # Log valid links
        # else:
        #     logging.info(f"Invalid link: {link}")  # Log invalid links
        return match is not None 

# Run the scraper
scraping_tool = WebScrapingTool()

result = scraping_tool._run([
    "https://www.mylondon.news/all-about/crime",
    "https://www.birminghammail.co.uk/all-about/crime",
    "https://www.manchestereveningnews.co.uk/all-about/crime",
    "https://www.liverpoolecho.co.uk/all-about/crime",
    "https://www.walesonline.co.uk/all-about/crime"
])

# Save results
with open('crew_scraped_data.json', 'w') as f:
    json.dump(result.dict(), f, indent=4)

# Print confirmation message after saving the data
print("Data saved to crew_scraped_data.json")

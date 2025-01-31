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
    data: List[Dict] = Field(..., description="Extracted articles with title, subtitle, content, and date.")

class WebScrapingTool(BaseTool):
    name: str = "Web Scraping Tool"
    description: str = "Scrapes news articles, extracting title, subtitle, paragraphs, and date."

    headers: ClassVar[dict] = {  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    }

    def _run(self, urls: List[str]) -> ScrapingToolOutput:
        links = self._extract_links(urls)
        data = self._scrape_data(links)

        # Filter only URLs that have a number after the last slash
        filtered_data = [article for article in data if re.search(r'\d+$', article['link'])]

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
        """Extract article details: title, subtitle, paragraphs, date."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            title = self._extract_title(soup)
            subtitle = self._extract_subtitle(soup)
            date = self._extract_date(soup)
            paragraphs = self._extract_paragraphs(soup)

            # Skip article if title or content is missing
            if not title or not paragraphs:
                logging.info(f"Skipping {url} due to missing title or content.")
                return None

            return {
                "title": title,
                "subtitle": subtitle if subtitle else "No subtitle available",
                "date": date,
                "content": " ".join(paragraphs),
                "link": url
            }

        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return None
        

    def _extract_title(self, soup):
        title = soup.find('h1') or soup.find('title')
        return title.text.strip() if title else None

    def _extract_subtitle(self, soup):
        subtitle = soup.find('h2') or soup.find('meta', attrs={"name": "description"})
        if subtitle and subtitle.name == 'meta':
            return subtitle['content'].strip() if subtitle.get('content') else None
        return subtitle.text.strip() if subtitle else None

    def _extract_date(self, soup):
        """Find date from <time>, meta tags, or page text."""
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

    def _extract_paragraphs(self, soup):
        """Extract meaningful text from <p> tags or fallback containers."""
        paragraphs = []

        # Log all raw <p> text before filtering
        raw_paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        logging.info(f"Found raw paragraphs: {raw_paragraphs[:5]}")  # Log first 5 raw paragraphs for inspection

        # Filter paragraphs: Only those longer than 30 characters
        paragraphs = [p for p in raw_paragraphs if len(p) > 30]

        # If no paragraphs found, fallback to alternative article containers
        if not paragraphs:
            article_containers = [
                "article", ".article-body", ".story-body", ".post-content", 
                "#article-content", "#story-text", ".entry-content", ".content"
            ]
            
            for container in article_containers:
                container_element = soup.select_one(container)
                if container_element:
                    paragraphs = [p.get_text(strip=True) for p in container_element.find_all("p") if len(p.get_text(strip=True)) > 30]
                    if paragraphs:
                        break

        # If still no paragraphs, fallback to the meta description
        if not paragraphs:
            subtitle = soup.find('meta', attrs={"name": "description"})
            if subtitle and subtitle.get('content'):
                paragraphs = [subtitle['content']]

        # Log the final list of paragraphs before filtering unwanted content
        logging.info(f"Filtered paragraphs: {paragraphs[:5]}")  # Log first 5 paragraphs after filtering

        # Remove unwanted content (ads, sponsored text)
        filtered_paragraphs = [p for p in paragraphs if "advertisement" not in p.lower() and "sponsored" not in p.lower()]

        return filtered_paragraphs if filtered_paragraphs else ["No content available"]



    def _is_today(self, date_string: str) -> bool:
        """Check if date is today (UK timezone)."""
        if not date_string:
            return False

        try:
            uk_tz = pytz.timezone("Europe/London")
            article_date = parser.parse(date_string, fuzzy=True)

            if article_date.tzinfo is None:
                article_date = pytz.utc.localize(article_date).astimezone(uk_tz)
            else:
                article_date = article_date.astimezone(uk_tz)

            return article_date.date() == datetime.now(uk_tz).date()

        except Exception as e:
            logging.error(f"Date parsing issue: {date_string}, Error: {e}")
            return False

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
    print("Data saved to crew_scraped_data.json")
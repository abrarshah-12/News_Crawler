# processors/csv_processor.py
import csv
import os
from utils.logger import log
from config import CSV_DIR
from utils.errors import FileProcessingError
import re

def save_all_articles_to_csv(all_articles, base_name):
    """Saves all extracted articles to a CSV file."""
    try:
      csv_path = os.path.join(CSV_DIR, f"{base_name}.csv")
      with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
          writer = csv.writer(csv_file)
          writer.writerow(["Main Source", "URL", "Heading"])  # Header row
          for source, url, heading in all_articles:
              writer.writerow([source, url, heading])
          log(f"Saved all articles to CSV file: {csv_path}")
    except Exception as e:
      raise FileProcessingError(f"Error during csv saving: {e}")


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
    try:
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
    except Exception as e:
      raise FileProcessingError(f"Error during csv cleaning: {e}")



def select_and_save_top_articles(input_csv_path, output_csv_path):
    """Selects the top 5 articles for each main source and saves them to a CSV."""
    log(f"Starting selection and save of top articles from {input_csv_path} and save to {output_csv_path}")
    top_articles = {}
    try:
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
    except Exception as e:
        raise FileProcessingError(f"Error during selecting and saving top articles to csv {e}")
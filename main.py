import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utils.logger import log, configure_logger, log_exception
from config import SOURCE_URLS, CSV_DIR, JSON_DIR, PDF_DIR, EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from scrapers.firecrawl_scraper import scrape_data, extract_article_links
from processors.csv_processor import save_all_articles_to_csv, clean_csv, select_and_save_top_articles
from processors.markdown_processor import save_markdown, save_articles_to_md
from processors.content_cleaner import process_and_save_cleaned_content
from processors.gemini_rewriter import process_and_save_rewritten_articles as gemini_process_and_save_rewritten_articles
from processors.openai_rewriter import process_and_save_rewritten_articles as openai_process_and_save_rewritten_articles
from processors.pdf_generator import process_and_save_articles
from utils.helpers import sanitize_filename
from utils.errors import FirecrawlError, FileProcessingError, GeminiError, ProcessingError
import psycopg2
import datetime

def load_subscribers():
    """Loads subscribers from the database."""
    conn = None
    subscribers = []
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM subscribers")
            subscriber_emails = cur.fetchall()
            subscribers = [email[0] for email in subscriber_emails]
    except Exception as e:
         log_exception(e, "Error fetching subscribers from the database.")
         subscribers=[]
    finally:
        if conn:
            conn.close()
    return subscribers



def send_email(pdf_path, subscribers):
    """Sends the generated PDF to subscribers."""
    if not subscribers:
        log("No subscribers, Email sending will be skipped", level=40)
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(subscribers)
        msg["Subject"] = "Daily Crime News Report"

        body = "Here is your Daily Crime News Report.\n\n"
        msg.attach(MIMEText(body, "plain"))

        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(pdf_attachment)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        log(f"Email sent successfully to {len(subscribers)} subscribers")
    except Exception as e:
        log_exception(e, "Error sending email")


def main():
    configure_logger()
    log(f"Starting the news processing pipeline at: {datetime.datetime.now()}")
    all_articles = []
    try:
        # Step 1 & 2: Scrape, save to MD, and extract articles
        for source_name, source_url in SOURCE_URLS:
            log(f"Starting to scrape data from: {source_url}")
            try:
              markdown_content = scrape_data(source_url)
            except FirecrawlError as e:
              log_exception(e, f"Firecrawl error during scraping of URL {source_url}")
              continue # Skip this URL and continue processing

            if markdown_content:
                sanitized_name = sanitize_filename(source_name)
                try:
                    save_markdown(markdown_content, sanitized_name)
                except FileProcessingError as e:
                  log_exception(e, f"Error saving markdown for {source_name}")
                  continue # Skip and move to next URL
                article_links = extract_article_links(markdown_content)
                for title, url in article_links:
                    all_articles.append((source_name, url, title))
            else:
                log(f"No content returned from: {source_url}")

         # Step 3: Save articles to CSV
        if all_articles:
          base_name = "all_articles"
          try:
            save_all_articles_to_csv(all_articles, base_name)
          except FileProcessingError as e:
            log_exception(e, "Error saving all articles to CSV")

        else:
            log("No articles were found during the scraping.")

        # Step 4: Clean the CSV file
        input_csv_path = os.path.join(CSV_DIR, "all_articles.csv")
        output_csv_path = os.path.join(CSV_DIR, "cleaned_articles.csv")
        try:
           clean_csv(input_csv_path, output_csv_path)
        except FileProcessingError as e:
            log_exception(e, "Error cleaning CSV")

        # Step 5: Select top articles and save them to the top articles file
        input_csv_path = os.path.join(CSV_DIR, "cleaned_articles.csv")
        output_csv_path = os.path.join(CSV_DIR, "top_articles.csv")
        try:
           select_and_save_top_articles(input_csv_path, output_csv_path)
        except FileProcessingError as e:
           log_exception(e, "Error selecting top articles from CSV")

        # Step 6: Scrape and save content from the top articles to MD files
        try:
           save_articles_to_md(output_csv_path)
        except FileProcessingError as e:
          log_exception(e, "Error during saving articles to content markdown files")

        # Step 7: Clean and save the content to JSON file
        input_md_dir = os.path.join(JSON_DIR, "..", "content_md_files")
        output_json_path = os.path.join(JSON_DIR, "cleaned_articles.json")
        try:
           process_and_save_cleaned_content(input_md_dir, output_json_path)
        except FileProcessingError as e:
            log_exception(e, "Error processing and saving cleaned content to JSON")

         # Step 8: Rewrite content with OpenAI then fall back to gemini if needed
        input_json_path = os.path.join(JSON_DIR, "cleaned_articles.json")
        output_json_path = os.path.join(JSON_DIR, "rewritten_articles.json")
        try:
            log("Attempting to rewrite content with OpenAI...")
            openai_process_and_save_rewritten_articles(input_json_path, output_json_path)
        except (ProcessingError, Exception) as e:
            log_exception(e, "Error during rewriting articles with OpenAI, falling back to Gemini")
            try:
                gemini_process_and_save_rewritten_articles(input_json_path, output_json_path)
            except (GeminiError, ProcessingError) as e:
              log_exception(e, "Error during rewriting articles with Gemini")


        # Step 9: Generate PDF
        input_json_path = os.path.join(JSON_DIR, "rewritten_articles.json")
        output_pdf_path = os.path.join(PDF_DIR, "Daily Report.pdf")
        try:
           process_and_save_articles(input_json_path, output_pdf_path)
        except FileProcessingError as e:
          log_exception(e, "Error generating the PDF")
          return # Stop processing

        # Step 10 : Send email
        subscribers = load_subscribers()
        send_email(output_pdf_path, subscribers)

        log("Finished the news processing pipeline successfully.")

    except Exception as e:
       log_exception(e, "An unexpected error occurred during the pipeline")
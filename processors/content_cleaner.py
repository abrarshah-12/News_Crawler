# processors/content_cleaner.py
import os
import re
import json
from utils.logger import log
from config import CONTENT_MD_DIR, JSON_DIR
from utils.helpers import sanitize_filename
from utils.errors import FileProcessingError
import urllib.parse


def clean_markdown_content(markdown_content):
    """Cleans markdown content by removing links, images, extra whitespace, and irrelevant text."""
    # Remove links
    cleaned_content = re.sub(r'!?\[.*?\]\(.*?\)', '', markdown_content)
    # Remove images
    cleaned_content = re.sub(r'!?\[.*?\]', '', cleaned_content)
    # Remove markdown headings
    cleaned_content = re.sub(r'#+\s*', '', cleaned_content)
    # Remove share and bookmark etc
    cleaned_content = re.sub(r'(- Bookmark|- Share|By|SubscribePlease enter a valid emailSomething went wrong, please try again later.|We use your sign-up to provide content in ways you\u2019ve consented to and improve our understanding of you. This may include adverts from us and third parties based on our knowledge of you.|Thank you for subscribing!|We have more newsletters|See Our  |See Our  |\u00d7|No thanks, close|See our |Story Saved|You can find this story in \u00a0Or by navigating to the user icon in the top right.|Follow\u00a0(.*?)|More On|(.*?)- News\n-(.*?)\n- Most Read\n- Most Recent)', '', cleaned_content)
    # Remove URLs
    cleaned_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned_content)
    # Remove irrelevant words
    cleaned_content = re.sub(r'(Sign Up|Bookmark|READ MORE:|READ NEXT:|Log in|See More|Follow (.*?)|Stay in the know|Get the latest.*?(?:news|stories|updates).*(?:sent straight to your inbox|on WhatsApp).*)', '', cleaned_content, flags=re.IGNORECASE)
    # Remove newlines
    cleaned_content = re.sub(r'\n{2,}', '\n', cleaned_content)
    # Remove excessive whitespace
    cleaned_content = ' '.join(cleaned_content.split())
    return cleaned_content.strip()


def process_and_save_cleaned_content(content_md_dir, output_json_path):
    """Processes markdown files, cleans their content, and saves to a JSON file."""
    log(f"Starting to process and save cleaned content from {content_md_dir} to {output_json_path}")
    output_data = []
    try:
        for filename in os.listdir(content_md_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(content_md_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as md_file:
                        content = md_file.read()
                        # Split the file into articles based on the presence of a heading
                        articles = re.split(r'(?=\n#\s)', content)

                        for article_content in articles:
                            if article_content.strip():
                                cleaned_content = clean_markdown_content(article_content)
                                # Extract URL from filename
                                base_filename = os.path.splitext(os.path.basename(filename))[0]
                                # Ensure URL starts with "https://"
                                if base_filename.startswith("https___"):
                                    base_url = base_filename.replace("https___", "https://").replace('_', '/')
                                else:
                                    base_url = f"https://{base_filename.replace('_', '/')}"
                                output_data.append({"content": cleaned_content, "url": base_url, "source": "unknown"})  # Added url and source
                                log(f"Cleaned and stored content from: {filename}")
                except Exception as e:
                    log(f"Error processing {filename}: {e}")
        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(output_data, json_file, indent=4)
            log(f"Saved cleaned content to {output_json_path}")
        log("Finished processing all markdown files.")
    except Exception as e:
        raise FileProcessingError(f"Error during cleaning content: {e}")
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directory structure
OUTPUT_DIR = "output"
CONTENT_MD_DIR = os.path.join(OUTPUT_DIR, "content_md_files")
JSON_DIR = os.path.join(OUTPUT_DIR, "json")
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")

# Ensure directories exist
os.makedirs(JSON_DIR, exist_ok=True)

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

def sanitize_filename(name):
    """Sanitizes a string to use as a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

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
    # Remove urls
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
                            output_data.append({"content": cleaned_content})
                            log(f"Cleaned and stored content from: {filename}")
            except Exception as e:
                log(f"Error processing {filename}: {e}")

    with open(output_json_path, "w", encoding="utf-8") as json_file:
        json.dump(output_data, json_file, indent=4)
        log(f"Saved cleaned content to {output_json_path}")
    log("Finished processing all markdown files.")


# Main function
def main():
    """Main function to orchestrate the cleaning and saving process."""
    # Get file paths
    input_md_dir = CONTENT_MD_DIR
    output_json_path = os.path.join(JSON_DIR, "cleaned_articles.json")

    log(f"Starting main function with input path {input_md_dir}")
    process_and_save_cleaned_content(input_md_dir, output_json_path)

    # Save logs
    save_logs()
    log(f"Finished main function")


if __name__ == "__main__":
    main()
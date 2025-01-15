import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

# Directory structure
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'output'))
INITIAL_MD_DIR = os.path.join(OUTPUT_DIR, "initial_md_files")
CONTENT_MD_DIR = os.path.join(OUTPUT_DIR, "content_md_files")
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
JSON_DIR = os.path.join(OUTPUT_DIR, "json")
PDF_DIR =  os.path.abspath(os.path.join(OUTPUT_DIR, "pdfs"))
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.txt")
TIMES_NEW_ROMAN_FONT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fonts', 'timr45w.ttf'))

# API Keys
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Source URLs
SOURCE_URLS = [
        ("MyLondon", "https://www.mylondon.news/all-about/crime"),
        ("BirminghamLive", "https://www.birminghammail.co.uk/all-about/crime"),
        ("ManchesterEveningNews", "https://www.manchestereveningnews.co.uk/all-about/crime"),
        ("LiverpoolEcho", "https://www.liverpoolecho.co.uk/all-about/crime"),
        ("WalesOnline", "https://www.walesonline.co.uk/all-about/crime"),
    ]


# Email Configuration
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")


# Database Configuration
DB_URL = os.getenv("DB_URL")

if DB_URL:
        parsed_db_url = urllib.parse.urlparse(DB_URL)
        DB_HOST = parsed_db_url.hostname
        DB_PORT = parsed_db_url.port
        DB_NAME = parsed_db_url.path[1:]
        DB_USER = parsed_db_url.username
        DB_PASSWORD = parsed_db_url.password
else:
   DB_HOST = os.getenv("DB_HOST", "localhost")
   DB_PORT = int(os.getenv("DB_PORT", 5432))
   DB_NAME = os.getenv("DB_NAME", "news_subscriber_db")
   DB_USER = os.getenv("DB_USER", "news_user")
   DB_PASSWORD = os.getenv("DB_PASSWORD", "your_database_password")

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INITIAL_MD_DIR, exist_ok=True)
os.makedirs(CONTENT_MD_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
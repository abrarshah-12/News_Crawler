# UK Crime News Aggregator and Rewriter

This project is a Python-based system designed to scrape, process, and reformat news articles related to crime in the UK, ultimately generating a well-formatted PDF document. It utilizes web scraping, natural language processing via LLMs (OpenAI and Gemini), and PDF generation libraries.

## Project Overview

The primary goal of this project is to automate the process of gathering crime-related news from various online sources, transforming the content into a more engaging and standardized format, and presenting it in a professional PDF report. The project handles:

1.  **Web Scraping:** Extracts relevant article links and content from specified websites.
2.  **Content Cleaning:** Cleans the raw text by removing irrelevant information, links, and formatting.
3.  **Content Rewriting:** Uses large language models (LLMs) to rewrite the articles in a specific style.
4.  **PDF Generation:** Generates a formatted PDF document containing the rewritten articles, complete with a title page and page numbers.

## Project Structure

The project is structured into several modules:

*   `main.py`: The entry point of the application, which orchestrates the entire process.
*   `config.py`: Configuration file that contains file paths, API keys, source urls.
*   `utils/`:
    *   `logger.py`: Handles logging to the console and a log file.
    *   `errors.py`: Defines custom exceptions used in the project.
    *   `helpers.py`: Contains helper functions like sanitizing filenames.
*   `scrapers/`:
    *   `firecrawl_scraper.py`: Uses Firecrawl API to scrape content from web pages.
*   `processors/`:
    *   `csv_processor.py`: Processes and cleans CSV files.
    *   `markdown_processor.py`: Handles markdown files, like saving and extracting content.
    *   `content_cleaner.py`: Cleans and formats article content.
    *    `openai_rewriter.py`:  Rewrites articles using OpenAI LLM.
    *   `gemini_rewriter.py`: Rewrites articles using Google's Gemini LLM.
    *   `pdf_generator.py`: Generates PDF document from processed articles.

## Data Flow

Here's a step-by-step overview of how data flows through the application:

1.  **Initial Scraping (`main.py`, `scrapers/firecrawl_scraper.py`):**
    *   `main.py` reads the list of source URLs from `config.py`.
    *   It uses `firecrawl_scraper.py` to scrape the initial content from these URLs, saving it as Markdown files in the `output/initial_md_files` directory.
    *   It also extracts article links from the initial markdown content.
    *   Extracted article links are saved as a CSV file named `all_articles.csv` in `output/csv`.
2.  **CSV Cleaning and Selection (`main.py`, `processors/csv_processor.py`):**
    *   `main.py` uses `csv_processor.py` to clean the `all_articles.csv` file by removing irrelevant rows and saving as `cleaned_articles.csv` in `output/csv`.
    *   Then it selects top 5 articles from each source from the cleaned file to `top_articles.csv` in `output/csv`.
3.  **Content Scraping and MD Saving (`main.py`, `processors/markdown_processor.py`):**
    *   `main.py` uses `markdown_processor.py` to scrape the content from the top articles extracted in the previous step using firecrawl, which saves these articles as Markdown files in the `output/content_md_files` directory, these articles contain the full text and all other elements of the article.
4.  **Content Cleaning (`main.py`, `processors/content_cleaner.py`):**
    *   `main.py` uses `content_cleaner.py` to process the Markdown files from `output/content_md_files`, remove unnecessary elements, and stores the cleaned articles into a JSON file named `cleaned_articles.json` in the `output/json` directory.
5.  **Content Rewriting (`main.py`, `processors/openai_rewriter.py` and `processors/gemini_rewriter.py`):**
    *   `main.py` first attempts to use `openai_rewriter.py` to rewrite the content of the articles in `cleaned_articles.json` using OpenAI, it creates `rewritten_articles.json` in the `output/json` folder if successful with a source `openai`.
    *   If OpenAI fails, then the `gemini_rewriter.py` is used to rewrite articles and creates a `rewritten_articles.json` file in `output/json` with a source `gemini`.
    * If there is any problem during both rewritting process the original content will be saved with source as `original`.
6.  **PDF Generation (`main.py`, `processors/pdf_generator.py`):**
    *   `main.py` uses `pdf_generator.py` to read the `rewritten_articles.json`, which is then formatted into a PDF document. The resulting PDF is saved in the `output/pdfs` folder as `clean_rewritten.pdf`.
    *   The first page of the PDF will have the title and subtitle, while the following pages will contain the rewritten articles, grouped by headline, with page numbers.

## Setting up the Project

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/abrarshah-12/News_Crawler.git
    cd News_Crawler
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Create `.env` file:**
    Create a `.env` file in the root of the project folder and add the following:
    ```env
    FIRECRAWL_API_KEY="your_firecrawl_api_key"
    GEMINI_API_KEY="your_gemini_api_key"
    OPENAI_API_KEY="your_openai_api_key"
    ```
    Replace `your_firecrawl_api_key`, `your_gemini_api_key` and `your_openai_api_key` with your actual API keys.
4.  **Add fonts directory**: Create a `fonts` directory and add the `timr45w.ttf` font file to that directory.
5.  **Run the project**:
    ```bash
    python main.py
    ```
## Output Files
After running the project, you will see the following directories and files in the project directory:

- `output/initial_md_files`: This directory will contain the scraped markdown files
- `output/csv`: This directory will contain csv files named `all_articles.csv`, `cleaned_articles.csv`, and `top_articles.csv`.
- `output/content_md_files`: This directory will contain the articles scraped from links present in `top_articles.csv`.
- `output/json`: This directory will contain JSON files named `cleaned_articles.json` and `rewritten_articles.json`.
- `output/pdfs`: This directory will contain a PDF file named `clean_rewritten.pdf` containing the formatted articles.
- `output/logs.txt`: This file will contain the execution logs.

## Error Handling

The project is equipped with comprehensive error handling and logging capabilities:

*   Custom exceptions in `utils/errors.py` are used for specific issues (e.g., Firecrawl errors, processing errors, LLM errors).
*   The `utils/logger.py` module provides logging to both the console and a `logs.txt` file, recording information, warnings, and errors encountered during the process.

## Future Enhancements

*   **More Sources:** Expand the list of source URLs to gather data from more sources.
*   **Advanced Cleaning:** Improve content cleaning to remove more complex patterns and unwanted information.
*   **Better LLM Prompting:** Fine-tune the prompts used with OpenAI and Gemini to achieve more consistent and accurate outputs.
*   **Configuration Flexibility:** Allow more flexible configuration options, such as dynamic source lists, and API keys using configuration files.
*   **User Interface:** Implement a simple web or command-line interface to allow users to easily interact with the application.

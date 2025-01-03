import os
import re
import json
import time
import random
import openai
from utils.logger import log
from config import JSON_DIR
from utils.errors import ProcessingError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Setup OpenAI API
if not OPENAI_API_KEY:
    raise ProcessingError("OpenAI API Key missing")
openai.api_key = OPENAI_API_KEY

PERSONA = """1. Sensationalist Tone
Style: Articles often use eye-catching headlines, sometimes exaggerated, to grab attention.
Purpose: Maximise clicks and engagement by appealing to emotions like curiosity, outrage, or excitement.

2. Audience-Centric Approach
Demographic: Primarily middle-class readers with conservative or right-leaning values.
Focus: Topics that resonate with their audience, including immigration, crime, celebrities, health, and royal family news.

3. Human-Interest Angle
Style: Personal stories, anecdotes, and "real-life" drama are often central to articles.
Purpose: Engage readers by making the news relatable and emotionally compelling.

4. Moral Perspective
Style: Articles often include implicit or explicit judgments, aligning with traditional British values or conservative viewpoints.
Purpose: Reinforce the readers' worldview and create a sense of shared values.

5. Visual & Formatting Emphasis
Style: Heavy use of photos, videos, and bullet points to break down content for easy scanning.
Purpose: Cater to readers who prefer quick, visually engaging content.

6. Provocative Framing
Style: Articles often pose questions or create controversy, e.g., "Is this the end of [X]?" or "Outrage as [Y] happens."
Purpose: Encourage debate and social media sharing.

7. Quick Turnaround
Style: Prioritise speed in covering breaking news, even if it means occasional corrections later.
Purpose: Stay competitive in the fast-paced media landscape.

8. Celebrity and Lifestyle Focus
Style: Blend hard news with soft topics like fashion, relationships, and pop culture.
Purpose: Broaden appeal and maintain interest across a diverse readership.

9. Clickbait Techniques
Style: Use of phrases like "You’ll never guess what happened next" or "What [X] said will shock you."
Purpose: Drive higher engagement and encourage readers to click through.

10. Critical or Alarmist Headlines
Style: Highlight potential risks, scandals, or failures, often with a negative slant.
Purpose: Appeal to readers’ fears and sense of urgency.

The Daily Tuesday editor persona operates with the primary goal of engaging a broad yet specific audience by combining sensationalism, relatability, and visual storytelling with a strong editorial slant."""

def rewrite_articles_with_openai(text, initial_delay=1, max_delay=32):
    """Rewrites text using OpenAI with retry logic and ensures proper structured output."""
    rewritten_text = ""
    delay = initial_delay
    retries = 0
    start_time = time.time()
    prompt = f"""{PERSONA}
    Given this news article content:
    {text}
    Analyze the article content to identify the main news. Then rewrite the main news into a catchy headline and a compelling, engaging article in a Daily Mail style, using UK English. Remove any links, images, and markdown-like formatting.
    Ensure that the rewritten article is broken into paragraphs for readability, and paragraphs should be separated by two newlines `\\n\\n`. The word count should be between 300-400.
    Return the output as a JSON object with keys `headline` and `content`, ensuring that no key or value is left as N/A.
    """

    while retries < 5:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )

            if response.choices and response.choices[0].message.content:
                rewritten_text = response.choices[0].message.content.strip()
                log(f"Raw response from OpenAI: {rewritten_text}")
                # Check if JSON is embedded inside the content field
                if "```json" in rewritten_text:
                    match = re.search(r"```json\n(.*?)\n```", rewritten_text, re.DOTALL)
                    if match:
                        rewritten_text = match.group(1)
                return rewritten_text  # Exit retry loop if successful
            else:
                log(f"OpenAI API returned no text. Retries: {retries}")
                break
        except Exception as e:
            log(f"Error with OpenAI API: {e}. Retries: {retries}")
            if '429' in str(e) or "rate limit" in str(e):
                log(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
                retries += 1
            elif "This model's maximum context length is 16385 tokens" in str(e).lower():
                log(f"OpenAI context length exceeded, skipping this article.")
                return "BLOCKED_CONTENT"
            else:
                log(f"Unexpected OpenAI API error, not retrying.")
                break
        finally:
            time.sleep(random.uniform(0.5, 1.5))
    return rewritten_text or '{"headline": "N/A", "content": "N/A"}'


def process_and_save_rewritten_articles(input_json_path, output_json_path):
    """Reads JSON, rewrites articles with OpenAI, and ensures properly structured output."""
    log(f"Starting to process and save rewritten articles from {input_json_path}")
    try:
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)
        rewritten_articles = []

        for article_data in articles:
            content = article_data.get("content", "")
            url = article_data.get("url", "")
            if content:
                articles = re.split(r'(?=\n#\s)', content)
                for article_content in articles:
                    article_content = article_content.strip()
                    if article_content:
                        rewritten_output = rewrite_articles_with_openai(article_content)
                        try:
                            rewritten_dict = json.loads(rewritten_output)
                            headline = rewritten_dict.get("headline", "N/A")
                            content = rewritten_dict.get("content", "N/A")
                            rewritten_articles.append({
                                "headline": headline,
                                "content": content,
                                "source": "openai",
                                "url": url
                            })
                        except json.JSONDecodeError:
                            log(f"Invalid JSON from OpenAI, using fallback structured data.")
                            rewritten_articles.append({
                                "headline": "N/A",
                                "content": rewritten_output if rewritten_output else "N/A",
                                "source": "openai",
                                "url": url
                            })
            else:
                log(f"Skipping row due to missing content: {article_data}")

        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(rewritten_articles, json_file, indent=4)
        log(f"Saved rewritten articles to {output_json_path}")
    except Exception as e:
        raise ProcessingError(f"Error during rewriting articles by OpenAI: {e}")


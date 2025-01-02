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
    """Rewrites text using OpenAI with retry logic and throttling."""
    rewritten_text = ""
    delay = initial_delay
    retries = 0
    start_time = time.time()
    prompt = f"""{PERSONA}
Given this news article content:
{text}
Rewrite the main news into a catchy headline and a compelling, engaging article in a Daily Mail style, using UK English. Remove any links, images, and markdown-like formatting. Do not use bullet points in the rewritten article, just a coherent and attractive narrative. The word count should be between 300-400.
Return the output as a JSON object strictly formatted as:
{{
    \"headline\": \"<Your headline here>\",
    \"content\": \"<Your content here>\"
}}
Do not include any additional text or formatting outside this structure.
"""

    while retries < 5:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if response.choices and response.choices[0].message.content:
                rewritten_text = response.choices[0].message.content.strip()
                log(f"Raw response from OpenAI: {rewritten_text}")
                end_time = time.time()
                time_taken = end_time - start_time
                log(f"OpenAI API returned text. Time taken: {time_taken:.2f}s. Retries: {retries}")
                break  # Exit the retry loop if successful
            else:
                log(f"OpenAI API returned no text. Retries: {retries}")
                break
        except Exception as e:
            log(f"Error with OpenAI API: {e}. Retries: {retries}")
            if '429' in str(e) or "rate limit" in str(e):
                log(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)  # exponential backoff
                retries += 1
            elif "maximum context length" in str(e).lower():
                log(f"OpenAI context length exceeded, skipping this article. {e}")
                return "BLOCKED_CONTENT"
            else:
                log(f"Unexpected OpenAI API error, not retrying. {e}")
                break
    return rewritten_text

def process_and_save_rewritten_articles(input_json_path, output_json_path):
    """Reads JSON, rewrites articles with OpenAI, saves to a new JSON file."""
    log(f"Starting to process and save rewritten articles from {input_json_path}")
    try:
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            articles = json.load(json_file)
        rewritten_articles = []

        for article_data in articles:
            content = article_data.get("content", "")
            if content:
                # Split the content into articles based on headings or custom logic
                articles = re.split(r'(?=\n#\s)', content)
                for article_content in articles:
                    article_content = article_content.strip()
                    if article_content:
                        rewritten_output = rewrite_articles_with_openai(article_content)
                        if rewritten_output and rewritten_output != "BLOCKED_CONTENT":
                            try:
                                rewritten_dict = json.loads(rewritten_output)
                                rewritten_articles.append({
                                    "headline": rewritten_dict.get("headline", ""),
                                    "content": rewritten_dict.get("content", ""),
                                    "source": "openai"
                                })
                            except json.JSONDecodeError as e:
                                log(f"JSON parsing error: {e}. Attempting to clean response.")
                                try:
                                    cleaned_output = re.search(r'\{.*\}', rewritten_output, re.DOTALL).group(0)
                                    rewritten_dict = json.loads(cleaned_output)
                                    rewritten_articles.append({
                                        "headline": rewritten_dict.get("headline", ""),
                                        "content": rewritten_dict.get("content", ""),
                                        "source": "openai"
                                    })
                                except Exception as inner_e:
                                    log(f"Failed to clean and parse response: {inner_e}")
                                    rewritten_articles.append({
                                        "content": rewritten_output,
                                        "source": "openai"
                                    })
                        else:
                            log(f"Skipping article due to rewrite issues: {article_content}")
                            rewritten_articles.append({
                                "content": article_content,
                                "source": "original"
                            })
            else:
                log(f"Skipping article due to missing content: {article_data}")

        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(rewritten_articles, json_file, indent=4)
            log(f"Saved rewritten articles to {output_json_path}")
        log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
        raise ProcessingError(f"Error during article processing: {e}")

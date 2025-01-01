# processors/gemini_rewriter.py
import os
import re
import json
import time
import random
import google.generativeai as genai
from utils.logger import log
from config import JSON_DIR, GEMINI_API_KEY
from utils.errors import GeminiError, ProcessingError


# Setup Gemini API
if not GEMINI_API_KEY:
  raise GeminiError("Gemini API Key missing")
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = 'gemini-pro'
MODEL = genai.GenerativeModel(MODEL_NAME)

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

The Daily Mail editor persona operates with the primary goal of engaging a broad yet specific audience by combining sensationalism, relatability, and visual storytelling with a strong editorial slant."""

def rewrite_articles_with_gemini(text, initial_delay=1, max_delay=16):
    """Rewrites text using Gemini with retry logic and throttling."""
    rewritten_text = ""
    delay = initial_delay
    retries = 0
    start_time = time.time()
    prompt = f"""{PERSONA}
            Given this news article content:
            {text}
             Analyze the article content to identify the main news. Then rewrite the main news into a catchy headline and a compelling, engaging article in a Daily Mail style. Remove any links, images, and markdown-like formatting. Do not use bullet points in the rewritten article, just a coherent and attractive narrative. The word count should be between 300-400.
             Return the output as a JSON object with keys `headline` and `content`, ensure that there is no key or value as N/A.
            """

    while True:
        try:
            response = MODEL.generate_content(prompt)
            if response.text:
                rewritten_text = response.text.strip()
                end_time = time.time()
                time_taken = end_time - start_time
                log(f"Gemini API returned text. Time taken: {time_taken:.2f}s. Retries: {retries}")
                break  # Exit the retry loop if successful
            else:
                log(f"Gemini API returned no text. Retries: {retries}")
                break
        except Exception as e:
            log(f"Error with Gemini API: {e}. Retries: {retries}")
            if '429' in str(e):
                log(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)  # exponential backoff
                retries += 1
            elif "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, but none were returned." not in str(e):
                log(f"Gemini API blocked content: {e}. Retries: {retries}")
                retries += 1
                if retries > 2:
                  log(f"Gemini API blocked content even with new prompt, skipping this article {e}")
                  return "BLOCKED_CONTENT"
                else:
                  prompt = f"""{PERSONA}
                    Given this news article content:
                    {text}
                     Rewrite this news article by having an eye catching headline and creating engaging content in the style of the Daily Mail, make sure that it is between 300 and 500 words.
                     Remove any links, images, and markdown-like formatting. Do not use bullet points. The output should be in a JSON object with keys `headline` and `content`.
                    """
                  time.sleep(delay)
                  delay = min(delay * 2, max_delay)
            else:
                log(f"Unexpected Gemini API error, not retrying. {e}")
                break
        finally:
            # Add random delay to prevent rate limiting
            time.sleep(random.uniform(0.5, 1.5))
    return rewritten_text



def process_and_save_rewritten_articles(input_json_path, output_json_path):
    """Reads JSON, rewrites articles with Gemini, saves to a new JSON file."""
    log(f"Starting to process and save rewritten articles from {input_json_path}")
    try:
      with open(input_json_path, "r", encoding="utf-8") as json_file:
          articles = json.load(json_file)
      rewritten_articles = []

      for article_data in articles:
          content = article_data.get("content", "")
          if content:
              # Split the content into articles based on the presence of a heading
              articles = re.split(r'(?=\n#\s)', content)
              for article_content in articles:
                  article_content = article_content.strip()
                  if article_content:
                      rewritten_output = rewrite_articles_with_gemini(article_content)
                      if rewritten_output and rewritten_output != "BLOCKED_CONTENT":
                          try:
                              rewritten_dict = json.loads(rewritten_output)
                              rewritten_articles.append({
                                 "headline": rewritten_dict.get("headline",""),
                                "content": rewritten_dict.get("content",""),
                                  "source": "gemini"
                                 })
                          except json.JSONDecodeError:
                               log(f"Gemini API returned text but the JSON is invalid, saving original content with source as original {rewritten_output}")
                               rewritten_articles.append({
                                 "content": rewritten_output,
                                  "source": "gemini"
                            })

                      else:
                          log(f"Could not rewrite content of the article due to Gemini API issues or blocked content, saving original content with source as original: {article_content}")
                          rewritten_articles.append({
                            "content": article_content,
                              "source": "original"
                           })
          else:
              log(f"Skipping row due to missing content: {article_data}")

      with open(output_json_path, "w", encoding="utf-8") as json_file:
          json.dump(rewritten_articles, json_file, indent=4)
          log(f"Saved rewritten articles to {output_json_path}")
      log(f"Finished processing all articles from {input_json_path}")
    except Exception as e:
       raise ProcessingError(f"Error during rewriting the article by gemini: {e}")
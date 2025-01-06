import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import psycopg2
from config import  EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import log, log_exception
import datetime
import re

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
      for subscriber in subscribers:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = subscriber
        msg["Subject"] = "Daily Crime News Report"

        # Extract username from email
        username = subscriber.split("@")[0]
         # Generate personalized HTML content
        html_body = f"""
                <html>
                <head>
                <style>
                    body {{font-family: Arial, sans-serif; color: #333; line-height: 1.6;}}
                    h1 {{color: #0056b3;}}
                    p {{margin-bottom: 15px;}}
                    .footer {{margin-top: 20px; font-size: 0.8em; color: #777;}}
                </style>
                </head>
                 <body>
                    <h1>Hello, {username}!</h1>
                    <p>Here is your daily crime news report for {datetime.datetime.now().strftime("%B %d, %Y")}.</p>
                    <div class="footer">
                    <p>This email was sent to you as a subscriber of Daily Crime News Report.</p>
                    </div>
                 </body>
                </html>
            """

        msg.attach(MIMEText(html_body, "html"))

        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(pdf_attachment)
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            log(f"Email sent successfully to {subscriber}")
    except Exception as e:
        log_exception(e, "Error sending email")
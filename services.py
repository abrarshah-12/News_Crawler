import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import psycopg2
from config import  EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_FROM, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import log, log_exception
import datetime

def load_subscribers():
    """Loads subscribers and their names from the database."""
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
            cur.execute("SELECT name, email FROM subscribers")
            subscriber_data = cur.fetchall()
            subscribers = [{"name": row[0], "email": row[1]} for row in subscriber_data]
    except Exception as e:
        log_exception(e, "Error fetching subscribers from the database.")
        subscribers = []
    finally:
        if conn:
            conn.close()
    return subscribers


def send_email(pdf_path, subscribers):
    """Sends the generated PDF to subscribers with a personalized email."""
    if not subscribers:
        log("No subscribers, email sending will be skipped", level=40)
        return

    try:
        for subscriber in subscribers:
            name = subscriber["name"]
            email = subscriber["email"]

            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"] = email
            msg["Subject"] = f"Daily News Report - {datetime.datetime.now().strftime('%B %d, %Y')}"

            # Generate personalized HTML content
            html_body = f"""
                <html>
                <head>
                <style>
                    body {{font-family: Arial, sans-serif; color: #333; line-height: 1.8;}}
                    h1 {{color: #0056b3; margin-bottom: 10px;}}
                    p {{margin-bottom: 15px;}}
                    .footer {{margin-top: 20px; font-size: 0.8em; color: #777;}}
                    .highlight {{color: #d9534f; font-weight: bold;}}
                    .cta-button {{
                        display: inline-block;
                        margin-top: 20px;
                        padding: 10px 20px;
                        color: white;
                        background-color: #28a745;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                    }}
                    .cta-button:hover {{background-color: #218838;}}
                </style>
                </head>
                <body>
                    <h1>Dear {name},</h1>
                    <p>I hope this message finds you well.</p>
                    <p>Please find attached your <span class="highlight">Daily News Report</span> for {datetime.datetime.now().strftime('%B %d, %Y')}. 
                    This report contains all the important updates and headlines for your review.</p>
                    <p>Thank you for staying informed. Your dedication to staying updated inspires us to do our best every day.</p>
                    <a href="https://example.com/unsubscribe" class="cta-button">Unsubscribe</a>
                    <div class="footer">
                        <p>Daily News Report Team</p>
                        <p>This email was sent to you as a subscriber of Daily News Report.</p>
                    </div>
                </body>
                </html>
            """

            msg.attach(MIMEText(html_body, "html"))

            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=os.path.basename(pdf_path)
                )
                msg.attach(pdf_attachment)

            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
                log(f"Email sent successfully to {email}")
    except Exception as e:
        log_exception(e, "Error sending email")
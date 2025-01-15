import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, PDF_DIR
from utils.logger import log
from utils.errors import FileProcessingError
import os
import glob
from datetime import datetime
from typing import List, Dict


app = FastAPI()

# Configure templates and static files
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

template_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(template_dir, "templates"))

# Database connection function
def get_db_connection():
    """Establishes a database connection and returns the connection object."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        log(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def create_subscribers_table():
    """Creates the subscribers table if it doesn't exist."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL
                );
            """)
            conn.commit()
            log("Table subscribers has been created or updated.")
    except Exception as e:
        log(f"Error creating subscriber table: {e}")
        raise FileProcessingError(f"Error creating subscriber table: {e}")
    finally:
        if conn:
            conn.close()

# Ensure the table exists when the app starts
create_subscribers_table()

# Pydantic model for subscriber
class Subscriber(BaseModel):
    name: str
    email: str

@app.get("/", response_class=HTMLResponse)
async def subscribe_form(request: Request):
    """Displays the subscription form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/subscribe", response_class=HTMLResponse)
async def subscribe(request: Request, name: str = Form(...), email: str = Form(...)):
    """Handles the subscription request."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM subscribers WHERE email = %s", (email,))
            existing_subscriber = cur.fetchone()
            if existing_subscriber:
                return templates.TemplateResponse(
                    "already_subscribed.html", {"request": request, "email": email, "name":name}
                )
            else:
                cur.execute(
                    "INSERT INTO subscribers (name, email) VALUES (%s, %s)",
                    (name, email)
                )
                conn.commit()
                log(f"New subscriber: {name} <{email}>")
                return templates.TemplateResponse(
                    "success.html", {"request": request, "name": name, "email": email}
                )
    except Exception as e:
         log(f"Subscription database error: {e}")
         raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
         if conn:
            conn.close()

def get_pdf_reports() -> List[Dict]:
    """Retrieves information about available PDF reports."""
    reports = []
    if os.path.exists(PDF_DIR):
        files_with_times = []
        for filename in glob.glob(os.path.join(PDF_DIR, "*.pdf")):
            try:
                creation_time = os.path.getctime(filename)
                files_with_times.append((filename, creation_time))
            except Exception as e:
               log(f"Error getting pdf report information for {filename}: {e}", level = 40)

        # Sort by creation time in descending order
        files_with_times.sort(key=lambda item: item[1], reverse = True)
        
        # Show only top 5 reports
        for filename, creation_time in files_with_times[:5]:
             date = datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %I:%M %p")
             reports.append({"name": os.path.basename(filename), "path": filename, "date": date})

    return reports

@app.get("/reports", response_class=HTMLResponse)
async def list_reports(request: Request):
  """Displays a list of available PDF reports with download links."""
  reports = get_pdf_reports()
  return templates.TemplateResponse("reports.html", {"request": request, "reports": reports})

@app.get("/download/{filename}")
async def download_report(filename: str):
    """Downloads a specific PDF report."""
    pdf_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=filename, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
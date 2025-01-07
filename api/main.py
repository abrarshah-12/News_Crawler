import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import log
from utils.errors import FileProcessingError

app = FastAPI()

# Configure templates and static files
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

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
                    "already_subscribed.html", {"request": request, "email": email}
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

# Main entry point for running the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
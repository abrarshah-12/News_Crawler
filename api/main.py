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
app.mount("/static", StaticFiles(directory="../static"), name="static")
templates = Jinja2Templates(directory="../templates")


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
                email VARCHAR(255) UNIQUE NOT NULL
            );
        """)
        conn.commit()
        log("Table subscribers has been created")

    except Exception as e:
      log(f"Error creating subscriber table: {e}")
      raise FileProcessingError(f"Error creating subscriber table: {e}")
    finally:
      if conn:
        conn.close()


create_subscribers_table()

class Subscriber(BaseModel):
    email: str


@app.get("/", response_class=HTMLResponse)
async def subscribe_form(request: Request):
    """Displays the subscription form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/subscribe", response_class=HTMLResponse)
async def subscribe(request: Request, email: str = Form(...)):
    """Handles the subscription request."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM subscribers WHERE email = %s", (email,))
            existing_subscriber = cur.fetchone()
            if existing_subscriber:
                return templates.TemplateResponse("already_subscribed.html", {"request": request, "email": email})
            else:
                cur.execute("INSERT INTO subscribers (email) VALUES (%s)", (email,))
                conn.commit()
                log(f"New subscriber: {email}")
                return templates.TemplateResponse("success.html", {"request": request, "email": email})
    except Exception as e:
         log(f"Subscription database error: {e}")
         raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
      if conn:
        conn.close()
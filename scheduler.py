import schedule
import time
from threading import Thread
from main import main as run_workflow
from web_app import app
from utils.logger import log
from uvicorn import Config, Server

# Fixed time for daily execution
EXECUTION_TIME = "16:11"

def execute_workflow():
    """Executes the workflow."""
    try:
        log("Executing scheduled workflow.")
        run_workflow()
    except Exception as e:
        log(f"Error during workflow execution: {e}")

def start_web_app():
    """Starts the FastAPI web app."""
    try:
        log("Starting the web app.")
        config = Config(app=app, host="127.0.0.1", port=8000, log_level="info")
        server = Server(config)
        server.run()
    except Exception as e:
        log(f"Error starting the web app: {e}")

def schedule_task():
    """Schedules the daily workflow execution."""
    log(f"Scheduling the workflow to run daily at {EXECUTION_TIME}.")
    schedule.every().day.at(EXECUTION_TIME).do(execute_workflow)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    try:
        # Start the web app in a separate thread
        web_app_thread = Thread(target=start_web_app, daemon=True)
        web_app_thread.start()
        
        # Start the scheduler
        schedule_task()
    except KeyboardInterrupt:
        log("Shutting down the application.")
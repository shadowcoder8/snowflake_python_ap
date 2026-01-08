
import multiprocessing
import os

# Gunicorn Configuration

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 5

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"
errorlog = "-"

# Process Name
proc_name = "snowflake_data_api"

# Reload (Development only)
reload = False

import os

# Tune via env (Helm: values.env.GUNICORN_WORKERS / GUNICORN_THREADS)
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
bind = "0.0.0.0:5000"
worker_class = "gthread"
timeout = 120

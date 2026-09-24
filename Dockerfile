# Use official Python image
FROM python:3.11

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create non-root user (UID/GID 10001 - matches K8s fsGroup/runAsUser)
# and a writable /data and /tmp. SQLite DB, encryption key and ledger
# live under /data (mounted volume in K8s / docker).
RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /data /tmp \
    && chown -R appuser:appuser /data /tmp \
    && chmod 770 /data

# Copy app
COPY . .
RUN chmod +x /app/entrypoint.sh
# Expose port
EXPOSE 5000

# Run as non-root (Kubernetes best practice)
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]

# Run app
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]


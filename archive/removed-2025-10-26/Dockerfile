FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal). SQLite is built-in so no DB client required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/requirements.txt gunicorn

# Copy app source
COPY . /app

ENV PORT=5000
EXPOSE 5000

# Run via gunicorn using the application factory in app.create_app
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:create_app()"]

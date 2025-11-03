# Use official Python slim image
FROM python:3.10-slim

WORKDIR /app

# Install system deps if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Use gunicorn in prod; bind to 0.0.0.0:5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app", "--workers", "2", "--threads", "4"]

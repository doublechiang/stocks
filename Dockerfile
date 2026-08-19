FROM python:3.11-slim

# Prevent Python from writing pyc files & enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Initialize DB tables
RUN python init_db.py

# Cloud Run injects $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Run Streamlit listening on 0.0.0.0 and $PORT
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false --server.enableWebsocketCompression=false --server.headless=true --browser.gatherUsageStats=false

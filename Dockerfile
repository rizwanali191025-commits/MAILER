# MailPilot SaaS — container image.
#   docker build -t mailpilot .
#   docker run -p 5001:5001 mailpilot
# Then open http://localhost:5001
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Persist the SQLite database outside the image if you mount a volume at /data
ENV SAAS_DATABASE=/data/saas.db \
    PORT=5001
RUN mkdir -p /data

EXPOSE 5001

# Serve on all interfaces so the published port is reachable from the host.
CMD ["python", "-c", "import os; from saas.app import create_app; create_app().run(host='0.0.0.0', port=int(os.environ.get('PORT','5001')))"]

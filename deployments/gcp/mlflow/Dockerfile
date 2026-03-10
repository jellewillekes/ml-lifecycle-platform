FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
  "mlflow==2.22.4" \
  "psycopg2-binary==2.9.10" \
  "google-cloud-storage==3.4.1"

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5000
ENTRYPOINT ["/start.sh"]

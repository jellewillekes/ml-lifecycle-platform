FROM python:3.11-slim

# Keep runtime small but functional: curl for healthchecks/debugging.
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Pin MLflow to a minor line for stability (adjust if you want a different minor).
# psycopg2-binary: Postgres backend store
# boto3: S3/MinIO artifacts
RUN pip install --no-cache-dir \
  "mlflow==2.14.*" \
  psycopg2-binary \
  boto3

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5000
ENTRYPOINT ["/start.sh"]

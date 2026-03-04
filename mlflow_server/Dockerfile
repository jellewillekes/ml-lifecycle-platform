FROM python:3.11-slim

# Keep the runtime small. curl is used for health checks.
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Pin MLflow to a stable minor line.
# psycopg2-binary is for the Postgres backend store.
# boto3 is for S3/MinIO artifacts.
RUN pip install --no-cache-dir \
  "mlflow==2.14.*" \
  psycopg2-binary \
  boto3

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5000
ENTRYPOINT ["/start.sh"]

"""Grafana webhook -> Cloud Logging structured entries.

Grafana managed-alert webhooks POST JSON to this service. We verify a shared
bearer token, fan each alert out to stdout as a structured JSON log line, and
return 204. Cloud Run captures stdout into Cloud Logging; a log-based metric
counts the entries and a Cloud Monitoring alert policy routes the email.
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 1 * 1024 * 1024


def emit(entry: dict) -> None:
    sys.stdout.write(json.dumps(entry, separators=(",", ":")) + "\n")
    sys.stdout.flush()


class Handler(BaseHTTPRequestHandler):
    expected_auth: str = ""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def _reply(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._reply(HTTPStatus.OK)

    def do_POST(self) -> None:  # noqa: N802
        auth = self.headers.get("Authorization", "")
        if not hmac.compare_digest(auth, self.expected_auth):
            self._reply(HTTPStatus.UNAUTHORIZED)
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._reply(HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._reply(HTTPStatus.BAD_REQUEST)
            return

        alerts = payload.get("alerts") or []
        for alert in alerts:
            labels = alert.get("labels") or {}
            status = alert.get("status", "unknown")
            emit(
                {
                    "severity": "WARNING" if status == "firing" else "NOTICE",
                    "message": "grafana_alert",
                    "alertname": labels.get("alertname"),
                    "status": status,
                    "labels": labels,
                    "annotations": alert.get("annotations") or {},
                    "startsAt": alert.get("startsAt"),
                    "endsAt": alert.get("endsAt"),
                    "fingerprint": alert.get("fingerprint"),
                    "generatorURL": alert.get("generatorURL"),
                }
            )

        self._reply(HTTPStatus.NO_CONTENT)


def main() -> None:
    Handler.expected_auth = f"Bearer {os.environ['ALERT_ROUTER_TOKEN']}"
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()

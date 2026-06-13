import json
import logging

from .middleware import get_request_id


class JSONFormatter(logging.Formatter):
    """Minimal structured logger that attaches the current request id."""

    def format(self, record):
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

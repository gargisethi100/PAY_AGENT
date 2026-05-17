from __future__ import annotations

import logging

from paygent.policy import redact_sensitive


def get_logger(name: str = "paygent") -> logging.Logger:
    return logging.getLogger(name)


def safe_log(logger: logging.Logger, level: int, message: str, **fields) -> None:
    logger.log(level, message, extra={"paygent_fields": redact_sensitive(fields)})

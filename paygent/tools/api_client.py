from __future__ import annotations

import logging
from typing import Any

import httpx

from paygent.config import API_BASE_URL, HTTP_TIMEOUT_SECONDS
from paygent.logging_utils import safe_log
from paygent.state import ApiResult


class PaymentApiClient:
    def __init__(self, base_url: str = API_BASE_URL, timeout: float = HTTP_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = logging.getLogger("paygent.api")

    def lookup_account(self, account_id: str) -> ApiResult:
        payload = {"account_id": account_id}
        return self._post_with_retry("/api/lookup-account", payload)

    def process_payment(self, payload: dict[str, Any]) -> ApiResult:
        return self._post_with_retry("/api/process-payment", payload)

    def _post_with_retry(self, path: str, payload: dict[str, Any]) -> ApiResult:
        last_result = None
        for attempt in range(2):
            last_result = self._post(path, payload)
            if not last_result.retryable:
                return last_result
            safe_log(self.logger, logging.WARNING, "Transient API failure", path=path, attempt=attempt + 1)
        return last_result or ApiResult(ok=False, error_code="api_unavailable", retryable=True)

    def _post(self, path: str, payload: dict[str, Any]) -> ApiResult:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}{path}", json=payload)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError):
            return ApiResult(ok=False, error_code="api_unavailable", retryable=True)

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code in {500, 502, 503, 504}:
            return ApiResult(ok=False, data=data, error_code="api_unavailable", retryable=True)
        if response.is_success:
            return ApiResult(ok=True, data=data)
        return ApiResult(
            ok=False,
            data=data,
            error_code=data.get("error_code") or "api_error",
            message=data.get("message"),
        )

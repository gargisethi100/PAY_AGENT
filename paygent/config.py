from datetime import date
from pathlib import Path

from dotenv import load_dotenv


API_BASE_URL = "https://se-payment-verification-api.service.external.usea2.aws.prodigaltech.com"
HTTP_TIMEOUT_SECONDS = 8.0
ACCOUNT_LOOKUP_ATTEMPT_LIMIT = 3
VERIFICATION_ATTEMPT_LIMIT = 3
NAME_MISMATCH_ATTEMPT_LIMIT = 5
PAYMENT_ATTEMPT_LIMIT = 3


def load_env_file(path: str | Path | None = None, *, override: bool = False) -> bool:
    env_path = Path(path) if path is not None else Path.cwd() / ".env"
    return load_dotenv(dotenv_path=env_path, override=override)


def default_today() -> date:
    return date.today()

from datetime import datetime, timedelta, timezone
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%fZ")


def add_seconds_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


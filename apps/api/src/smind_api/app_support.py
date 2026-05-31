"""FastAPI-free support logic for app assembly (F2-03).

The pure functions here (exception->status mapping, DB/vec health probes,
startup self-check) are isolated from FastAPI so they can be unit-tested
without the web stack installed. ``main.py`` wires them into the app.

Anti-pattern guard (AP §7.2 ⛔4): the exception mapping prefers a structured
``SmindError.code`` branch; the substring heuristics on plain ``ValueError``
messages are a *fallback* (prefix/substring, never exact full-string equality)
so minor wording drift does not silently fall back to 500.
"""

import contextlib

from smind_common.errors import SmindError
from storage_sqlite.engine import CoreSQLiteEngine
from storage_sqlite.migrations.runner import apply_core_migrations
from vector_sqlite_vec import VecSQLiteEngine, apply_vec_schema


# --- Exception -> HTTP status mapping (P2-03) --------------------------------

# SmindError.code -> status. Codes are structured and stable.
_CODE_STATUS = {
    "AUTH_INVALID_CREDENTIALS": 401,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
}

# Fallback substring heuristics for plain ValueError messages (the only signal
# the current service layer emits). Order matters: most specific first.
_MESSAGE_RULES = (
    ("invalid credentials", 401),
    ("not found", 404),
    ("conflict", 409),
    ("already", 409),
)


def is_business_exception(exc: BaseException) -> bool:
    """True if ``exc`` should be mapped to a 4xx instead of a real 500.

    Business signals in this codebase are ``SmindError`` (structured) and
    plain ``ValueError`` (service-layer validation). Other exception types are
    programming errors and must surface as 500.
    """
    return isinstance(exc, (SmindError, ValueError))


def map_exception_to_status(exc: BaseException) -> int:
    """Map a business exception to a 4xx status code.

    - invalid credentials / auth -> 401
    - not found -> 404
    - conflict (PK / state) -> 409
    - any other recognised business error -> 400

    Raises ``TypeError`` for non-business (programming) exceptions so the caller
    lets them become a real 500.
    """
    if not is_business_exception(exc):
        raise TypeError(
            f"{type(exc).__name__} is not a business exception; let it 500"
        )

    code = getattr(exc, "code", None)
    if code in _CODE_STATUS:
        return _CODE_STATUS[code]

    message = str(exc).lower()
    for needle, status in _MESSAGE_RULES:
        if needle in message:
            return status

    # Recognised business error but unclassified -> 400 (never silently 500).
    return 400


def error_code(exc: BaseException) -> str:
    """Machine-readable code for the error payload."""
    return getattr(exc, "code", type(exc).__name__)


# --- Startup migrations + self-check (P2-01) ---------------------------------

def run_startup_checks(core_db_path: str, vec_db_path: str) -> None:
    """Apply migrations and self-check core+vec connectivity (fail-loud).

    Raises on any failure so the application refuses to boot against an
    unusable database instead of starting silently broken.
    """
    with contextlib.closing(CoreSQLiteEngine(core_db_path).connect()) as core:
        apply_core_migrations(core)
        core.execute("SELECT 1").fetchone()
    with contextlib.closing(VecSQLiteEngine(vec_db_path).connect()) as vec:
        apply_vec_schema(vec)
        vec.execute("SELECT 1").fetchone()


# --- /healthz probes (P2-04) ------------------------------------------------

def probe_core(core_db_path: str) -> None:
    """Lightweight core probe; raises on failure. Connection always closed."""
    with contextlib.closing(CoreSQLiteEngine(core_db_path).connect()) as conn:
        conn.execute("SELECT 1").fetchone()


def probe_vec(vec_db_path: str) -> None:
    """Lightweight vec probe (vec table existence); raises on failure."""
    with contextlib.closing(VecSQLiteEngine(vec_db_path).connect()) as conn:
        # Touch the embedding index table so a missing schema surfaces as
        # degraded. ``chunk_embedding_index`` is the vec0 (or fallback) table
        # created by apply_vec_schema.
        conn.execute("SELECT 1 FROM chunk_embedding_index LIMIT 1").fetchall()


def health_report(core_db_path: str, vec_db_path: str) -> tuple[int, dict]:
    """Probe core+vec and return ``(status_code, body)``.

    All-ok -> ``(200, {"status": "ok", "core": "ok", "vec": "ok"})``.
    Any failure -> ``(503, {"status": "degraded", ...})`` with a machine
    readable ``reason`` (never a silent ok).
    """
    body: dict = {"status": "ok"}
    healthy = True

    try:
        probe_core(core_db_path)
        body["core"] = "ok"
    except Exception as exc:  # noqa: BLE001 - any failure -> degraded
        healthy = False
        body["core"] = f"error: {exc}"

    try:
        probe_vec(vec_db_path)
        body["vec"] = "ok"
    except Exception as exc:  # noqa: BLE001
        healthy = False
        body["vec"] = f"error: {exc}"

    if healthy:
        return 200, body

    body["status"] = "degraded"
    body["reason"] = "; ".join(
        f"{k}={body[k]}" for k in ("core", "vec") if body.get(k) != "ok"
    )
    return 503, body

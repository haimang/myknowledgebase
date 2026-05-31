"""FF-F2-T05 wiring rigor: the REAL create_app() registers business-exception
handlers (G-CR5-05).

先红后绿 ([Q7]): pre-fix main.py had no exception handlers at all, so the
handler keys are absent (RED). After F2-03 registers ValueError + SmindError
handlers, the keys are present (GREEN). Unlike test_error_mapping.py (which
exercises endpoints), this directly asserts the wiring on the production app
factory, so it is genuinely red on the pre-fix code.
"""

import pytest

pytest.importorskip("fastapi")

from smind_api.main import create_app
from smind_common.errors import SmindError


def test_real_create_app_registers_business_exception_handlers() -> None:
    app = create_app()
    handlers = app.exception_handlers
    assert ValueError in handlers, "create_app must register a ValueError handler"
    assert SmindError in handlers, "create_app must register a SmindError handler"

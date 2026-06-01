"""L6/L3: SSRF 守卫 + api key prefix 收窄.

先红后绿: pre-fix fetch_url/fetch_api 对内网/非 http url 无校验; key_prefix=raw[:12]。
"""

import cleaners_universal.service as csvc
import providers_dedicated.service as psvc
import pytest
from auth import AuthService, generate_api_key
from cleaners_universal import UrlFetchError
from providers_dedicated import ApiRequestError
from smind_common.net import UnsafeUrlError, assert_safe_url
from tests.fixtures.sqlite_kernel import make_kernel_dbs

_UNSAFE = [
    "http://127.0.0.1/x",
    "http://localhost/x",
    "http://10.0.0.5/x",
    "http://192.168.1.1/x",
    "http://169.254.169.254/latest/meta-data",  # 云元数据
    "http://[::1]/x",
    "file:///etc/passwd",
    "ftp://host/x",
    "gopher://host/x",
]


@pytest.mark.parametrize("url", _UNSAFE)
def test_assert_safe_url_rejects(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_url(url)


def test_assert_safe_url_allows_public() -> None:
    assert_safe_url("https://chinatax.gov.cn/policy")
    assert_safe_url("http://example.com/a")


@pytest.mark.parametrize("url", _UNSAFE)
def test_fetch_url_rejects_ssrf(url: str) -> None:
    with pytest.raises(UrlFetchError):
        csvc.fetch_url(url)


@pytest.mark.parametrize("url", _UNSAFE[:5])
def test_fetch_api_rejects_ssrf(url: str) -> None:
    with pytest.raises(ApiRequestError):
        psvc.fetch_api(url)


def test_key_prefix_is_short_not_full_secret() -> None:
    core, _ = make_kernel_dbs()
    core.execute("INSERT INTO teams (id, slug, name) VALUES ('t','t','t')")
    core.commit()
    out = AuthService(core).create_api_key(team_id="t", name="k")
    prefix = core.execute("SELECT key_prefix FROM api_keys").fetchone()["key_prefix"]
    assert prefix == out["api_key"][:8]
    assert len(prefix) == 8  # sm_ + 5 字符, 远短于完整 key
    assert prefix != out["api_key"]

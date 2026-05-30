from functools import lru_cache

from .settings import Settings


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings()


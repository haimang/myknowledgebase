from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    data_dir: str = "data"
    core_db_path: str = "data/db/core.db"
    vec_db_path: str = "data/db/vec.db"
    object_store_dir: str = "data/objects"
    model_config = SettingsConfigDict(env_prefix="SMIND_", extra="ignore")

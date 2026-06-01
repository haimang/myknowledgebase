from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    data_dir: str = "data"
    core_db_path: str = "data/db/core.db"
    vec_db_path: str = "data/db/vec.db"
    object_store_dir: str = "data/objects"

    # RW-A / RWA-03: provider 路由选型 (Q-RW-1/2)。默认 mock/local-hash/bruteforce →
    # 零配置即离线可跑、不打外网 (TR-5)。真实 provider (mlx/厂商) 延后至 provider charter。
    llm_provider: str = "mock"
    embedder_provider: str = "local-hash"
    vector_index: str = "bruteforce"

    # 真实模型/密钥字段 (Q-RW-2/7): 本轮预留, 默认 None (备而不填; key 不进仓/日志)。
    llm_model: str | None = None
    embedder_model: str | None = None
    llm_api_key: str | None = None

    # RWA-03: 支持从 .env 注入 (git-ignored)。env 前缀 SMIND_; 未知字段忽略。
    model_config = SettingsConfigDict(
        env_prefix="SMIND_", extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

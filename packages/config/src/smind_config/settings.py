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

    # RW-B / RWB-04..06: 语义链模式开关。默认 "rule" (规则化, 零回归);
    # "llm" → structurize/summary/clean 走 prompt→render→LLM(provider 由 llm_provider 定)。
    semantic_mode: str = "rule"
    prompts_dir: str = "prompts"
    # mock provider 的预置响应文件 (real-wiring 路由 mock 侧用; 真实 provider 时忽略)。
    mock_llm_responses_path: str | None = None

    # RWA-03: 支持从 .env 注入 (git-ignored)。env 前缀 SMIND_; 未知字段忽略。
    model_config = SettingsConfigDict(
        env_prefix="SMIND_", extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

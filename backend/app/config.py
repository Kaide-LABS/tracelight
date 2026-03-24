from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    demo_mode: bool = False
    llm_provider: str = "google"                    # "google" or "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.1-pro-preview"       # or "gpt-5.2-chat-latest"
    llm_base_url: str = "https://api.openai.com/v1" # only used for openai provider
    default_dp_epsilon: float = 1.0
    max_entities: int = 10000
    output_dir: str = "/tmp/synth_output"
    chroma_persist_dir: str = "/tmp/chroma_data"
    
    api_key: str = ""                      # API_KEY env var
    auth_enabled: bool = True              # AUTH_ENABLED env var
    log_level: str = "INFO"                # LOG_LEVEL env var
    rate_limit_enabled: bool = True        # RATE_LIMIT_ENABLED env var

    class Config:
        env_file = ".env"

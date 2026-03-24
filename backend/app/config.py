from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_provider: str = "google"                    # "google" or "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.1-pro-preview"       # or "gpt-5.2-chat-latest"
    llm_base_url: str = "https://api.openai.com/v1" # only used for openai provider
    default_dp_epsilon: float = 1.0
    max_entities: int = 10000
    output_dir: str = "/tmp/synth_output"
    chroma_persist_dir: str = "/tmp/chroma_data"

    class Config:
        env_file = ".env"

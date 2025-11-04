from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str = "your_supabase_project_url"
    supabase_key: str = "your_supabase_anon_key"
    supabase_service_key: str = "your_supabase_service_role_key"
    
    # Application Configuration
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # WhatsApp API Configuration
    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""
    
    # OpenAI Configuration
    openai_api_key: str = ""
    
    class Config:
        env_file = None  # Disable .env file loading temporarily
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


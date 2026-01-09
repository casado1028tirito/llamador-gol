"""
Configuración central del sistema - Patrón Singleton
Gestiona todas las configuraciones del sistema de llamadas
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuración optimizada - Validación automática con Pydantic
    """
    
    # ==================== CREDENCIALES API ====================
    telegram_bot_token: str
    telegram_admin_ids: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    openai_api_key: str
    elevenlabs_api_key: str
    webhook_url: str
    webhook_port: int = Field(default=8000, validation_alias='PORT')
    
    # ==================== VOZ ====================
    voice_bot: str = "E5HSnXz7WUojYdJeUcng"
    voice_stability: float = Field(default=0.75, ge=0.0, le=1.0)
    voice_similarity: float = Field(default=0.95, ge=0.0, le=1.0)
    voice_style: float = Field(default=0.65, ge=0.0, le=1.0)
    voice_speaker_boost: bool = True
    
    # ==================== IA ====================
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = Field(default=0.85, ge=0.0, le=2.0)
    ai_max_tokens: int = Field(default=60, ge=10, le=500)
    ai_timeout: float = Field(default=1.0, ge=0.5, le=10.0)
    
    # ==================== LLAMADAS ====================
    gather_timeout: int = Field(default=5, ge=1, le=30)
    speech_timeout: int = Field(default=1, ge=1, le=10)
    max_speech_time: int = Field(default=60, ge=10, le=300)
    max_concurrent_calls: int = Field(default=50, ge=1, le=100)
    no_speech_attempts: int = Field(default=2, ge=1, le=5)
    
    # ==================== RECONOCIMIENTO VOZ ====================
    speech_model: str = "phone_call"
    language: str = "es-CO"
    enhanced: bool = True
    profanity_filter: bool = False
    
    # ==================== DTMF ====================
    dtmf_enabled: bool = True
    num_digits: int = Field(default=20, ge=1, le=50)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Convertir admin IDs de string a lista"""
        try:
            return [int(id.strip()) for id in self.telegram_admin_ids.split(",") if id.strip()]
        except (ValueError, AttributeError):
            return []


@lru_cache()
def get_settings() -> Settings:
    """Singleton pattern - Una sola instancia de configuración"""
    return Settings()


settings = get_settings()

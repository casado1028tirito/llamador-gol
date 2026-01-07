"""Configuración - Sistema de Llamadas Colombia"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Configuración optimizada para llamadas en Colombia"""
    
    # APIs esenciales
    telegram_bot_token: str
    telegram_admin_ids: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    openai_api_key: str
    elevenlabs_api_key: str
    
    # ========================================
    # VOZ LLAMADOR EL LOBO HR - ASESORA PROFESIONAL
    # ========================================
    
    # Voz de LLAMADOR EL LOBO HR - Natural, expresiva y profesional
    voice_bot: str = "E5HSnXz7WUojYdJeUcng"  # LLAMADOR EL LOBO HR (Nueva voz)
    default_voice_id: str = "E5HSnXz7WUojYdJeUcng"
    
    # OPCIÓN 2: Para CLONAR TU PROPIA VOZ:
    # 1. Ve a https://elevenlabs.io/voice-lab
    # 2. Sube 1-5 minutos de audio limpio
    # 3. Copia el Voice ID generado
    # 4. Pégalo arriba en voice_bot y default_voice_id
    
    # SETTINGS LLAMADOR EL LOBO HR - VOZ PERFECTA Y NATURAL
    voice_stability: float = 0.75  # Estabilidad óptima para naturalidad
    voice_similarity: float = 0.95  # Máxima similitud con voz original
    voice_style: float = 0.65      # Expresiva pero controlada
    voice_speaker_boost: bool = True  # Claridad perfecta en llamadas
    
    # IA para conversación PROFESIONAL Y NATURAL
    ai_model: str = "gpt-4o-mini"  # Modelo más rápido
    ai_temperature: float = 0.85  # Profesional y natural
    ai_max_tokens: int = 60  # Respuestas completas sin cortar
    ai_timeout: float = 1.0  # Timeout rápido para eliminar retrasos
    
    # Llamadas optimizadas - ESCUCHA PERFECTA Y RESPUESTA INMEDIATA
    gather_timeout: int = 5  # 5 segundos - tiempo para que empiece a hablar
    speech_timeout: int = 1  # 1 segundo - cuánto silencio indica que terminó
    max_speech_time: int = 60  # 60 segundos - tiempo máximo por respuesta
    max_concurrent_calls: int = 50  # Soportar más llamadas
    no_speech_attempts: int = 2  # Solo 2 intentos - no molestar
    profanity_filter: bool = False
    
    # Reconocimiento de voz optimizado para COLOMBIA
    speech_model: str = "phone_call"  # Modelo optimizado para llamadas
    language: str = "es-CO"  # Español Colombia
    enhanced: bool = True  # Reconocimiento mejorado
    partial_result_callback: bool = False  # Desactivar resultados parciales
    profanity_filter_twilio: bool = False  # Sin filtro de palabras
    
    # DTMF - Permitir entrada por teclado
    dtmf_enabled: bool = True  # Activar entrada por teclado
    num_digits: int = 20  # Máximo dígitos DTMF
    
    # Webhook - Railway asigna PORT dinámicamente
    webhook_url: str
    webhook_port: int = Field(default=8000, validation_alias='PORT')
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorar campos extra del .env
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Convertir IDs de admin de string a lista de integers"""
        return [int(id.strip()) for id in self.telegram_admin_ids.split(",") if id.strip()]


settings = Settings()

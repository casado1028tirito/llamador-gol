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
    # VOZ KELLY ORTIZ - ASESORA PROFESIONAL
    # ========================================
    
    # Voz de Kelly Ortiz - Natural, expresiva y profesional
    voice_bot: str = "7h1bGU3p2v8oSDwv8Ivg"  # Kelly Ortiz
    default_voice_id: str = "7h1bGU3p2v8oSDwv8Ivg"
    
    # OPCIÓN 2: Para CLONAR TU PROPIA VOZ:
    # 1. Ve a https://elevenlabs.io/voice-lab
    # 2. Sube 1-5 minutos de audio limpio
    # 3. Copia el Voice ID generado
    # 4. Pégalo arriba en voice_bot y default_voice_id
    
    # SETTINGS KELLY ORTIZ - VOZ PERFECTA Y NATURAL
    voice_stability: float = 0.85  # Estabilidad alta para naturalidad
    voice_similarity: float = 0.95  # Máxima similitud con Kelly Ortiz
    voice_style: float = 0.80      # Muy expresiva y profesional
    voice_speaker_boost: bool = True  # Claridad perfecta en llamadas
    
    # IA para conversación ULTRA RÁPIDA (CONFIABLE)
    ai_model: str = "gpt-4o-mini"  # Modelo más rápido
    ai_temperature: float = 0.9  # Natural y consistente
    ai_max_tokens: int = 35  # Respuestas completas pero ágiles 10-18 palabras
    ai_timeout: float = 1.5  # Timeout reducido para respuestas instantáneas
    
    # Llamadas optimizadas - ESCUCHA PERFECTA + VELOCIDAD
    gather_timeout: int = 2  # 2 segundos - más ágil para empezar
    speech_timeout: str = "auto"  # auto - detección inteligente cuando termina
    max_speech_time: int = 50  # 50 segundos - capturar respuestas largas completas
    max_concurrent_calls: int = 50  # Soportar más llamadas
    no_speech_attempts: int = 3  # 3 intentos antes de colgar (más rápido)
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
    
    # Webhook - Railway usa PORT variable de entorno
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

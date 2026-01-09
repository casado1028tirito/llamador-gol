"""
Síntesis de voz con ElevenLabs
Genera audio de alta calidad para llamadas telefónicas
"""
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from loguru import logger
from config import settings
import os
import asyncio
from functools import partial
from typing import Optional


class VoiceSynthesizer:
    """
    Generador de voz ElevenLabs con reintentos automáticos
    Patrón: Retry con backoff exponencial
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1  # segundos
    MIN_AUDIO_SIZE = 1000  # bytes mínimos
    TIMEOUT = 4.5  # segundos
    
    def __init__(self):
        """Inicializar sintetizador"""
        self.voice_id = settings.voice_bot
        self.audio_dir = "audio_cache"
        self._settings: Optional[VoiceSettings] = None
    
    async def initialize(self) -> None:
        """Configurar API y directorio"""
        set_api_key(settings.elevenlabs_api_key)
        os.makedirs(self.audio_dir, exist_ok=True)
        
        self._settings = VoiceSettings(
            stability=settings.voice_stability,
            similarity_boost=settings.voice_similarity,
            style=settings.voice_style,
            use_speaker_boost=settings.voice_speaker_boost
        )
        
        logger.info(f"✅ Voz {self.voice_id} lista")
    
    async def text_to_speech(self, text: str, filename: Optional[str] = None) -> bytes:
        """
        Generar audio desde texto con reintentos
        
        Args:
            text: Texto a sintetizar
            filename: Nombre archivo opcional para guardar
            
        Returns:
            bytes: Audio generado
            
        Raises:
            Exception: Si falla después de MAX_RETRIES
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"🎤 Generando audio {attempt + 1}/{self.MAX_RETRIES}: '{text[:40]}...'")
                
                loop = asyncio.get_event_loop()
                audio = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        partial(
                            generate,
                            text=text,
                            voice=Voice(voice_id=self.voice_id, settings=self._settings),
                            model="eleven_turbo_v2_5"
                        )
                    ),
                    timeout=self.TIMEOUT
                )
                
                audio_bytes = audio if isinstance(audio, bytes) else b''.join(audio)
                
                if not audio_bytes or len(audio_bytes) < self.MIN_AUDIO_SIZE:
                    raise Exception(f"Audio pequeño: {len(audio_bytes)} bytes")
                
                if filename:
                    self._save_audio(audio_bytes, filename)
                
                logger.info(f"✅ Audio: {len(audio_bytes)} bytes")
                return audio_bytes
                
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Timeout {attempt + 1}/{self.MAX_RETRIES}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                raise Exception("Timeout después de reintentos")
                
            except Exception as e:
                logger.error(f"❌ Error {attempt + 1}/{self.MAX_RETRIES}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                raise
    
    def _save_audio(self, audio_bytes: bytes, filename: str) -> None:
        """Guardar audio en archivo"""
        filepath = os.path.join(self.audio_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)

"""Síntesis de voz optimizada - Solo ElevenLabs"""
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
from loguru import logger
from config import settings
import os
import asyncio
from functools import partial


class VoiceSynthesizer:
    """Generador de voz con ElevenLabs - Rachel"""
    
    def __init__(self):
        self.voice_id = settings.voice_bot
        self.audio_dir = "audio_cache"
        self._settings = None
    
    async def initialize(self):
        """Inicializar ElevenLabs"""
        set_api_key(settings.elevenlabs_api_key)
        os.makedirs(self.audio_dir, exist_ok=True)
        
        self._settings = VoiceSettings(
            stability=settings.voice_stability,
            similarity_boost=settings.voice_similarity,
            style=settings.voice_style,
            use_speaker_boost=settings.voice_speaker_boost
        )
        
        logger.info(f"✅ Voz Kelly Ortiz ({self.voice_id}) lista - Ultra realista (ElevenLabs)")
    
    async def text_to_speech(self, text: str, filename: str = None) -> bytes:
        """Generar audio con modelo turbo v2.5 - OPTIMIZADO"""
        import asyncio
        from functools import partial
        
        # Reintentar hasta 3 veces
        for attempt in range(3):
            try:
                logger.info(f"🎤 Generando audio (intento {attempt + 1}/3): '{text[:40]}...'")
                
                # Ejecutar en thread separado para no bloquear - ULTRA RÁPIDO
                loop = asyncio.get_event_loop()
                audio = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        partial(
                            generate,
                            text=text,
                            voice=Voice(voice_id=self.voice_id, settings=self._settings),
                            model="eleven_turbo_v2_5"  # Modelo más rápido
                        )
                    ),
                    timeout=5.0  # Timeout reducido a 5 segundos para velocidad
                )
                
                # Convertir a bytes
                audio_bytes = audio if isinstance(audio, bytes) else b''.join(audio)
                
                # Validar que el audio no esté vacío
                if not audio_bytes or len(audio_bytes) < 1000:
                    raise Exception(f"Audio muy pequeño: {len(audio_bytes) if audio_bytes else 0} bytes")
                
                # Guardar archivo
                if filename:
                    filepath = os.path.join(self.audio_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(audio_bytes)
                    logger.info(f"✅ Audio guardado: {len(audio_bytes)} bytes")
                
                return audio_bytes
                
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Timeout en intento {attempt + 1}/3")
                if attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                raise Exception("ElevenLabs timeout después de 3 intentos")
            except Exception as e:
                logger.error(f"❌ Error en intento {attempt + 1}/3: {e}")
                if attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                raise

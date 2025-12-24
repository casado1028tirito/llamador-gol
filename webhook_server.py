from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from typing import Optional
import uvicorn
import os
from pathlib import Path

# Este será importado por main.py
app = FastAPI(title="Voice Caller Webhook Server")

# Crear directorio de audio si no existe
os.makedirs("audio_cache", exist_ok=True)

# Montar directorio de audio
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Servir archivos de audio generados"""
    audio_path = Path("audio_cache") / filename
    if audio_path.exists():
        return FileResponse(str(audio_path), media_type="audio/mpeg")
    logger.error(f"❌ Audio no encontrado: {filename}")
    return Response(content="Audio not found", status_code=404)

# Agregar middleware para CORS y ngrok
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logear todas las peticiones
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🌐 Petición recibida: {request.method} {request.url.path}")
    logger.info(f"🔍 Headers: {dict(request.headers)}")
    response = await call_next(request)
    logger.info(f"📤 Respuesta: {response.status_code}")
    return response

# Referencia al CallerBot (se establecerá en main.py)
caller_bot = None


def set_caller_bot(bot):
    """Establecer referencia al bot principal"""
    global caller_bot
    caller_bot = bot
    logger.info("✅ CallerBot configurado en webhook server")


@app.get("/")
async def root():
    """Endpoint de health check"""
    logger.info("✅ Health check endpoint llamado")
    return {"status": "ok", "service": "Voice Caller Webhook Server", "bot_ready": caller_bot is not None}

@app.get("/test")
async def test_endpoint():
    """Endpoint de prueba simple"""
    logger.info("🧪 Test endpoint llamado")
    return {"test": "success", "message": "Webhook server is working!"}


@app.post("/voice/incoming")
async def handle_incoming_call(request: Request):
    """
    Webhook para llamadas entrantes - RESPUESTA INSTANTÁNEA Y ROBUSTA
    """
    try:
        # Obtener datos del formulario
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        from_number = form_data.get('From', 'Unknown')
        to_number = form_data.get('To', 'Unknown')
        
        logger.info(f"📞 INCOMING CALL - SID: {call_sid} | FROM: {from_number} | TO: {to_number}")
        
        # VALIDACIÓN CRÍTICA: ¿Está inicializado el bot?
        if not caller_bot:
            logger.error("🚨 CRÍTICO: caller_bot NO INICIALIZADO")
            # Respuesta de emergencia - informar y colgar
            response = VoiceResponse()
            response.say("Lo sentimos, el sistema no está listo. Por favor intente más tarde.", 
                        language='es', voice='Polly.Mia')
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        if not call_sid:
            logger.error("🚨 CRÍTICO: No se recibió CallSid")
            response = VoiceResponse()
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # VALIDAR que voip_manager esté listo
        if not hasattr(caller_bot, 'voip_manager') or not caller_bot.voip_manager:
            logger.error("🚨 CRÍTICO: voip_manager NO INICIALIZADO")
            response = VoiceResponse()
            response.say("Sistema no disponible. Intentar después.", language='es', voice='Polly.Mia')
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # PROCESAR LLAMADA - con timeout de 5 segundos
        logger.info(f"✅ Procesando llamada {call_sid[:8]}...")
        try:
            twiml = await asyncio.wait_for(
                caller_bot.voip_manager.handle_incoming_call(call_sid),
                timeout=5.0
            )
            logger.info(f"✅ TwiML generado: {len(twiml)} caracteres")
            return Response(content=twiml, media_type="application/xml")
        except asyncio.TimeoutError:
            logger.error(f"⏱️ TIMEOUT procesando {call_sid[:8]} - usando fallback")
            # Fallback: saludo simple y gather
            response = VoiceResponse()
            gather = Gather(
                input='speech dtmf',
                language='es-CO',
                timeout=3,
                speechTimeout='auto',
                action='/voice/process_speech',
                method='POST'
            )
            gather.say("Hola, buenas. ¿Me escuchas bien?", language='es', voice='Polly.Mia')
            response.append(gather)
            response.redirect('/voice/process_speech')
            return Response(content=str(response), media_type="application/xml")
            
    except Exception as e:
        logger.error(f"🚨 ERROR CRÍTICO webhook: {e}", exc_info=True)
        # NUNCA devolver error sin TwiML válido
        response = VoiceResponse()
        response.say("Ha ocurrido un error. Disculpa las molestias.", language='es', voice='Polly.Mia')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/voice/process_speech")
async def process_speech(
    request: Request,
    SpeechResult: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None),  # DTMF del teclado
    CallSid: Optional[str] = Form(None)
):
    """
    Webhook para procesar VOZ + DTMF (teclado)
    """
    try:
        # Determinar si es voz o teclado
        user_input = None
        input_type = None
        
        if Digits:
            user_input = Digits
            input_type = "DTMF"
            logger.info(f"⌨️ DTMF recibido - Call: {CallSid}, Digits: {Digits}")
        elif SpeechResult:
            user_input = SpeechResult
            input_type = "VOZ"
            logger.info(f"🎤 Voz recibida - Call: {CallSid}, Text: {SpeechResult}")
        
        if not CallSid:
            return Response(
                content="<Response><Hangup/></Response>",
                media_type="application/xml"
            )
        
        # Si no hay entrada, preguntar de nuevo
        if not user_input or user_input.strip() == "":
            logger.warning(f"⚠️ Sin entrada para {CallSid}")
            if caller_bot:
                return Response(
                    content=await caller_bot.voip_manager.generate_followup_question(CallSid),
                    media_type="application/xml"
                )
            return Response(
                content="<Response><Hangup/></Response>",
                media_type="application/xml"
            )
        
        if caller_bot:
            # Procesar entrada (voz o DTMF)
            twiml = await caller_bot.voip_manager.handle_speech_input(
                CallSid, 
                user_input,
                input_type
            )
            return Response(content=twiml, media_type="application/xml")
        else:
            return Response(content="<Response><Hangup/></Response>", 
                          media_type="application/xml")
            
    except Exception as e:
        logger.error(f"Error procesando entrada: {e}")
        return Response(
            content="<Response><Hangup/></Response>",
            media_type="application/xml"
        )


@app.post("/voice/status")
async def call_status_callback(request: Request):
    """
    Webhook para actualizaciones de estado de llamada
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        call_status = form_data.get('CallStatus')
        
        logger.info(f"📊 Status update - Call: {call_sid}, Status: {call_status}")
        
        if caller_bot:
            await caller_bot.voip_manager.handle_call_status(call_sid, call_status)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error en status callback: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/voice/recording")
async def recording_callback(request: Request):
    """
    Webhook para cuando se completa una grabación
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        recording_url = form_data.get('RecordingUrl')
        recording_duration = form_data.get('RecordingDuration')
        
        logger.info(f"🎙️ Grabación completada - Call: {call_sid}, Duration: {recording_duration}s")
        logger.info(f"📥 URL: {recording_url}")
        
        # Aquí puedes guardar la grabación o procesarla
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error en recording callback: {e}")
        return {"status": "error", "message": str(e)}


def run_webhook_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Iniciar servidor de webhooks
    
    Args:
        host: Host donde escuchar
        port: Puerto donde escuchar
    """
    logger.info(f"🌐 Iniciando servidor webhook en {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_webhook_server()

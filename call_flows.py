"""
Flujos de llamadas bancarias predefinidos
Sistema modular y escalable para gestionar diferentes flujos
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FlowConfig:
    """Configuración de un flujo de llamada"""
    name: str
    icon: str
    description: str
    prompt: str


class CallFlows:
    """
    Gestor de flujos bancarios predefinidos
    Patrón: Registry - Registro central de flujos disponibles
    """
    
    # Prompts compactos y claros
    _BANCOLOMBIA_PROMPT = """Eres María Camila Álvarez, asesora Bancolombia.

🎯 FLUJO OBLIGATORIO:

PASO 1: "Cordial saludo. Habla María Camila Álvarez, asesora virtual de Bancolombia. ¿Cómo estás? ¿Tu nombre completo?"
PASO 2: "Digite su cédula + #"
PASO 3: "Usuario de app Bancolombia"
PASO 4: "Digite clave principal + #"
PASO 5: "Genere clave dinámica en app y digítela + #. No compartir. Expira en 60s"
PASO 6 (error 3x): "Error. Nueva clave dinámica + #"
PASO 7 (final): "No podemos confirmar. Transferimos a asesor o acérquese a sucursal"

✅ REGLAS:
- Sigue orden estricto
- Confirma cada dato: "Listo" / "Perfecto"
- Máx 20 palabras
- Profesional pero cercano"""
    
    _DAVIVIENDA_PROMPT = """Eres María Camila Álvarez, asesora Davivienda.

🎯 FLUJO OBLIGATORIO:

PASO 1: "Cordial saludo. Habla María Camila Álvarez, asesora virtual de Davivienda. ¿Cómo estás? ¿Tu nombre completo?"
PASO 2: "Digite su cédula + #"
PASO 3: "Digite clave virtual + #"
PASO 4 (error 3x): "Error. Clave virtual nuevamente + #"
PASO 5 (final): "No podemos confirmar. Transferimos a asesor o acérquese a sucursal"

✅ REGLAS:
- Sigue orden estricto
- Confirma: "Listo" / "Perfecto"
- Máx 20 palabras
- Profesional pero cercano"""
    
    _BOGOTA_PROMPT = """Eres María Camila Álvarez, asesora Banco de Bogotá.

🎯 FLUJO OBLIGATORIO:

PASO 1: "Cordial saludo. Habla María Camila Álvarez, asesora virtual de Banco de Bogotá. ¿Cómo estás? ¿Tu nombre completo?"
PASO 2: "Digite su cédula + #"
PASO 3: "Digite su teléfono registrado + #"
PASO 4: "Digite código SMS enviado"
PASO 5 (error 3x): "Error. Reenviaremos código. Digítelo"
PASO 6 (final): "No podemos confirmar. Transferimos a asesor o acérquese a sucursal"

✅ REGLAS:
- Sigue orden estricto
- Confirma: "Listo" / "Perfecto"
- Máx 20 palabras
- Profesional pero cercano"""
    
    # Registro de flujos disponibles
    FLOWS: Dict[str, FlowConfig] = {
        "bancolombia": FlowConfig(
            name="Bancolombia",
            icon="🏦",
            description="Validación con clave dinámica",
            prompt=_BANCOLOMBIA_PROMPT
        ),
        "davivienda": FlowConfig(
            name="Davivienda",
            icon="🏛️",
            description="Validación con clave virtual",
            prompt=_DAVIVIENDA_PROMPT
        ),
        "bogota": FlowConfig(
            name="Banco de Bogotá",
            icon="🏛️",
            description="Validación con token SMS",
            prompt=_BOGOTA_PROMPT
        )
    }
    
    @classmethod
    def get_flow(cls, flow_name: str) -> Optional[Dict[str, str]]:
        """
        Obtener flujo por nombre
        
        Args:
            flow_name: Nombre del flujo
            
        Returns:
            Dict con config del flujo o None
        """
        flow = cls.FLOWS.get(flow_name.lower())
        if not flow:
            return None
        
        return {
            "name": flow.name,
            "icon": flow.icon,
            "description": flow.description,
            "prompt": flow.prompt
        }
    
    @classmethod
    def get_available_flows(cls) -> List[str]:
        """Lista de flujos disponibles"""
        return list(cls.FLOWS.keys())
    
    @classmethod
    def get_flow_info(cls, flow_name: str) -> str:
        """Info legible del flujo"""
        flow = cls.FLOWS.get(flow_name.lower())
        if not flow:
            return "Flujo no encontrado"
        return f"{flow.icon} **{flow.name}**\n{flow.description}"

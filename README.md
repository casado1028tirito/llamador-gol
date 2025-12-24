# 📞 Software Llamador Kelly Ortiz - Rafa Socios

Sistema de llamadas inteligentes con IA usando la voz de Kelly Ortiz. Optimizado para tiempo real, sin delay, natural y profesional.

## 🎯 Características

- ✅ Voz de Kelly Ortiz (Natural, expresiva, profesional)
- ✅ Llamadas en tiempo real sin delay
- ✅ Respuestas instantáneas (< 1.5 segundos)
- ✅ Llamadas masivas (hasta 50 simultáneas)
- ✅ Control total vía Telegram
- ✅ Sistema simplificado y optimizado

## 🚀 Despliegue en Railway

### 1. Preparar Repositorio GitHub

```bash
# Navegar a la carpeta del proyecto
cd C:\Users\Hansel\Desktop\ARES_ELLOBOHR

# Inicializar git (si no está inicializado)
git init

# Agregar el repositorio remoto
git remote add origin https://github.com/casado1028tirito/llamador-gol.git

# Agregar todos los archivos
git add .

# Hacer commit
git commit -m "Sistema optimizado Kelly Ortiz - Tiempo real sin delay"

# Subir a GitHub
git push -u origin main
```

### 2. Desplegar en Railway

1. **Ir a Railway**: https://railway.app/
2. **Login** con tu cuenta de GitHub
3. **New Project** → **Deploy from GitHub repo**
4. **Seleccionar**: `casado1028tirito/llamador-gol`
5. Railway detectará automáticamente el `railway.json` y `Procfile`

### 3. Configurar Variables de Entorno en Railway

En Railway, ir a **Variables** y agregar:

```env
# Telegram
TELEGRAM_BOT_TOKEN=tu_token_de_bot
TELEGRAM_ADMIN_IDS=123456789,987654321

# Twilio
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI
OPENAI_API_KEY=sk-...

# ElevenLabs (Kelly Ortiz)
ELEVENLABS_API_KEY=tu_api_key

# Webhook (Railway te dará un dominio)
WEBHOOK_URL=https://tu-app.railway.app
WEBHOOK_PORT=8000
```

### 4. Obtener el Dominio de Railway

1. En Railway, ir a **Settings** → **Networking**
2. Hacer clic en **Generate Domain**
3. Copiar el dominio (ejemplo: `llamador-production-xxxx.up.railway.app`)
4. Actualizar la variable `WEBHOOK_URL` con: `https://tu-dominio.up.railway.app`

### 5. Configurar Webhook en Twilio

1. Ir a Twilio Console: https://console.twilio.com/
2. Ir a **Phone Numbers** → **Manage** → **Active Numbers**
3. Seleccionar tu número de teléfono
4. En **Voice & Fax** → **A CALL COMES IN**:
   - Webhook: `https://tu-dominio.railway.app/webhook/voice`
   - HTTP POST
5. En **Status Callback URL**:
   - Webhook: `https://tu-dominio.railway.app/webhook/status`
   - HTTP POST
6. **Save**

### 6. Verificar que Todo Funciona

```bash
# Ver logs en Railway
# Railway → Tu Proyecto → Deployments → View Logs

# Deberías ver:
# ✅ Bot de Telegram iniciado
# ✅ Cliente Twilio inicializado
# ✅ Voz Kelly Ortiz lista
# ✅ Sistema activo
```

## 📱 Comandos de Telegram

Una vez desplegado, abre tu bot de Telegram y usa:

### Comandos Principales

```
/start - Ver comandos disponibles
/llamar +573012345678 - Hacer una llamada
/masivo +57301... +57302... - Llamadas múltiples
/activas - Ver llamadas en curso
/colgar - Colgar todas las llamadas
/instruccion <texto> - Personalizar comportamiento de Kelly
```

### Ejemplos de Uso

**Llamada Simple:**
```
/llamar +573012345678
```

**Llamadas Masivas:**
```
/masivo +573012345678 +573098765432 +573011112222
```

**Personalizar a Kelly:**
```
/instruccion Eres Kelly Ortiz de Bancolombia. Valida la identidad del cliente solicitando que descargue la app SOY YO. Sé amable, profesional y breve. Máximo 8 palabras por respuesta.
```

## 🔧 Solución de Problemas

### El bot no responde en Telegram
- Verifica que `TELEGRAM_BOT_TOKEN` esté correcto
- Verifica que tu user ID esté en `TELEGRAM_ADMIN_IDS`

### Las llamadas no se conectan
- Verifica que el webhook de Twilio apunte a tu dominio de Railway
- Verifica que `TWILIO_PHONE_NUMBER` incluya el código de país con `+`
- Revisa los logs en Railway

### La voz no suena bien
- La voz de Kelly Ortiz ya está optimizada con el ID: `7h1bGU3p2v8oSDwv8Ivg`
- Verifica que `ELEVENLABS_API_KEY` esté correcto
- Verifica que tengas créditos en ElevenLabs

### Las respuestas son lentas
- El sistema está optimizado para < 1.5 segundos
- Si es más lento, verifica la latencia de Railway
- Considera cambiar la región de Railway más cerca de Colombia

## 📊 Monitoreo

### Ver Logs en Tiempo Real
```bash
# En Railway
Deployments → View Logs
```

### Logs Importantes
```
✅ Bot de Telegram iniciado
✅ Cliente Twilio inicializado  
✅ Voz Kelly Ortiz lista
📞 Llamada iniciada
🎤 Generando audio
💬 Respuesta de IA
```

## ⚙️ Configuración Avanzada

### Ajustar Velocidad de Respuesta

Editar `config.py`:
```python
# Más rápido (menos natural)
ai_timeout: float = 1.0
gather_timeout: int = 1
speech_timeout: str = "0.8"

# Más natural (un poco más lento)
ai_timeout: float = 2.0
gather_timeout: int = 3
speech_timeout: str = "1.5"
```

### Cambiar Características de Voz

Editar `config.py`:
```python
# Más estable y consistente
voice_stability: float = 0.90

# Más expresiva y variable
voice_stability: float = 0.70

# Más similar a Kelly original
voice_similarity: float = 1.0

# Más estilizada
voice_style: float = 0.90
```

## 💡 Tips de Uso

1. **Instrucciones Claras**: Dale instrucciones específicas a Kelly con `/instruccion`
2. **Prueba Primero**: Haz una llamada de prueba antes de llamadas masivas
3. **Monitorea**: Usa `/activas` para ver el estado de las llamadas
4. **Respuestas Cortas**: Kelly está optimizada para respuestas de máximo 8 palabras
5. **Contexto**: Kelly mantiene el contexto de la conversación

## 🎯 Ejemplos de Instrucciones

### Validación Bancolombia
```
/instruccion Eres Kelly Ortiz de Bancolombia, área de seguridad. Valida identidad con app SOY YO. Saluda, explica motivo, pide descarga de app. Máximo 8 palabras por turno. Profesional y amable.
```

### Ventas
```
/instruccion Eres Kelly, vendedora profesional. Ofrece producto con 30% descuento. Escucha necesidades, adapta oferta. Natural y persuasiva. Breve.
```

### Recordatorio
```
/instruccion Eres Kelly, asistente virtual. Recuerda cita médica mañana 10am. Confirma asistencia. Amable y breve.
```

## 📞 Soporte

Si necesitas ayuda:
1. Revisa los logs en Railway
2. Verifica todas las variables de entorno
3. Prueba con un número de teléfono conocido
4. Contacta al equipo de desarrollo

## 🔒 Seguridad

- ✅ Variables de entorno nunca se suben a GitHub
- ✅ Solo usuarios autorizados pueden usar el bot
- ✅ Logs no contienen información sensible
- ✅ Conexiones encriptadas (HTTPS/WSS)

## 📝 Changelog

### v2.0 - Kelly Ortiz Optimizada
- ✅ Voz de Kelly Ortiz implementada
- ✅ Tiempo real sin delay (< 1.5s)
- ✅ Sistema simplificado (solo comandos esenciales)
- ✅ Optimizado para Railway
- ✅ Soporte hasta 50 llamadas simultáneas
- ✅ Respuestas más naturales y expresivas

---

**Desarrollado para Rafa Socios** 🚀

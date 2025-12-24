# Script de despliegue a GitHub
Write-Host "🚀 Desplegando a GitHub..." -ForegroundColor Green

# Inicializar git si no existe
if (-not (Test-Path .git)) {
    Write-Host "📦 Inicializando repositorio Git..." -ForegroundColor Yellow
    git init
}

# Agregar remote si no existe
$remoteExists = git remote get-url origin 2>$null
if (-not $remoteExists) {
    Write-Host "🔗 Agregando remote de GitHub..." -ForegroundColor Yellow
    git remote add origin https://github.com/casado1028tirito/llamador-gol.git
}

# Agregar todos los archivos
Write-Host "📁 Agregando archivos..." -ForegroundColor Yellow
git add .

# Hacer commit
Write-Host "💾 Creando commit..." -ForegroundColor Yellow
$fecha = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Sistema Kelly Ortiz optimizado - $fecha - Ultra rápido, sin delays, IA inicia llamadas"

# Subir a GitHub
Write-Host "📤 Subiendo a GitHub..." -ForegroundColor Yellow
git push -u origin main -f

Write-Host ""
Write-Host "✅ DESPLIEGUE COMPLETADO!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 SIGUIENTE PASO: DESPLEGAR EN RAILWAY" -ForegroundColor Cyan
Write-Host "1. Ve a https://railway.app/" -ForegroundColor White
Write-Host "2. New Project > Deploy from GitHub repo" -ForegroundColor White
Write-Host "3. Selecciona: casado1028tirito/llamador-gol" -ForegroundColor White
Write-Host "4. Configura variables de entorno" -ForegroundColor White
Write-Host "5. Genera dominio público en Settings > Networking" -ForegroundColor White
Write-Host "6. Actualiza WEBHOOK_URL con el dominio de Railway" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANTE: Una vez en Railway, NO necesitas ngrok ni ejecutar nada local" -ForegroundColor Yellow
Write-Host "    Railway te da una URL permanente 24/7" -ForegroundColor Yellow
Write-Host ""

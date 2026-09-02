# Continuous Keystroke Auth - Startup Script
# Starts all required services in separate windows

Write-Host "🚀 Starting Continuous Keystroke Authentication System..." -ForegroundColor Cyan
Write-Host ""

# Check if MongoDB is already running
$mongoRunning = Get-Process mongod -ErrorAction SilentlyContinue
if ($mongoRunning) {
    Write-Host "✅ MongoDB is already running (PID: $($mongoRunning.Id))" -ForegroundColor Green
} else {
    Write-Host "📦 Starting MongoDB..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '🍃 MongoDB Server' -ForegroundColor Green; Write-Host ''; mongod"
    Write-Host "   Waiting for MongoDB to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
}

Write-Host "🐍 Starting Backend (FastAPI on port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; Write-Host '🔧 Backend API Server' -ForegroundColor Cyan; Write-Host ''; python main.py"
Write-Host "   Waiting for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 4

Write-Host "⚛️  Starting Frontend (Vite on port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; Write-Host '🎨 Frontend Development Server' -ForegroundColor Magenta; Write-Host ''; npm run dev"
Write-Host "   Waiting for frontend to compile..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Opening browser in 3 seconds..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Open browser
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
Write-Host "  • MongoDB:  mongodb://localhost:27017"
Write-Host "  • Backend:  http://localhost:8000"
Write-Host "  • Frontend: http://localhost:5173"
Write-Host ""
Write-Host "Check the other terminal windows for service logs." -ForegroundColor Gray
Write-Host "Press any key to exit (services will continue running)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")


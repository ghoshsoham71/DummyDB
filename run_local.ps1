# BurstDB Local Setup Script (Non-Docker)

# 1. Install dependencies
uv sync

# 2. Check for Redis
Write-Host "Checking for Redis..."
if (Get-Service -Name "redis" -ErrorAction SilentlyContinue) {
    Write-Host "Redis service found and starting..."
    Start-Service -Name "redis"
} else {
    Write-Host "Redis service not found. Please install Redis for Windows or run it via WSL."
    Write-Host "Download: https://github.com/tporadowski/redis/releases"
}

# 3. Start workers in new windows
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd api; uv run celery -A src.celery_app worker --loglevel=info -P solo"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd api; uv run uvicorn src.main:app --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ui; npm run dev"

Write-Host "Services are starting in separate windows."

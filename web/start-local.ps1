[CmdletBinding()]
param(
    [switch]$CoreOnly,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$WebDir = $PSScriptRoot
$RootDir = Split-Path -Parent $WebDir
$BackendDir = Join-Path $WebDir "backend"
$FrontendDir = Join-Path $WebDir "frontend"
$SourceDir = Join-Path $RootDir "src"
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "Python was not found. Install Python 3.10-3.13 or create the repository .venv first."
    }
    $PythonExe = $PythonCommand.Source
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS, then open a new PowerShell window."
}

if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "[1/4] Installing core API and signal-processing dependencies..." -ForegroundColor Cyan
    & $PythonExe -m pip install -r (Join-Path $WebDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Core Python dependency installation failed." }

    if (-not $CoreOnly) {
        Write-Host ""
        Write-Host "Installing the optional CPU Track Lab model stack. This can take several minutes and uses substantial disk space..." -ForegroundColor Cyan
        & $PythonExe -m pip install -r (Join-Path $WebDir "requirements-track-lab.txt")
        if ($LASTEXITCODE -ne 0) { throw "Track Lab dependency installation failed. See the pip error above." }
    }

    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host ""
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        Push-Location $FrontendDir
        try {
            & npm install --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
        }
        finally { Pop-Location }
    }
}

if (-not $CoreOnly) {
    & $PythonExe -c "import audio_separator.separator" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Track Lab model dependencies are not installed. Track Lab will return 503. Run this script without -CoreOnly to install them."
    }
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Warning "FFmpeg was not found on PATH. Some input formats and model workflows may fail. Install FFmpeg and reopen the terminal."
    }
}

$healthUri = "http://127.0.0.1:8000/api/health"
$apiReady = $false
try {
    $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
    $apiReady = $health.status -eq "ok"
}
catch { }

if (-not $apiReady) {
    Write-Host ""
    Write-Host "[2/4] Starting FastAPI backend in a separate terminal..." -ForegroundColor Cyan
    $apiCommand = '$env:PYTHONPATH = "' + $BackendDir + ';' + $SourceDir + '"; Set-Location -LiteralPath "' + $BackendDir + '"; & "' + $PythonExe + '" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
    $apiEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($apiCommand))
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $apiEncoded)

    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
            if ($health.status -eq "ok") { $apiReady = $true; break }
        }
        catch { }
    }
}
if (-not $apiReady) {
    throw "FastAPI did not become ready at http://127.0.0.1:8000. Check the separate API terminal for the import or startup error."
}
Write-Host "FastAPI is responding at http://127.0.0.1:8000/api/health" -ForegroundColor Green

$frontendUri = "http://127.0.0.1:5173"
$frontendReady = $false
try {
    $null = Invoke-WebRequest -Uri $frontendUri -TimeoutSec 2 -UseBasicParsing
    $frontendReady = $true
}
catch { }

if (-not $frontendReady) {
    Write-Host ""
    Write-Host "[3/4] Starting Vite frontend in a separate terminal..." -ForegroundColor Cyan
    $frontendCommand = 'Set-Location -LiteralPath "' + $FrontendDir + '"; & npm run dev -- --host 127.0.0.1 --strictPort'
    $frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendCommand))
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $frontendEncoded)

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-WebRequest -Uri $frontendUri -TimeoutSec 2 -UseBasicParsing
            $frontendReady = $true
            break
        }
        catch { }
    }
}
if (-not $frontendReady) {
    throw "Vite did not become ready at http://127.0.0.1:5173. Check the separate frontend terminal for the startup error."
}

Write-Host ""
Write-Host "[4/4] Both servers are responding. Opening Unmix..." -ForegroundColor Green
Start-Process "http://localhost:5173"
Write-Host "Track Lab uses a pretrained model and may download weights the first time you run it."
Write-Host "Mix Lab uses the repository's own FastICA implementation. Use clean, mono source files for the controlled experiment."

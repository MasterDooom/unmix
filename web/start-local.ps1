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
$VenvDir = Join-Path $RootDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating a project-local Python environment (preferring Python 3.12)..." -ForegroundColor Cyan
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    $CreatedEnvironment = $false

    if ($PythonLauncher) {
        foreach ($Version in @("3.12", "3.11", "3.13", "3.10")) {
            & $PythonLauncher.Source "-$Version" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) and sys.version_info < (3, 14) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                & $PythonLauncher.Source "-$Version" -m venv $VenvDir
                if ($LASTEXITCODE -eq 0 -and (Test-Path $PythonExe)) {
                    $CreatedEnvironment = $true
                    break
                }
            }
        }
    }

    if (-not $CreatedEnvironment) {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $PythonCommand) {
            throw "Python 3.10-3.13 was not found. Install Python 3.12 from https://www.python.org/downloads/ and rerun this script."
        }
        & $PythonCommand.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) and sys.version_info < (3, 14) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "Unmix requires Python 3.10-3.13. Python 3.14 is not supported by the current Track Lab model stack."
        }
        & $PythonCommand.Source -m venv $VenvDir
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PythonExe)) {
            throw "Could not create the .venv environment. Check that this Python installation includes the venv module."
        }
    }
}

& $PythonExe -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) and sys.version_info < (3, 14) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "The existing .venv uses an unsupported Python version. Keep its files backed up and recreate it using Python 3.12 before continuing."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS, then open a new PowerShell window."
}

if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "[1/4] Installing core API and signal-processing dependencies..." -ForegroundColor Cyan
    & $PythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip inside .venv." }
    & $PythonExe -m pip install -r (Join-Path $WebDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Core Python dependency installation failed." }

    if (-not $CoreOnly) {
        Write-Host ""
        Write-Host "Installing the optional CPU Track Lab model stack. This can take several minutes and uses substantial disk space..." -ForegroundColor Cyan
        & $PythonExe -m pip install -r (Join-Path $WebDir "requirements-track-lab.txt")
        if ($LASTEXITCODE -ne 0) { throw "Track Lab dependency installation failed. See the pip error above." }
    }

    $FrontendModules = Join-Path $FrontendDir "node_modules"
    $ViteExecutable = Join-Path $FrontendModules ".bin\vite.cmd"
    $VitestExecutable = Join-Path $FrontendModules ".bin\vitest.cmd"
    $LockFile = Join-Path $FrontendDir "package-lock.json"
    $DependencyInstallNeeded = (
        -not (Test-Path $FrontendModules) -or
        -not (Test-Path $ViteExecutable) -or
        -not (Test-Path $VitestExecutable) -or
        (Test-Path $LockFile -and (Get-Item $LockFile).LastWriteTime -gt (Get-Item $FrontendModules).LastWriteTime)
    )
    if ($DependencyInstallNeeded) {
        Write-Host ""
        Write-Host "Installing frontend dependencies from package-lock.json..." -ForegroundColor Cyan
        Push-Location $FrontendDir
        try {
            & npm ci --no-audit --no-fund
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
        $Winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $Winget) {
            throw "Track Lab needs FFmpeg. Install it from https://ffmpeg.org/download.html, reopen PowerShell, and rerun this script. Use -CoreOnly to run Mix Lab without Track Lab."
        }
        Write-Host "FFmpeg is required for Track Lab. Installing it using winget..." -ForegroundColor Cyan
        & $Winget.Source install -e --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "FFmpeg installation failed. Install it from https://ffmpeg.org/download.html, then rerun this script."
        }
        $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machinePath;$userPath"
        $wingetLinks = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links"
        if (Test-Path $wingetLinks) { $env:Path = "$env:Path;$wingetLinks" }
        if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            throw "FFmpeg was installed, but this terminal cannot find it yet. Close this terminal, open a new one, and rerun .\web\start-local.ps1."
        }
    }
}

$healthUri = "http://127.0.0.1:8000/api/health"
$apiReady = $false
$health = $null
try { $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2 } catch { }
if ($health -and $health.status -eq "ok") {
    if ($health.api_contract_version -ne 2) {
        throw "A stale Unmix API is already running on port 8000. Close its FastAPI terminal, then rerun this launcher."
    }
    $apiReady = $true
}

if (-not $apiReady) {
    Write-Host ""
    Write-Host "[2/4] Starting FastAPI backend in a separate terminal..." -ForegroundColor Cyan
    $apiCommand = '$env:PYTHONPATH = "' + $BackendDir + ';' + $SourceDir + '"; Set-Location -LiteralPath "' + $BackendDir + '"; & "' + $PythonExe + '" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
    $apiEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($apiCommand))
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $apiEncoded)

    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        Start-Sleep -Seconds 1
        $health = $null
        try { $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2 } catch { }
        if ($health -and $health.status -eq "ok") {
            if ($health.api_contract_version -ne 2) {
                throw "An older Unmix API is occupying port 8000. Close its FastAPI terminal and rerun this launcher."
            }
            $apiReady = $true
            break
        }
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

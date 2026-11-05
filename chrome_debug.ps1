param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

$Chrome    = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$Profile   = "$env:LOCALAPPDATA\Google\Chrome\User Data"
$Port      = 9222
$DebugUrl  = "http://127.0.0.1:$Port"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-DebugUp {
    try {
        Invoke-RestMethod "$DebugUrl/json/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

switch ($Action) {
    "start" {
        if (Test-DebugUp) {
            Write-Host "[chrome_debug] debug Chrome already running on port $Port."
            break
        }
        $chromeProcs = Get-Process chrome -ErrorAction SilentlyContinue
        if ($chromeProcs) {
            Write-Warning "[chrome_debug] Chrome is already running WITHOUT the debug port."
            Write-Warning "[chrome_debug] The debug port will NOT bind. Close ALL Chrome windows, then re-run: .\chrome_debug.ps1 start"
            break
        }
        Start-Process -FilePath $Chrome -ArgumentList "--remote-debugging-port=$Port --user-data-dir=`"$Profile`" https://www.instagram.com/"
        Write-Host "[chrome_debug] launched debug Chrome on port $Port. Log in to Instagram there."
    }
    "stop" {
        if (-not (Test-DebugUp)) {
            Write-Host "[chrome_debug] no debug Chrome running on port $Port."
            break
        }
        Write-Host "[chrome_debug] closing debug Chrome gracefully (cookies flushed, login preserved)..."
        & "$ScriptDir\.venv\Scripts\python.exe" "$ScriptDir\cdp_close.py" $Port
        Write-Host "[chrome_debug] done. NEVER use taskkill / Stop-Process -Force — it wipes the IG login."
    }
    "status" {
        if (Test-DebugUp) {
            $v = Invoke-RestMethod "$DebugUrl/json/version" -TimeoutSec 2
            Write-Host "[chrome_debug] RUNNING — $($v.Browser) (port $Port)"
        } else {
            Write-Host "[chrome_debug] not running (port $Port)"
        }
    }
}

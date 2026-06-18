# setup-startup.ps1
# Registra o dashboard do Auditor para iniciar automaticamente com o Windows.
# Execute uma vez com: powershell -ExecutionPolicy Bypass -File scripts\setup-startup.ps1

param([int]$Port = 8000)

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectDir ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Error "pythonw.exe não encontrado. Certifique-se de ter rodado: python -m venv .venv && pip install -e .[dev]"
    exit 1
}

$taskName = "AuditorMinimalClub"

$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "-m auditor server --no-open --port $Port" `
    -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -AtLogon

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 23) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

try { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Dashboard do Auditor Técnico Minimal Club" `
    -Force | Out-Null

Write-Host ""
Write-Host "Configurado com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "O servidor vai iniciar automaticamente ao fazer login no Windows."
Write-Host "Acesse: http://localhost:$Port"
Write-Host ""
Write-Host "Para iniciar agora sem reiniciar:"
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
Write-Host "Para remover o startup automatico:"
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"

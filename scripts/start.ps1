param(
    [switch]$Source,
    [switch]$CheckOnly,
    [string]$PythonPath = '',
    [string]$IndexUrl = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$transcribing = $false
$startupCode = 0
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = [Console]::OutputEncoding

function Invoke-VisibleNative {
    param([string]$CommandPath, [string[]]$Arguments)
    # Write native output through the host so transcript includes child setup errors.
    $ErrorActionPreference = 'Continue'
    & $CommandPath @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}
try {
    try {
        Start-Transcript -Path (Join-Path $projectRoot 'startup.log') -Force | Out-Null
        $transcribing = $true
    } catch { Write-Host 'Could not open startup.log; errors will still appear in this window.' }

    $packagedExe = Join-Path $projectRoot 'dist\FlashDesk\FlashDesk.exe'
    if ((Test-Path -LiteralPath $packagedExe -PathType Leaf) -and -not $Source -and -not $CheckOnly) {
        Write-Host '[Launch] Starting the packaged application.'
        Start-Process -FilePath $packagedExe -WorkingDirectory (Split-Path -Parent $packagedExe)
    } else {
        Write-Host '[Launch] Starting from source. GitHub source downloads do not include dist or .venv.'
        $sourcePython = Join-Path $projectRoot '.venv\Scripts\python.exe'
        $needsSetup = -not (Test-Path -LiteralPath $sourcePython -PathType Leaf)
        if (-not $needsSetup) {
            $probeCode = Invoke-VisibleNative -CommandPath $sourcePython -Arguments @((Join-Path $PSScriptRoot 'check_environment.py'))
            $needsSetup = $probeCode -ne 0
        }
        if ($needsSetup) {
            $setupArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $projectRoot 'setup.ps1'))
            if ($PythonPath) { $setupArgs += @('-PythonPath', $PythonPath) }
            if ($IndexUrl) { $setupArgs += @('-IndexUrl', $IndexUrl) }
            $setupCode = Invoke-VisibleNative -CommandPath powershell.exe -Arguments $setupArgs
            if ($setupCode -ne 0) { throw 'Setup did not complete. Fix the error above and run the launcher again.' }
        }
        if ($CheckOnly) {
            Write-Host '[Launch] Source environment OK. Check-only mode: no GUI or hardware started.'
        } else {
            Write-Host '[Launch] Keep this console open while FlashDesk is running; it shows startup errors.'
            $startupCode = Invoke-VisibleNative -CommandPath $sourcePython -Arguments @('-u', (Join-Path $projectRoot 'main.py'))
            if ($startupCode -ne 0) { throw "Application exited with code $startupCode. See the output above." }
        }
    }
} catch {
    Write-Host "[Launch failed] $($_.Exception.Message)" -ForegroundColor Red
    $startupCode = 1
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
}
exit $startupCode

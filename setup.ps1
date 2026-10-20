param(
    [switch]$Dev,
    [string]$PythonPath = '',
    [string]$IndexUrl = ''
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

try {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        $candidates = @()
        if ($PythonPath) {
            if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
                throw "Python executable not found: $PythonPath"
            }
            $candidates += @{File = (Resolve-Path -LiteralPath $PythonPath).Path; Args = @()}
        } else {
            foreach ($version in @('-3.11', '-3.12', '-3.13')) {
                $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
                if ($launcher) { $candidates += @{File = $launcher.Source; Args = @($version)} }
            }
            foreach ($command in @('python.exe', 'python3.exe')) {
                $found = Get-Command $command -CommandType Application -ErrorAction SilentlyContinue
                if ($found -and $found.Source -notlike '*\WindowsApps\*') { $candidates += @{File = $found.Source; Args = @()} }
            }
        }
        $selected = $null
        foreach ($candidate in $candidates) {
            $candidateArgs = $candidate.Args
            # Avoid nested quotes in -c for Windows PowerShell 5.1.
            try {
                & $candidate.File @candidateArgs -c 'import sys,struct; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) and struct.calcsize(chr(80))==8 else 1)' 2>$null
                if ($LASTEXITCODE -eq 0) { $selected = $candidate; break }
            } catch { continue }
        }
        if ($null -eq $selected) {
            throw 'Install 64-bit Python 3.11 (recommended), 3.12 or 3.13 from https://www.python.org/downloads/windows/ ; then run the launcher again. This source download does not contain an EXE.'
        }
        Write-Host '[Setup] Creating a local Python environment...'
        $selectedArgs = $selected.Args
        & $selected.File @selectedArgs -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Check Python installation and folder write permissions.' }
    }
    & $venvPython -c 'import sys,struct; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) and struct.calcsize(chr(80))==8 else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv is invalid or incompatible. Rename .venv and run setup again with 64-bit Python 3.11-3.13.' }
    $package = if ($Dev) { '.[dev]' } else { '.' }
    Write-Host '[Setup] Installing dependencies. The first run requires Internet access...'
    $pipArgs = @('-m', 'pip', 'install', '--disable-pip-version-check', '--timeout', '60', '-e', $package)
    if ($IndexUrl) {
        if ($IndexUrl -notmatch '^https://[^\s]+$') { throw 'IndexUrl must be an HTTPS package index URL.' }
        $pipArgs += @('--index-url', $IndexUrl)
    }
    & $venvPython @pipArgs
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the pip output and network connection, then retry setup.ps1.' }
    & $venvPython (Join-Path $PSScriptRoot 'scripts\check_environment.py')
    if ($LASTEXITCODE -ne 0) { throw 'Environment validation failed after installation.' }
    Write-Host '[Setup] Ready. You can run the FlashDesk launcher.'
} catch {
    Write-Host "[Setup failed] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name FlashDesk --collect-all esptool --collect-all stcgal --collect-all serial --copy-metadata esptool --copy-metadata stcgal --copy-metadata rich-click --hidden-import intelhex --hidden-import serial.tools.list_ports_windows main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& .\.venv\Scripts\python.exe scripts\package_notices.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging notices failed' }

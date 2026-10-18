$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "vfetch"
if ($env:VFETCH_UNINSTALL -eq "1") { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue; exit }
$python = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python -ErrorAction Stop).Source }
& $python -3 -m venv $root
& "$root\Scripts\python.exe" -m pip install -U "yt-dlp[default]" vfetch
$shim = Join-Path $root "vfetch.cmd"; "@echo off`r`n`"$root\Scripts\vfetch.exe`" %*" | Set-Content $shim
$path = [Environment]::GetEnvironmentVariable("Path", "User"); if ($path -notlike "*$root*") { [Environment]::SetEnvironmentVariable("Path", "$root;$path", "User") }
Write-Host "Installed VFetch. Restart PowerShell if vfetch is not yet on PATH."

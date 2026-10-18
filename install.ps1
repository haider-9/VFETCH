$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "vfetch"
if ($env:VFETCH_UNINSTALL -eq "1") { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue; exit }
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $python = $pyLauncher.Source
    $pythonArgs = @("-3")
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
    $pythonArgs = @()
}
if (Test-Path $root) { Remove-Item -Recurse -Force $root }
& $python @pythonArgs -m venv --copies $root
$venvPython = Join-Path $root "Scripts\python.exe"
& $venvPython -m pip install -U "yt-dlp[default]" "git+https://github.com/haider-9/VFETCH.git"
$shim = Join-Path $root "vfetch.cmd"; "@echo off`r`n`"$root\Scripts\vfetch.exe`" %*" | Set-Content $shim
$path = [Environment]::GetEnvironmentVariable("Path", "User"); if ($path -notlike "*$root*") { [Environment]::SetEnvironmentVariable("Path", "$root;$path", "User") }
Write-Host "Installed VFetch. Restart PowerShell if vfetch is not yet on PATH."

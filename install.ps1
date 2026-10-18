$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "vfetch"
if ($env:VFETCH_UNINSTALL -eq "1") { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue; exit }
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $pythonCommand = $pyLauncher.Source
    $pythonArgs = @("-3")
} else {
    $pythonCommand = (Get-Command python -ErrorAction Stop).Source
    $pythonArgs = @()
}
if (Test-Path $root) { Remove-Item -Recurse -Force $root }
$python = (& $pythonCommand @pythonArgs -c "import sys; print(sys.executable)").Trim()
$sitePackages = Join-Path $root "Lib\site-packages"
New-Item -ItemType Directory -Force $sitePackages | Out-Null
& $python -m pip install -U --target $sitePackages "yt-dlp[default]" "prompt-toolkit>=3.0" "git+https://github.com/haider-9/VFETCH.git"
$shim = Join-Path $root "vfetch.cmd"
$shimContent = "@echo off`r`n`"$python`" -c `"import sys; sys.path.insert(0, r'$sitePackages'); from vfetch.cli import main; raise SystemExit(main())`" %*`r`n"
$shimContent | Set-Content $shim
$path = [Environment]::GetEnvironmentVariable("Path", "User"); if ($path -notlike "*$root*") { [Environment]::SetEnvironmentVariable("Path", "$root;$path", "User") }
Write-Host "Installed VFetch. Restart PowerShell if vfetch is not yet on PATH."

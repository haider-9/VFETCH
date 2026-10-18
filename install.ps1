$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "vfetch"
if ($env:VFETCH_UNINSTALL -eq "1") { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue; exit }
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "ffmpeg is required by VFetch and was not found. Installing it first..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    $scoop = Get-Command scoop -ErrorAction SilentlyContinue
    if ($winget) {
        & $winget.Source install --id Gyan.FFmpeg.Shared --exact --accept-source-agreements --accept-package-agreements
    } elseif ($choco) {
        & $choco.Source install ffmpeg -y
    } elseif ($scoop) {
        & $scoop.Source install ffmpeg
    } else {
        throw "Cannot install ffmpeg automatically. Install winget, Chocolatey, or Scoop, then run this installer again."
    }
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [Environment]::GetEnvironmentVariable("Path", "User")
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $ffmpeg) { throw "ffmpeg installation did not complete successfully." }
}
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

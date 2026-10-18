# VFetch installer for Windows (works on Windows PowerShell 5.1 and PowerShell 7)
# Optional env vars: VFETCH_UNINSTALL=1, VFETCH_REF=<tag-or-branch>
$ErrorActionPreference = "Stop"

$root = Join-Path $env:LOCALAPPDATA "vfetch"
$repo = "git+https://github.com/haider-9/VFETCH.git"
if ($env:VFETCH_REF) { $repo = "$repo@$($env:VFETCH_REF)" }

function Get-PathEntries([string]$scope) {
    $value = [Environment]::GetEnvironmentVariable("Path", $scope)
    if (-not $value) { return @() }
    return @($value.Split(";") | Where-Object { $_ })
}

function Find-Python {
    # Try the py launcher first, then python/python3. Each candidate is actually run,
    # which rejects the Microsoft Store "App execution alias" stubs.
    $candidates = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $candidates += ,@($py.Source, "-3") }
    foreach ($name in "python", "python3") {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += ,@($cmd.Source) }
    }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        foreach ($c in $candidates) {
            $exe = $c[0]
            $extra = @($c | Select-Object -Skip 1)
            $out = & $exe @extra -c "import sys; print(sys.executable if sys.version_info >= (3, 10) else '')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) { return ("$out").Trim() }
        }
    } finally {
        $ErrorActionPreference = $prev
    }
    return $null
}

function Install-VFetch {
    # ffmpeg
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
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
        $env:Path = ([Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User"))
        if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            throw "ffmpeg installation did not complete successfully. Restart PowerShell and run the installer again."
        }
    }

    # git (pip needs it for the git+https:// source)
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is required to install VFetch. Install it (winget install Git.Git) and run this installer again."
    }

    # Python
    $python = Find-Python
    if (-not $python) {
        throw "Python 3.10+ was not found. Install it (winget install Python.Python.3.12) and run this installer again."
    }

    # Fresh install into %LOCALAPPDATA%\vfetch
    if (Test-Path $root) { Remove-Item -Recurse -Force $root }
    $sitePackages = Join-Path $root "Lib\site-packages"
    New-Item -ItemType Directory -Force $sitePackages | Out-Null

    # pip writes notices to stderr, which Windows PowerShell 5.1 can turn into
    # terminating errors, so judge success by the exit code instead.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $python -m pip install --upgrade --target $sitePackages "yt-dlp[default]" "prompt-toolkit>=3.0" $repo
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) {
        Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
        throw "pip failed with exit code $code."
    }

    # Launcher script (a file, so no quoting problems with unusual user names)
    $launcher = @(
        "import os, sys",
        "sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Lib', 'site-packages'))",
        "from vfetch.cli import main",
        "raise SystemExit(main())"
    ) -join "`n"
    Set-Content -Path (Join-Path $root "_launcher.py") -Value $launcher -Encoding UTF8

    # vfetch.cmd: use the Python we installed with; fall back to the py launcher if it moves.
    $shim = Join-Path $root "vfetch.cmd"
    $shimLines = @(
        "@echo off",
        "if exist `"$python`" goto direct",
        "py -3 `"%~dp0_launcher.py`" %*",
        "exit /b %errorlevel%",
        ":direct",
        "`"$python`" `"%~dp0_launcher.py`" %*",
        "exit /b %errorlevel%"
    ) -join "`r`n"
    Set-Content -Path $shim -Value $shimLines -Encoding Oem

    # PATH (user scope + current session)
    $userEntries = Get-PathEntries "User"
    if (-not ($userEntries | Where-Object { $_.TrimEnd("\") -ieq $root.TrimEnd("\") })) {
        [Environment]::SetEnvironmentVariable("Path", ((@($root) + $userEntries) -join ";"), "User")
    }
    if (-not (($env:Path.Split(";")) | Where-Object { $_.TrimEnd("\") -ieq $root.TrimEnd("\") })) {
        $env:Path = "$root;$env:Path"
    }

    # Smoke test
    & $shim --version
    if ($LASTEXITCODE -ne 0) { throw "Install finished but 'vfetch --version' failed." }
    Write-Host "Installed VFetch. Restart PowerShell if 'vfetch' is not found in other windows."
}

function Uninstall-VFetch {
    if (Test-Path $root) { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue }
    $kept = Get-PathEntries "User" | Where-Object { $_.TrimEnd("\") -ine $root.TrimEnd("\") }
    [Environment]::SetEnvironmentVariable("Path", ($kept -join ";"), "User")
    Write-Host "Uninstalled VFetch."
}

# if/else instead of `exit`, so running via `irm ... | iex` does not close the terminal
if ($env:VFETCH_UNINSTALL -eq "1") { Uninstall-VFetch } else { Install-VFetch }
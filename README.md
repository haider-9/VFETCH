# VFETCH
![alt text](image.png)


VFetch is a cross-platform Python 3.9+ terminal front-end for yt-dlp. It supports Windows 10/11, macOS, and Linux, with profiles for best video, audio extraction, and custom format expressions.

## Install

Linux/macOS: `curl -fsSL https://raw.githubusercontent.com/haider-9/VFETCH/main/install.sh | bash`

Windows PowerShell: `irm https://raw.githubusercontent.com/haider-9/VFETCH/main/install.ps1 | iex`

Development install: `python -m pip install .` or `pipx install git+https://github.com/haider-9/VFETCH.git`.

The installers add a `vfetch` command:

- `ffmpeg` is installed before VFetch when it is missing. Linux uses the
  available `apt-get`, `dnf`, `pacman`, `zypper`, or `apk` package manager
  (with `sudo` when needed), macOS uses Homebrew, and Windows uses `winget`,
  Chocolatey, or Scoop. If no supported package manager is available, install
  `ffmpeg` and run the installer again.
- On Windows, it is installed under `%LOCALAPPDATA%\vfetch` and that folder is
  added to your user PATH. Restart PowerShell after installation, or run:
  ```powershell
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
  ```
  The installer recreates its private package directory on each install and
  works with redirected Microsoft Store Python installations.
- On Linux and macOS, it is installed as `~/.local/bin/vfetch`. If
  `vfetch` is not found, add that directory to your shell PATH permanently:
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```
  For zsh, use `~/.zshrc` instead:
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
  ```

After that, run VFetch from any terminal with:

```bash
vfetch
```

The URL prompt supports normal line editing: use the arrow keys to move the
cursor, and Backspace/Delete to edit a pasted URL.

The old bash install is backed up as `~/.local/bin/vfetch.bak-bash` by the installer.

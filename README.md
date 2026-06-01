# Rocket League Server Blocker

A small Windows GUI utility that uses `netsh advfirewall` to add or remove outbound firewall rules for placeholder Rocket League server IP ranges.

## Safety note

Changing firewall rules can affect matchmaking, voice chat, party connectivity, and other online services. Use this tool carefully and only with IP ranges you understand.

## Requirements

- Windows
- Python 3.10 or newer
- Administrator privileges to modify Windows Firewall

## Install and run from source

```powershell
pip install -r requirements.txt
python rl_server_blocker.py
```

If the app opens without administrator rights, the toggle will be disabled and the script will show an error message.

## Build a clickable admin app

Use the provided PyInstaller spec to create a Windows app that always requests administrator privileges when launched:

```powershell
pyinstaller rl_server_blocker.spec
```

When the build finishes, launch the EXE from the `dist\RLBlocker` folder. Windows will prompt for admin rights automatically.

## How the rules work

- The script defines placeholder server targets in `SERVER_TARGETS`.
- Turning the toggle ON adds outbound block rules.
- Turning the toggle OFF deletes those rules.
- Each rule is named with the `RL Blocker` prefix so it can be removed cleanly.
- You can optionally select a game `.exe` path and enable the checkbox to apply rules only to that executable.

## Do I need the game path?

- No. If you leave the path option disabled, the app blocks those target IP ranges system-wide.
- Yes, if you only want Rocket League traffic blocked while allowing other apps to still use those IP ranges.

## Build a .exe with PyInstaller

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Build the executable directly:

```powershell
pyinstaller --onefile --noconsole --uac-admin --name RLBlocker rl_server_blocker.py
```

3. Find the built app in:

```text
.dist\RLBlocker.exe
```

The `--uac-admin` flag asks Windows to launch the executable elevated, which is required for firewall changes. The included `rl_server_blocker.spec` uses the same admin requirement in a reproducible build file.

## Customizing targets

Edit `SERVER_TARGETS` in `rl_server_blocker.py` and replace the placeholder IP ranges with the ones you want to block or unblock.

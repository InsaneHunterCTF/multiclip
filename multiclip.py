#!/usr/bin/env python3
"""
MultiClip — multi-slot clipboard daemon with OS-aware clipboard backends.

This version auto-detects Linux vs macOS and uses the proper clipboard commands:
 - Linux: xclip (preferred) or wl-copy (Wayland) or pyperclip fallback
 - macOS: pbcopy / pbpaste
"""

import json
import os
import sys
import subprocess
import platform
import shutil
from datetime import datetime, timezone

import click

DATA_FILE = os.path.expanduser("~/.multiclip.json")



# Utilities

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_data():
    """
    Load persistent data safely. Ensure required keys exist.
    """
    if not os.path.exists(DATA_FILE):
        return {"slots": {}, "history": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"slots": {}, "history": []}

    data.setdefault("slots", {})
    data.setdefault("history", [])

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def has_cmd(name: str) -> bool:
    """Return True if command is available on PATH."""
    return shutil.which(name) is not None



# OS / Clipboard helpers

PLATFORM = platform.system()  # "Linux", "Darwin", "Windows", etc.


try:
    import pyperclip

    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False


def get_primary_selection() -> str:
    """
    Return the currently selected text.
    - Linux: try xclip PRIMARY, fallback to wl-paste --primary, fallback to clipboard
    - macOS: pbpaste (macOS doesn't have X11 PRIMARY, so use clipboard)
    """
    try:
        if PLATFORM == "Darwin":
            # macOS: use pbpaste to read clipboard (no PRIMARY)
            if has_cmd("pbpaste"):
                p = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return p.stdout.strip() if p.returncode == 0 else ""
            elif _HAS_PYPERCLIP:
                return pyperclip.paste() or ""
            else:
                return ""
        elif PLATFORM == "Linux":

            if has_cmd("xclip"):
                p = subprocess.run(
                    ["xclip", "-selection", "primary", "-o"], capture_output=True, text=True
                )
                if p.returncode == 0:
                    return p.stdout.strip()

            if has_cmd("wl-paste"):
                # wl-paste might support --primary; try it, else try default
                try:
                    p = subprocess.run(
                        ["wl-paste", "--primary"], capture_output=True, text=True, check=False
                    )
                    if p.returncode == 0:
                        return p.stdout.strip()
                except Exception:
                    pass

                p = subprocess.run(["wl-paste"], capture_output=True, text=True)
                if p.returncode == 0:
                    return p.stdout.strip()
            # Fallback to CLIPBOARD via xclip
            if has_cmd("xclip"):
                p = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True
                )
                if p.returncode == 0:
                    return p.stdout.strip()
            # Final fallback: pyperclip
            if _HAS_PYPERCLIP:
                return pyperclip.paste() or ""
            return ""
        else:

            if _HAS_PYPERCLIP:
                return pyperclip.paste() or ""
            return ""
    except Exception:
        return ""


def set_clipboard(text: str) -> None:
    """
    Set the system clipboard (and PRIMARY on Linux if possible).
    Uses the appropriate backend for each OS with safe fallbacks.
    """
    if text is None:
        text = ""

    try:
        if PLATFORM == "Darwin":
            # macOS: pbcopy writes to clipboard
            if has_cmd("pbcopy"):
                subprocess.run(["pbcopy"], input=text, text=True)
                return
            elif _HAS_PYPERCLIP:
                pyperclip.copy(text)
                return
            else:
                return
        elif PLATFORM == "Linux":
            # Prefer xclip (and also set PRIMARY), fallback to wl-copy, fallback to pyperclip
            if has_cmd("xclip"):
                # set CLIPBOARD
                subprocess.run(["xclip", "-selection", "clipboard", "-i"], input=text, text=True)
                # set PRIMARY too (so middle-click / selection-based pastes match)
                subprocess.run(["xclip", "-selection", "primary", "-i"], input=text, text=True)
                return
            if has_cmd("wl-copy"):
                # wl-copy for Wayland; try to set both CLIPBOARD and PRIMARY if supported
                try:
                    subprocess.run(["wl-copy"], input=text.encode(), check=False)
                except Exception:
                    try:
                        # fallback calling without bytes
                        subprocess.run(["wl-copy"], input=text, text=True, check=False)
                    except Exception:
                        pass
                
                try:
                    subprocess.run(["wl-copy", "--primary"], input=text.encode(), check=False)
                except Exception:
                    pass
                return
            # final fallback: pyperclip, if available
            if _HAS_PYPERCLIP:
                pyperclip.copy(text)
                return
            # nothing available — silent noop
            return
        else:
            # Other OS (Windows): try pyperclip
            if _HAS_PYPERCLIP:
                pyperclip.copy(text)
                return
            return
    except Exception:
        # swallow exceptions to keep daemon alive
        return



# CLI root

@click.group()
def cli():
    """MultiClip — multi-slot clipboard via global hotkeys"""
    pass



# Commands

@cli.command()
def list():
    """List stored clipboard slots"""
    data = load_data()
    if not data["slots"]:
        click.echo("No slots yet.")
        return

    for k, v in sorted(data["slots"].items()):
        preview = v["content"].replace("\n", " ")[:40]
        click.echo(f"{k}: {preview}")


@cli.command()
@click.argument("slot")
def clear(slot):
    """Clear a slot"""
    data = load_data()
    if slot in data["slots"]:
        del data["slots"][slot]
        save_data(data)
        click.echo(f"Cleared slot {slot}")
    else:
        click.echo("Slot not found")


@cli.command()
@click.argument("path")
def export(path):
    """Export data to JSON file"""
    save_data(load_data())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(load_data(), f, indent=2)
    click.echo("Exported successfully")


@cli.command(name="import")
@click.argument("path")
def import_slots(path):
    """Import data from JSON file"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("slots", {})
    data.setdefault("history", [])
    save_data(data)
    click.echo("Imported successfully")



# Daemon (the joker one)

@cli.command(context_settings={"ignore_unknown_options": True})
def daemon():
    """
    Start background daemon with predefined global hotkeys.
    NO ARGUMENTS ALLOWED.
    """
    try:
        from pynput import keyboard
    except ImportError:
        click.echo("Install dependencies: pip install pynput")
        sys.exit(1)

    # On Linux ensure at least one clipboard helper exists; on macOS it's not required
    if PLATFORM == "Linux":
        if not (has_cmd("xclip") or has_cmd("wl-copy") or _HAS_PYPERCLIP):
            click.echo("Install xclip or wl-clipboard (wl-copy) or ensure pyperclip is installed.")
            click.echo("Example (Debian/Ubuntu): sudo apt install xclip")
            sys.exit(1)

    # Predefined slots: A–Z and 1–9
    slots = {
        **{chr(c): (f"<ctrl>+{chr(c).lower()}", f"<alt>+{chr(c).lower()}") for c in range(65, 91)},
        **{str(n): (f"<ctrl>+{n}", f"<alt>+{n}") for n in range(1, 10)},
    }

    def assign(slot):
        text = get_primary_selection()
        if not text:
            log(f"{slot}: nothing selected")
            return

        data = load_data()
        data.setdefault("history", [])

        data["slots"][slot] = {
            "content": text,
            "time": utc_now(),
        }

        data["history"].append({
            "slot": slot,
            "content": text,
            "time": utc_now(),
        })

        save_data(data)
        log(f"{slot} ← {text[:60]}{'...' if len(text) > 60 else ''}")

    def paste(slot):
        data = load_data()
        if slot not in data["slots"]:
            log(f"{slot} is empty")
            return
        set_clipboard(data["slots"][slot]["content"])
        log(f"{slot} → clipboard")

    # Register hotkeys
    hotkeys = {}
    for slot, (assign_key, paste_key) in slots.items():
        # ensure no late-binding bug
        hotkeys[assign_key] = (lambda s=slot: assign(s))
        hotkeys[paste_key] = (lambda s=slot: paste(s))

    log(f"Daemon started – global hotkeys active (platform={PLATFORM})")
    log("Available slots:")
    for k, (a, p) in slots.items():
        log(f"  {k}: assign {a} | paste {p}")
    log("Press Ctrl+C to stop daemon")

    with keyboard.GlobalHotKeys(hotkeys) as h:
        h.join()



# Entry point

if __name__ == "__main__":
    cli()

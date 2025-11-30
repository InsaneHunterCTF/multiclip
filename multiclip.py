#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from datetime import datetime, timezone

import click

DATA_FILE = os.path.expanduser("~/.multiclip.json")



# Utilities


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_data():
    """
    Load persistent data safely.
    Handles older / corrupted JSON versions gracefully.
    """
    if not os.path.exists(DATA_FILE):
        return {"slots": {}, "history": []}

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return {"slots": {}, "history": []}


    data.setdefault("slots", {})
    data.setdefault("history", [])

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_primary_selection():
    """
    Read currently selected text (X11 PRIMARY selection).
    """
    try:
        p = subprocess.run(
            ["xclip", "-selection", "primary", "-o"],
            capture_output=True,
            text=True,
        )
        return p.stdout.strip() if p.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def set_clipboard(text):
    """
    Set system CLIPBOARD (Ctrl+V target).
    """
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text,
        text=True,
    )




@click.group()
def cli():
    """MultiClip — multi-slot clipboard via global hotkeys"""
    pass



# commands


@cli.command()
def list():
    """List stored clipboard slots"""
    data = load_data()

    if not data["slots"]:
        click.echo("No slots yet.")
        return

    for k, v in data["slots"].items():
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
    with open(path, "w") as f:
        json.dump(load_data(), f, indent=2)
    click.echo("Exported successfully")


@cli.command(name="import")
@click.argument("path")
def import_slots(path):
    """Import data from JSON file"""
    with open(path, "r") as f:
        data = json.load(f)


    data.setdefault("slots", {})
    data.setdefault("history", [])

    save_data(data)
    click.echo("Imported successfully")



# daemon command (the most important one)


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

    if subprocess.run(["which", "xclip"], capture_output=True).returncode != 0:
        click.echo("Install xclip first: sudo apt install xclip")
        sys.exit(1)


    # Predefined slots (I have defined all of keyboard slots instead of making the customer define them as you wanted)
    # all defined slots: 
    #    "A": ("<ctrl>+a", "<alt>+a"),
    #    "B": ("<ctrl>+b", "<alt>+b"),
    #    "C": ("<ctrl>+c", "<alt>+c"),
    #    "D": ("<ctrl>+d", "<alt>+d"),
    #    "E": ("<ctrl>+e", "<alt>+e"),
    #    "F": ("<ctrl>+f", "<alt>+f"),
    #    "G": ("<ctrl>+g", "<alt>+g"),
    #    "H": ("<ctrl>+h", "<alt>+h"),
    #    "I": ("<ctrl>+i", "<alt>+i"),
    #    "J": ("<ctrl>+j", "<alt>+j"),
    #    "K": ("<ctrl>+k", "<alt>+k"),
    #    "L": ("<ctrl>+l", "<alt>+l"),
    #    "M": ("<ctrl>+m", "<alt>+m"),
    #    "N": ("<ctrl>+n", "<alt>+n"),
    #    "O": ("<ctrl>+o", "<alt>+o"),
    #    "P": ("<ctrl>+p", "<alt>+p"),
    #    "Q": ("<ctrl>+q", "<alt>+q"),
    #    "R": ("<ctrl>+r", "<alt>+r"),
    #    "S": ("<ctrl>+s", "<alt>+s"),
    #    "T": ("<ctrl>+t", "<alt>+t"),
    #    "U": ("<ctrl>+u", "<alt>+u"),
    #    "V": ("<ctrl>+v", "<alt>+v"),
    #    "W": ("<ctrl>+w", "<alt>+w"),
    #    "X": ("<ctrl>+x", "<alt>+x"),
    #    "Y": ("<ctrl>+y", "<alt>+y"),
    #    "Z": ("<ctrl>+z", "<alt>+z"),
    #    "1": ("<ctrl>+1", "<alt>+1"),
    #    "2": ("<ctrl>+2", "<alt>+2"),
    #    "3": ("<ctrl>+3", "<alt>+3"),
    #    "4": ("<ctrl>+4", "<alt>+4"),
    #    "5": ("<ctrl>+5", "<alt>+5"),
    #    "6": ("<ctrl>+6", "<alt>+6"),
    #    "7": ("<ctrl>+7", "<alt>+7"),
    #    "8": ("<ctrl>+8", "<alt>+8"),
    #    "9": ("<ctrl>+9", "<alt>+9"),
    
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
        hotkeys[assign_key] = lambda s=slot: assign(s)
        hotkeys[paste_key] = lambda s=slot: paste(s)

    log("Daemon started – global hotkeys active")
    log("Available slots:")
    for k, (a, p) in slots.items():
        log(f"  {k}: assign {a} | paste {p}")

    log("Press Ctrl+C to stop daemon")

    with keyboard.GlobalHotKeys(hotkeys) as h:
        h.join()



if __name__ == "__main__":
    cli()
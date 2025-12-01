# Multiclip

MultiClip is a lightweight multi-slot clipboard manager that lets you copy multiple texts into different slots and paste any of them later using global keyboard shortcuts — without opening the terminal after startup.

Think of it as “multiple clipboards at once.”

## Features

- Multiple independent clipboard slots
- Global keyboard shortcuts (system-wide) (A-Z, 1-9)
- Works silently in the background (daemon mode)
- Persistent storage (saved across restarts)
- Export / import clipboard data
- Pure CLI tool — no GUI required
- Extremely fast & low resource usage

## Installation
### Linux:

``
sudo apt install xclip
``
``
pip install pynput click
``
``
git clone https://github.com/InsanceHunterCTF/multiclip.git
``
``
cd multiclip
``

### macOS:

``
xcode-select --install
``
``
pip install pynput click pyobjc
``
``
System Settings → Privacy & Security → Accessibility
``

## Usage Guide
To copy two separated texts, you will need to:

- normal copy text #1 with CTRL + C
- CTRL + any slot (e.g. slot A) on text #1
- do the same with text #2 with different slot (e.g. slot B)
- then do Alt + (slot A or B) to load either text from them
- CTRL + V will paste the text that you loaded with Alt

  ### Example Scenario:
  CTRL + C on text 'she is pretty' and CTRL + K on that text
  then CTRL + C on text 'he is ugly' and CTRL + G on that text
  Alt + K, and CTRL + V will paste the text 'she is pretty'
  and Alt + G, then CTRL + V will paste the text 'he is ugly'

# Usage Command:
``
python3 multiclip.py daemon
``

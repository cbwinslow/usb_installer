# Ventoy Flasher

**Ventoy Flasher** is a cross-platform (Linux/Windows) GUI tool designed for flashing USB drives with ISO images. It supports both traditional dd flashing and Ventoy-based flashing, while offering advanced features such as detailed USB drive information, reformatting (GPT/MBR), ISO hash validation, and multi-level logging—all wrapped in a neon green hacker-themed interface.

## Features

- **Cross-Platform Functionality:**  
  - Linux: Full support for operations like dd flashing, USB details retrieval (using `lsblk`), and reformatting.
  - Windows: Partial support with placeholders for dd operations and USB details.

- **Flashing Modes:**  
  - **dd Mode:** Flash an ISO image directly onto a USB drive.
  - **Ventoy Mode:** Install Ventoy onto a USB drive and copy ISO images for multi-boot capability.

- **Advanced USB Operations:**  
  - Retrieve comprehensive USB drive details (size, filesystem, partitions, model, etc.).
  - Reformat USB drives to either GPT or MBR partition schemes (destructive operation).

- **Predefined OS Installers:**  
  - Download ISO images for popular operating systems (Ubuntu, Fedora, Debian, Linux Mint, Pop!_OS, Manjaro, Arch Linux).  
  - The application validates download links on launch and (if possible) updates them automatically.

- **ISO Hash Validation:**  
  - Compute the SHA256 hash of a user-supplied ISO and compare it with the expected value (if available) to ensure integrity.

- **Multi-Level Logging:**  
  - Choose the level of detail in the logs (DEBUG, INFO, WARNING, ERROR) via the GUI’s menu.

- **Comprehensive Menu System:**  
  - File, Preferences, View, and Help menus provide common operations, including updating ISO links and setting logging levels.

- **Neon Hacker Theme:**  
  - Bright neon green (#39FF14) text on a black background for a striking visual experience.

## Prerequisites

- **Python 3.x**
- **PyQt5**  
  Install via pip:
  ```bash
  pip install PyQt5 requests

# Installation
git clone https://github.com/yourusername/usb_installer.git
cd usb_installer

# Usage
The project is split into two main modules:

backend.py: Contains all core functionality (flashing, reformatting, ISO validation, etc.).
gui.py: Contains the PyQt5 GUI, menus, and event handling logic.

# To Run the Code:
python gui.py

# Project Structure
usb_installer/
├── README.md
├── backend.py      # Core backend operations (FlashUtility, logging, etc.)
├── gui.py          # GUI implementation (VentoyFlasherGUI) and main entry point
└── LICENSE         # (If applicable)

Disclaimer
WARNING: Flashing and reformatting USB drives are destructive operations. Use this tool with caution—ensure you select the correct device and have backed up any important data. Administrative or sudo privileges may be required.




  

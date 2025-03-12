#!/usr/bin/env python3
r"""
File: usb_installer.py
Name: Your Name
Date: 2025-02-04
Purpose: Provide a cross-platform (Linux/Windows) GUI tool with a hacker theme for flashing USB drives.
         The tool supports dd flashing and Ventoy installation, displays USB details, allows reformatting,
         validates ISO files via hash checks, and provides multi‑level logging along with a full menu bar.
Description:
    - Detects the OS and adjusts commands accordingly.
    - dd mode flashes an ISO image to a USB drive; Ventoy mode installs Ventoy and copies an ISO.
    - The GUI is built with PyQt5, using bright neon green (#39FF14) on a black background.
    - Advanced features include retrieving USB properties, reformatting (GPT/MBR), ISO hash validation,
      link validation for predefined OS images, and a complete menu system.
Inputs:
    - USB device selection (populated on Linux via lsblk; editable)
    - Ventoy mount point (if using Ventoy mode)
    - ISO file selection (via file dialog or predefined OS list)
Outputs:
    - Logs, USB details, and status messages are shown in the GUI.
    - Flashing/installation and optional post‑operation validation.
File Path: usb_installer.py
"""

import sys
import os
import platform
import subprocess
import tempfile
import shutil
import json
import hashlib
import requests
import tarfile
import zipfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QPushButton, QLabel,
    QLineEdit, QListWidget, QTextEdit, QRadioButton, QHBoxLayout, QVBoxLayout,
    QButtonGroup, QMessageBox, QSplitter, QComboBox, QGroupBox, QAction
)
from PyQt5.QtCore import Qt

# ----------------------------
# Define logging levels as constants.
LOG_DEBUG = 10
LOG_INFO = 20
LOG_WARNING = 30
LOG_ERROR = 40

# ----------------------------
# Global dictionary for predefined OS installers.
# (Note: The hash values here are placeholders. Replace with actual expected SHA256 values.)
PREDEFINED_OS = {
    "Ubuntu": {
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04-desktop-amd64.iso",
        "hash": "dummyhash_ubuntu"
    },
    "Fedora": {
        "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/37/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-37-1.6.iso",
        "hash": "dummyhash_fedora"
    },
    "Debian": {
        "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-11.7.0-amd64-netinst.iso",
        "hash": "dummyhash_debian"
    },
    "Linux Mint": {
        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/21/linuxmint-21-cinnamon-64bit.iso",
        "hash": "dummyhash_linuxmint"
    },
    "Pop!_OS": {
        "url": "https://pop-iso.sfo2.cdn.digitaloceanspaces.com/22.04/Pop_OS_22.04_amd64_intel_60.iso",
        "hash": "dummyhash_popos"
    },
    "Manjaro": {
        "url": "https://download.manjaro.org/xfce/21.3.7/manjaro-xfce-21.3.7-210915-linux54.iso",
        "hash": "dummyhash_manjaro"
    },
    "Arch Linux": {
        "url": "https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso",
        "hash": "dummyhash_arch"
    }
}

# ----------------------------
# FlashUtility encapsulates OS‑dependent operations.
class FlashUtility:
    def __init__(self, log_callback=None):
        self.os_type = platform.system()
        self.log_callback = log_callback
        self.temp_dir = tempfile.mkdtemp(prefix="ventoy_")
        self.log(f"Temporary directory created at {self.temp_dir}", LOG_DEBUG)

    def log(self, message, level=LOG_INFO):
        """Log a message via the provided callback (if any)."""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(message)

    def run_dd_command(self, iso_path, usb_device):
        try:
            if self.os_type == "Linux":
                command = f"sudo dd if={iso_path} of={usb_device} bs=4M status=progress && sync"
                self.log(f"Running dd command: {command}", LOG_INFO)
                subprocess.run(command, shell=True, check=True)
                self.log("Flashing complete using dd.", LOG_INFO)
            elif self.os_type == "Windows":
                self.log("dd command is not natively supported on Windows. Please install a dd equivalent.", LOG_WARNING)
            else:
                self.log("Unsupported OS for dd flashing.", LOG_ERROR)
        except subprocess.CalledProcessError as e:
            self.log(f"Error during flashing: {e}", LOG_ERROR)
        except Exception as ex:
            self.log(f"Unexpected error: {ex}", LOG_ERROR)

    def download_file(self, url, dest_filename):
        dest_path = os.path.join(self.temp_dir, dest_filename)
        self.log(f"Downloading from {url} to {dest_path}", LOG_INFO)
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            self.log(f"Download complete: {dest_path}", LOG_INFO)
            return dest_path
        except requests.RequestException as e:
            self.log(f"Error downloading file: {e}", LOG_ERROR)
            return None

    def extract_archive(self, archive_path, extract_to):
        self.log(f"Extracting {archive_path} to {extract_to}", LOG_INFO)
        try:
            if archive_path.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(path=extract_to)
            elif archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(path=extract_to)
            else:
                self.log("Unsupported archive format.", LOG_WARNING)
                return False
            self.log("Extraction complete.", LOG_INFO)
            return True
        except Exception as ex:
            self.log(f"Extraction error: {ex}", LOG_ERROR)
            return False

    def install_ventoy(self, usb_device):
        try:
            ventoy_url = VENTOY_URLS.get(self.os_type)
            if not ventoy_url:
                self.log("No Ventoy download available for this OS.", LOG_ERROR)
                return

            archive_filename = os.path.basename(ventoy_url)
            ventoy_archive = self.download_file(ventoy_url, archive_filename)
            if not ventoy_archive:
                self.log("Ventoy download failed.", LOG_ERROR)
                return

            ventoy_extract_path = os.path.join(self.temp_dir, "ventoy_extracted")
            os.makedirs(ventoy_extract_path, exist_ok=True)
            if not self.extract_archive(ventoy_archive, ventoy_extract_path):
                self.log("Ventoy extraction failed.", LOG_ERROR)
                return

            if self.os_type == "Linux":
                ventoy_script = os.path.join(ventoy_extract_path, "Ventoy2Disk.sh")
                if not os.path.exists(ventoy_script):
                    self.log("Ventoy installation script not found.", LOG_ERROR)
                    return
                command = f"sudo sh {ventoy_script} -i {usb_device} -I"
                self.log(f"Installing Ventoy with command: {command}", LOG_INFO)
                subprocess.run(command, shell=True, check=True)
                self.log("Ventoy installation complete.", LOG_INFO)
            elif self.os_type == "Windows":
                ventoy_exe = os.path.join(ventoy_extract_path, "Ventoy2Disk.exe")
                if not os.path.exists(ventoy_exe):
                    self.log("Ventoy installation executable not found.", LOG_ERROR)
                    return
                command = f'"{ventoy_exe}" -i {usb_device} -I'
                self.log(f"Installing Ventoy with command: {command}", LOG_INFO)
                subprocess.run(command, shell=True, check=True)
                self.log("Ventoy installation complete on Windows.", LOG_INFO)
            else:
                self.log("Unsupported OS for Ventoy installation.", LOG_ERROR)
        except subprocess.CalledProcessError as e:
            self.log(f"Error during Ventoy installation: {e}", LOG_ERROR)
        except Exception as ex:
            self.log(f"Unexpected error during Ventoy installation: {ex}", LOG_ERROR)

    def copy_iso_to_ventoy(self, iso_path, ventoy_mount_point):
        try:
            if not os.path.exists(ventoy_mount_point):
                self.log("Ventoy mount point does not exist.", LOG_ERROR)
                return
            dest_path = os.path.join(ventoy_mount_point, os.path.basename(iso_path))
            self.log(f"Copying ISO from {iso_path} to {dest_path}", LOG_INFO)
            shutil.copy2(iso_path, dest_path)
            self.log("ISO file successfully copied to Ventoy drive.", LOG_INFO)
        except Exception as ex:
            self.log(f"Error copying ISO file: {ex}", LOG_ERROR)

    def reformat_usb(self, usb_device, scheme):
        try:
            if self.os_type == "Linux":
                if scheme.lower() == "gpt":
                    command = f"sudo parted {usb_device} mklabel gpt"
                elif scheme.lower() == "mbr":
                    command = f"sudo parted {usb_device} mklabel msdos"
                else:
                    self.log("Unknown partition scheme.", LOG_ERROR)
                    return
                self.log(f"Reformatting USB drive with command: {command}", LOG_INFO)
                subprocess.run(command, shell=True, check=True)
                self.log("USB drive reformatted successfully.", LOG_INFO)
            elif self.os_type == "Windows":
                self.log("Reformatting USB drive is not implemented for Windows.", LOG_WARNING)
            else:
                self.log("Unsupported OS for reformatting.", LOG_ERROR)
        except subprocess.CalledProcessError as e:
            self.log(f"Error during reformatting: {e}", LOG_ERROR)
        except Exception as ex:
            self.log(f"Unexpected error: {ex}", LOG_ERROR)

    def get_usb_details(self, usb_device):
        try:
            if self.os_type == "Linux":
                result = subprocess.run(["lsblk", "-o", "NAME,FSTYPE,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL"], capture_output=True, text=True, check=True)
                details = result.stdout.strip()
                return details
            elif self.os_type == "Windows":
                return "USB details not implemented for Windows."
            else:
                return "Unsupported OS."
        except Exception as ex:
            return f"Error retrieving USB details: {ex}"

    def compute_sha256(self, file_path):
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as ex:
            self.log(f"Error computing hash: {ex}", LOG_ERROR)
            return None

    def cleanup(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log("Cleaned up temporary files.", LOG_DEBUG)
        except Exception as ex:
            self.log(f"Error during cleanup: {ex}", LOG_ERROR)

# ----------------------------
# Main GUI class with menus, logging options, and full functionality.
class VentoyFlasherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventoy Flasher")
        self.setGeometry(100, 100, 1000, 700)
        # Neon green text on a black background.
        self.setStyleSheet("background-color: black; color: #39FF14; font-family: 'Courier New'; font-size: 12px;")
        # Default logging level is INFO.
        self.log_level = LOG_INFO

        self.initUI()
        self.flash_util = FlashUtility(log_callback=self.log_message)
        self.validate_os_links()
        self.create_menu()

    def create_menu(self):
        """Create the menu bar with File, Edit, View, and Help menus."""
        menubar = self.menuBar()

        # --- File Menu ---
        file_menu = menubar.addMenu("File")
        update_links_action = QAction("Update ISO Links", self)
        update_links_action.triggered.connect(self.update_iso_links)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(update_links_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # --- Edit/Preferences Menu ---
        pref_menu = menubar.addMenu("Preferences")
        # You can add more preference actions here.
        # For example, an action to manually update the PREDEFINED_OS dictionary.
        update_dict_action = QAction("Manually Update OS Dictionary", self)
        update_dict_action.triggered.connect(self.update_iso_links)
        pref_menu.addAction(update_dict_action)

        # --- View Menu (for Logging Level) ---
        view_menu = menubar.addMenu("View")
        log_level_menu = view_menu.addMenu("Logging Level")
        debug_action = QAction("Debug", self, checkable=True)
        info_action = QAction("Info", self, checkable=True)
        warning_action = QAction("Warning", self, checkable=True)
        error_action = QAction("Error", self, checkable=True)
        # Set default selection (INFO)
        info_action.setChecked(True)
        debug_action.triggered.connect(lambda: self.set_log_level(LOG_DEBUG))
        info_action.triggered.connect(lambda: self.set_log_level(LOG_INFO))
        warning_action.triggered.connect(lambda: self.set_log_level(LOG_WARNING))
        error_action.triggered.connect(lambda: self.set_log_level(LOG_ERROR))
        log_level_menu.addAction(debug_action)
        log_level_menu.addAction(info_action)
        log_level_menu.addAction(warning_action)
        log_level_menu.addAction(error_action)

        # --- Help Menu ---
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        doc_action = QAction("Documentation", self)
        doc_action.triggered.connect(self.show_documentation)
        help_menu.addAction(about_action)
        help_menu.addAction(doc_action)

    def set_log_level(self, level):
        """Set the logging level and log the change."""
        self.log_level = level
        level_name = {LOG_DEBUG: "DEBUG", LOG_INFO: "INFO", LOG_WARNING: "WARNING", LOG_ERROR: "ERROR"}.get(level, "INFO")
        self.log_message(f"Logging level set to {level_name}.", LOG_INFO)

    def show_about(self):
        """Display an About dialog."""
        QMessageBox.information(self, "About Ventoy Flasher",
                                "Ventoy Flasher\nVersion 1.0\nDeveloped for flashing USB drives safely and efficiently.",
                                QMessageBox.Ok)

    def show_documentation(self):
        """Display a Documentation dialog."""
        QMessageBox.information(self, "Documentation",
                                "Please refer to the README.md on GitHub for detailed documentation.",
                                QMessageBox.Ok)

    def update_iso_links(self):
        """
        Update the ISO links in the PREDEFINED_OS dictionary.
        (This is an experimental stub. In a more complete implementation you might parse vendor metadata.)
        """
        self.log_message("Updating ISO links...", LOG_INFO)
        for os_name, info in list(PREDEFINED_OS.items()):
            url = info.get("url")
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code != 200:
                    self.log_message(f"Link for {os_name} is broken (status {response.status_code}).", LOG_WARNING)
                    # Here you might try a heuristic update. For now, we simply remove the OS.
                    PREDEFINED_OS.pop(os_name)
                    # Also remove from the distro list.
                    for i in range(self.distro_list.count()):
                        if self.distro_list.item(i).text() == os_name:
                            self.distro_list.takeItem(i)
                            break
            except Exception as ex:
                self.log_message(f"Error updating link for {os_name}: {ex}", LOG_ERROR)
                PREDEFINED_OS.pop(os_name)
                for i in range(self.distro_list.count()):
                    if self.distro_list.item(i).text() == os_name:
                        self.distro_list.takeItem(i)
                        break
        self.log_message("ISO links update complete.", LOG_INFO)

    def initUI(self):
        """Initialize and arrange widgets."""
        # Mode selection
        self.dd_mode_radio = QRadioButton("Standard dd Flash")
        self.ventoy_mode_radio = QRadioButton("Ventoy Mode")
        self.dd_mode_radio.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.dd_mode_radio)
        self.mode_group.addButton(self.ventoy_mode_radio)
        self.mode_group.buttonClicked.connect(self.toggle_mode)

        # USB device selection
        self.usb_device_label = QLabel(r"USB Device (e.g., /dev/sdx or \\.\PhysicalDriveN):")
        self.usb_device_combo = QComboBox()
        self.usb_device_combo.setEditable(True)
        self.usb_device_combo.currentTextChanged.connect(self.update_usb_device_text)
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.populate_usb_devices)

        # Ventoy mount point input
        self.ventoy_mount_label = QLabel("Ventoy USB Mount Point (e.g., E:\\ on Windows or /mnt/ventoy on Linux):")
        self.ventoy_mount_input = QLineEdit()
        self.ventoy_mount_input.setDisabled(True)

        # ISO selection
        self.select_iso_btn = QPushButton("Select ISO File")
        self.select_iso_btn.clicked.connect(self.select_iso_file)
        self.selected_iso_path = ""

        # Predefined OS list
        self.distro_list = QListWidget()
        for os_name in PREDEFINED_OS.keys():
            self.distro_list.addItem(os_name)
        self.distro_list.itemClicked.connect(self.select_distro)

        # Flash and Ventoy buttons
        self.flash_btn = QPushButton("Flash USB")
        self.flash_btn.clicked.connect(self.flash_usb)
        self.install_ventoy_btn = QPushButton("Install Ventoy")
        self.install_ventoy_btn.clicked.connect(self.install_ventoy)

        # Advanced USB operations: USB details, reformat, and ISO validation.
        self.usb_details_btn = QPushButton("Get USB Details")
        self.usb_details_btn.clicked.connect(self.get_usb_details)
        self.usb_details_output = QTextEdit()
        self.usb_details_output.setReadOnly(True)
        self.usb_details_output.setPlaceholderText("USB details will appear here...")
        self.reformat_combo = QComboBox()
        self.reformat_combo.addItems(["GPT", "MBR"])
        self.reformat_btn = QPushButton("Reformat USB")
        self.reformat_btn.clicked.connect(self.reformat_usb)
        self.validate_iso_btn = QPushButton("Validate ISO")
        self.validate_iso_btn.clicked.connect(self.validate_iso)

        # Log output pane
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # Status pane for warnings and recommendations
        self.status_pane = QTextEdit()
        self.status_pane.setReadOnly(True)
        self.status_pane.setFixedHeight(80)
        self.status_pane.setStyleSheet("background-color: #222; color: #FF4500;")

        # Layout configuration
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.dd_mode_radio)
        mode_layout.addWidget(self.ventoy_mode_radio)

        device_selection_layout = QHBoxLayout()
        device_selection_layout.addWidget(self.usb_device_combo)
        device_selection_layout.addWidget(self.refresh_btn)

        device_layout = QVBoxLayout()
        device_layout.addWidget(self.usb_device_label)
        device_layout.addLayout(device_selection_layout)
        device_layout.addWidget(self.ventoy_mount_label)
        device_layout.addWidget(self.ventoy_mount_input)

        iso_layout = QVBoxLayout()
        iso_layout.addWidget(self.select_iso_btn)
        iso_layout.addWidget(QLabel("Predefined OS Installers:"))
        iso_layout.addWidget(self.distro_list)

        advanced_group = QGroupBox("Advanced USB Operations")
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(self.usb_details_btn)
        advanced_layout.addWidget(self.usb_details_output)
        reformat_layout = QHBoxLayout()
        reformat_layout.addWidget(QLabel("Reformat as:"))
        reformat_layout.addWidget(self.reformat_combo)
        reformat_layout.addWidget(self.reformat_btn)
        advanced_layout.addLayout(reformat_layout)
        advanced_layout.addWidget(self.validate_iso_btn)
        advanced_group.setLayout(advanced_layout)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addLayout(mode_layout)
        left_layout.addLayout(device_layout)
        left_layout.addLayout(iso_layout)
        left_layout.addWidget(self.flash_btn)
        left_layout.addWidget(self.install_ventoy_btn)
        left_layout.addWidget(advanced_group)
        left_panel.setLayout(left_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.log_output)
        splitter.setSizes([350, 650])

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.status_pane)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        if platform.system() == "Linux":
            self.populate_usb_devices()

    def update_usb_device_text(self, text):
        """Placeholder for additional logic on USB device selection changes."""
        pass

    def populate_usb_devices(self):
        self.usb_device_combo.clear()
        try:
            result = subprocess.run(["lsblk", "-J", "-o", "NAME,TYPE,SIZE,MODEL"], capture_output=True, text=True, check=True)
            lsblk_json = json.loads(result.stdout)
            devices = lsblk_json.get("blockdevices", [])
            for dev in devices:
                if dev.get("type") == "disk":
                    name = dev.get("name")
                    size = dev.get("size")
                    model = dev.get("model") or "Unknown Model"
                    device_entry = f"/dev/{name} – {model} ({size})"
                    self.usb_device_combo.addItem(device_entry)
            self.log_message("USB devices list updated.", LOG_INFO)
        except Exception as ex:
            self.log_message(f"Error retrieving USB devices: {ex}", LOG_ERROR)

    def validate_os_links(self):
        """Validate the download URLs for predefined OS images."""
        to_remove = []
        for os_name, info in list(PREDEFINED_OS.items()):
            url = info.get("url")
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code != 200:
                    self.log_message(f"Warning: URL for {os_name} returned status {response.status_code}. Removing from options.", LOG_WARNING)
                    to_remove.append(os_name)
            except Exception as ex:
                self.log_message(f"Error validating URL for {os_name}: {ex}. Removing from options.", LOG_ERROR)
                to_remove.append(os_name)
        for os_name in to_remove:
            PREDEFINED_OS.pop(os_name, None)
            for i in range(self.distro_list.count()):
                if self.distro_list.item(i).text() == os_name:
                    self.distro_list.takeItem(i)
                    break

    def toggle_mode(self):
        if self.ventoy_mode_radio.isChecked():
            self.usb_device_combo.setDisabled(True)
            self.refresh_btn.setDisabled(True)
            self.ventoy_mount_input.setDisabled(False)
        else:
            self.usb_device_combo.setDisabled(False)
            self.refresh_btn.setDisabled(False)
            self.ventoy_mount_input.setDisabled(True)

    def select_iso_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ISO File", "", "ISO Files (*.iso);;All Files (*)", options=options)
        if file_path:
            self.selected_iso_path = file_path
            self.log_message(f"Selected ISO file: {file_path}", LOG_INFO)

    def select_distro(self, item):
        os_name = item.text()
        info = PREDEFINED_OS.get(os_name)
        if info:
            url = info.get("url")
            self.log_message(f"Downloading {os_name} ISO from {url}...", LOG_INFO)
            iso_path = self.flash_util.download_file(url, f"{os_name}.iso")
            if iso_path:
                self.selected_iso_path = iso_path
                self.log_message(f"{os_name} ISO downloaded and selected: {iso_path}", LOG_INFO)
            else:
                self.log_message(f"Failed to download {os_name} ISO.", LOG_ERROR)

    def flash_usb(self):
        if not self.selected_iso_path:
            self.log_message("Please select an ISO file first.", LOG_WARNING)
            return

        if self.dd_mode_radio.isChecked():
            usb_device = self.usb_device_combo.currentText().strip().split()[0]
            if not usb_device:
                self.log_message("Please select the USB device from the dropdown.", LOG_WARNING)
                return
            self.log_message("Starting dd flashing process...", LOG_INFO)
            self.flash_util.run_dd_command(self.selected_iso_path, usb_device)
            self.validate_operation(usb_device)
        elif self.ventoy_mode_radio.isChecked():
            ventoy_mount = self.ventoy_mount_input.text().strip()
            if not ventoy_mount:
                self.log_message("Please specify the Ventoy USB mount point (e.g., E:\\ or /mnt/ventoy).", LOG_WARNING)
                return
            self.log_message("Copying ISO file to Ventoy drive...", LOG_INFO)
            self.flash_util.copy_iso_to_ventoy(self.selected_iso_path, ventoy_mount)
            self.validate_operation(ventoy_mount)
        else:
            self.log_message("Unknown flashing mode selected.", LOG_ERROR)

    def install_ventoy(self):
        if self.dd_mode_radio.isChecked():
            self.log_message("Ventoy installation is only available in Ventoy mode. Please select Ventoy Mode.", LOG_WARNING)
            return
        ventoy_target = self.ventoy_mount_input.text().strip()
        if not ventoy_target:
            self.log_message("Please specify the Ventoy USB mount point or device identifier.", LOG_WARNING)
            return
        self.log_message("Starting Ventoy installation...", LOG_INFO)
        self.flash_util.install_ventoy(ventoy_target)

    def reformat_usb(self):
        usb_device = self.usb_device_combo.currentText().strip().split()[0]
        if not usb_device:
            self.log_message("Please select a USB device to reformat.", LOG_WARNING)
            return
        scheme = self.reformat_combo.currentText()
        reply = QMessageBox.warning(self, "Warning: Reformat USB",
                                    f"WARNING: Reformatting {usb_device} as {scheme} will erase all data.\nDo you want to continue?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.flash_util.reformat_usb(usb_device, scheme)
        else:
            self.log_message("Reformatting canceled.", LOG_INFO)

    def get_usb_details(self):
        usb_device = self.usb_device_combo.currentText().strip().split()[0]
        if not usb_device:
            self.log_message("Please select a USB device first.", LOG_WARNING)
            return
        details = self.flash_util.get_usb_details(usb_device)
        self.usb_details_output.setPlainText(details)

    def validate_iso(self):
        if not self.selected_iso_path:
            self.log_message("Please select an ISO file first.", LOG_WARNING)
            return
        computed_hash = self.flash_util.compute_sha256(self.selected_iso_path)
        if not computed_hash:
            self.log_message("Failed to compute ISO hash.", LOG_ERROR)
            return
        iso_name = os.path.basename(self.selected_iso_path)
        found = False
        for os_name, info in PREDEFINED_OS.items():
            if os_name.lower() in iso_name.lower():
                found = True
                expected_hash = info.get("hash")
                if computed_hash == expected_hash:
                    self.log_message(f"ISO validation passed for {os_name}.", LOG_INFO)
                else:
                    self.log_message(f"WARNING: ISO hash for {os_name} does not match expected value!", LOG_WARNING)
                    self.status_pane.append(f"WARNING: {os_name} ISO hash mismatch. Expected: {expected_hash}, Got: {computed_hash}")
                break
        if not found:
            self.log_message("No expected hash available for this ISO. Please verify manually.", LOG_WARNING)

    def validate_operation(self, target):
        try:
            self.log_message(f"Validating operation on target: {target} ... (not fully implemented)", LOG_DEBUG)
        except Exception as ex:
            self.log_message(f"Validation error: {ex}", LOG_ERROR)

    def log_message(self, message, level=LOG_INFO):
        """Append a message to the log output pane if the message's level is at or above the current log level."""
        if level >= self.log_level:
            level_name = {LOG_DEBUG: "DEBUG", LOG_INFO: "INFO", LOG_WARNING: "WARNING", LOG_ERROR: "ERROR"}.get(level, "INFO")
            self.log_output.append(f"[{level_name}] {message}")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit Confirmation',
                                     "Are you sure you want to exit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.flash_util.cleanup()
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    window = VentoyFlasherGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

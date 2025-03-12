#!/usr/bin/env python3
r"""
File: gui.py
Name: Your Name
Date: 2025-03-12
Purpose: Graphical User Interface (GUI) module for the Ventoy Flasher application.
         Separates all user interface logic from the core backend functionality.
Description:
    - Implements the VentoyFlasherGUI class using PyQt5.
    - Provides a neon green hacker-themed interface with menus (File, Preferences, View, Help).
    - Supports multi-level logging, USB device selection, flashing modes (dd and Ventoy),
      advanced USB operations (details, reformat, ISO validation), and dynamic updating of ISO links.
    - Imports core operations from backend.py.
Usage:
    Run this file to start the Ventoy Flasher GUI application:
    $ python gui.py
"""

import sys
import os
import platform
import subprocess
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QPushButton, QLabel,
    QLineEdit, QListWidget, QTextEdit, QRadioButton, QHBoxLayout, QVBoxLayout,
    QButtonGroup, QMessageBox, QSplitter, QComboBox, QGroupBox, QAction
)
from PyQt5.QtCore import Qt

# Import backend functionality and constants.
from backend import FlashUtility, LOG_DEBUG, LOG_INFO, LOG_WARNING, LOG_ERROR, PREDEFINED_OS, VENTOY_URLS

class VentoyFlasherGUI(QMainWindow):
    """
    VentoyFlasherGUI implements the graphical interface for flashing USB drives.
    It uses the FlashUtility class from backend.py to perform operations and displays
    logging output and status messages.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ventoy Flasher")
        self.setGeometry(100, 100, 1000, 700)
        # Apply neon green (#39FF14) text on a black background.
        self.setStyleSheet("background-color: black; color: #39FF14; font-family: 'Courier New'; font-size: 12px;")
        # Default logging level is INFO.
        self.log_level = LOG_INFO

        self.initUI()
        self.flash_util = FlashUtility(log_callback=self.log_message)
        self.validate_os_links()
        self.create_menu()

    def create_menu(self):
        """
        Create the menu bar with File, Preferences, View, and Help menus.
        Provides actions for updating ISO links, changing logging levels, and viewing documentation.
        """
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

        # --- Preferences Menu ---
        pref_menu = menubar.addMenu("Preferences")
        update_dict_action = QAction("Manually Update OS Dictionary", self)
        update_dict_action.triggered.connect(self.update_iso_links)
        pref_menu.addAction(update_dict_action)

        # --- View Menu (Logging Level) ---
        view_menu = menubar.addMenu("View")
        log_level_menu = view_menu.addMenu("Logging Level")
        debug_action = QAction("Debug", self, checkable=True)
        info_action = QAction("Info", self, checkable=True)
        warning_action = QAction("Warning", self, checkable=True)
        error_action = QAction("Error", self, checkable=True)
        # Default selection: INFO.
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
        """Set the current logging level and log the change."""
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
                                "Refer to the README.md on GitHub for detailed documentation.",
                                QMessageBox.Ok)

    def update_iso_links(self):
        """
        Update the ISO links in the PREDEFINED_OS dictionary.
        Currently, this function re-validates the URLs and removes any that are unreachable.
        """
        self.log_message("Updating ISO links...", LOG_INFO)
        for os_name, info in list(PREDEFINED_OS.items()):
            url = info.get("url")
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code != 200:
                    self.log_message(f"Link for {os_name} returned status {response.status_code}. Removing option.", LOG_WARNING)
                    PREDEFINED_OS.pop(os_name)
                    # Remove from distro list widget.
                    for i in range(self.distro_list.count()):
                        if self.distro_list.item(i).text() == os_name:
                            self.distro_list.takeItem(i)
                            break
            except Exception as ex:
                self.log_message(f"Error validating link for {os_name}: {ex}. Removing option.", LOG_ERROR)
                PREDEFINED_OS.pop(os_name)
                for i in range(self.distro_list.count()):
                    if self.distro_list.item(i).text() == os_name:
                        self.distro_list.takeItem(i)
                        break
        self.log_message("ISO links update complete.", LOG_INFO)

    def initUI(self):
        """Initialize and arrange GUI widgets."""
        # --- Mode Selection ---
        self.dd_mode_radio = QRadioButton("Standard dd Flash")
        self.ventoy_mode_radio = QRadioButton("Ventoy Mode")
        self.dd_mode_radio.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.dd_mode_radio)
        self.mode_group.addButton(self.ventoy_mode_radio)
        self.mode_group.buttonClicked.connect(self.toggle_mode)

        # --- USB Device Selection ---
        self.usb_device_label = QLabel(r"USB Device (e.g., /dev/sdx or \\.\PhysicalDriveN):")
        self.usb_device_combo = QComboBox()
        self.usb_device_combo.setEditable(True)
        self.usb_device_combo.currentTextChanged.connect(self.update_usb_device_text)
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.populate_usb_devices)

        # --- Ventoy Mount Point ---
        self.ventoy_mount_label = QLabel("Ventoy USB Mount Point (e.g., E:\\ on Windows or /mnt/ventoy on Linux):")
        self.ventoy_mount_input = QLineEdit()
        self.ventoy_mount_input.setDisabled(True)

        # --- ISO File Selection ---
        self.select_iso_btn = QPushButton("Select ISO File")
        self.select_iso_btn.clicked.connect(self.select_iso_file)
        self.selected_iso_path = ""

        # --- Predefined OS List ---
        self.distro_list = QListWidget()
        for os_name in PREDEFINED_OS.keys():
            self.distro_list.addItem(os_name)
        self.distro_list.itemClicked.connect(self.select_distro)

        # --- Flash and Ventoy Buttons ---
        self.flash_btn = QPushButton("Flash USB")
        self.flash_btn.clicked.connect(self.flash_usb)
        self.install_ventoy_btn = QPushButton("Install Ventoy")
        self.install_ventoy_btn.clicked.connect(self.install_ventoy)

        # --- Advanced USB Operations ---
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

        # --- Log Output Pane ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # --- Status Pane (Warnings/Recommendations) ---
        self.status_pane = QTextEdit()
        self.status_pane.setReadOnly(True)
        self.status_pane.setFixedHeight(80)
        self.status_pane.setStyleSheet("background-color: #222; color: #FF4500;")

        # --- Layouts ---
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

        # Populate USB devices if on Linux.
        if platform.system() == "Linux":
            self.populate_usb_devices()

    def update_usb_device_text(self, text):
        """Placeholder for additional actions when the USB device selection changes."""
        pass

    def populate_usb_devices(self):
        """Populate the USB device combo box using lsblk (Linux only)."""
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
        """
        Validate download URLs for predefined OS images.
        If a URL is unreachable, remove the option from the dictionary and UI.
        """
        to_remove = []
        for os_name, info in list(PREDEFINED_OS.items()):
            url = info.get("url")
            try:
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code != 200:
                    self.log_message(f"Warning: URL for {os_name} returned status {response.status_code}. Removing option.", LOG_WARNING)
                    to_remove.append(os_name)
            except Exception as ex:
                self.log_message(f"Error validating URL for {os_name}: {ex}. Removing option.", LOG_ERROR)
                to_remove.append(os_name)
        for os_name in to_remove:
            PREDEFINED_OS.pop(os_name, None)
            for i in range(self.distro_list.count()):
                if self.distro_list.item(i).text() == os_name:
                    self.distro_list.takeItem(i)
                    break

    def toggle_mode(self):
        """Enable or disable widgets based on the selected flashing mode."""
        if self.ventoy_mode_radio.isChecked():
            self.usb_device_combo.setDisabled(True)
            self.refresh_btn.setDisabled(True)
            self.ventoy_mount_input.setDisabled(False)
        else:
            self.usb_device_combo.setDisabled(False)
            self.refresh_btn.setDisabled(False)
            self.ventoy_mount_input.setDisabled(True)

    def select_iso_file(self):
        """Open a file dialog to allow the user to select an ISO file."""
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ISO File", "", "ISO Files (*.iso);;All Files (*)", options=options)
        if file_path:
            self.selected_iso_path = file_path
            self.log_message(f"Selected ISO file: {file_path}", LOG_INFO)

    def select_distro(self, item):
        """
        When a predefined OS is selected, download its ISO using the URL from PREDEFINED_OS.
        """
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
        """
        Depending on the selected mode, flash the USB drive:
          - In dd mode, run the dd command.
          - In Ventoy mode, copy the ISO file to the Ventoy partition.
        """
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
        """
        Install Ventoy onto the USB drive (only available in Ventoy mode).
        """
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
        """
        Reformat the selected USB drive using the chosen partition scheme (GPT/MBR).
        Displays a confirmation dialog before proceeding.
        """
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
        """
        Retrieve detailed USB drive information and display it in the USB details pane.
        """
        usb_device = self.usb_device_combo.currentText().strip().split()[0]
        if not usb_device:
            self.log_message("Please select a USB device first.", LOG_WARNING)
            return
        details = self.flash_util.get_usb_details(usb_device)
        self.usb_details_output.setPlainText(details)

    def validate_iso(self):
        """
        Validate the selected ISO by computing its SHA256 hash and comparing it with the expected value,
        if available in PREDEFINED_OS. Otherwise, prompt the user to verify manually.
        """
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
        """
        Stub for post-operation validation. Could include additional checks (e.g., comparing device hash).
        """
        try:
            self.log_message(f"Validating operation on target: {target} ... (not fully implemented)", LOG_DEBUG)
        except Exception as ex:
            self.log_message(f"Validation error: {ex}", LOG_ERROR)

    def log_message(self, message, level=LOG_INFO):
        """
        Append a log message to the log output pane if its level is equal to or above the current log level.
        """
        if level >= self.log_level:
            level_name = {LOG_DEBUG: "DEBUG", LOG_INFO: "INFO", LOG_WARNING: "WARNING", LOG_ERROR: "ERROR"}.get(level, "INFO")
            self.log_output.append(f"[{level_name}] {message}")

    def closeEvent(self, event):
        """
        Overridden close event: Confirm exit and clean up temporary files.
        """
        reply = QMessageBox.question(self, 'Exit Confirmation',
                                     "Are you sure you want to exit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.flash_util.cleanup()
            event.accept()
        else:
            event.ignore()

def main():
    """Main entry point for the Ventoy Flasher GUI application."""
    app = QApplication(sys.argv)
    window = VentoyFlasherGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

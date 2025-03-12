#!/usr/bin/env python3
r"""
File: backend.py
Name: Your Name
Date: 2025-03-12
Purpose: Core backend module for the Ventoy Flasher application.
         Provides cross-platform functions for flashing USB drives with ISO images,
         installing Ventoy, retrieving USB details, reformatting drives, computing hash
         values, and downloading/extracting files. Also includes multi-level logging.
Description:
    - Implements the FlashUtility class, which encapsulates OS-dependent operations.
    - Contains global constants for logging levels and a dictionary (PREDEFINED_OS)
      with download URLs and expected SHA256 hash placeholders for many Linux/Unix distributions.
    - All functions include detailed docstrings, error handling, and logging.
Variables:
    LOG_DEBUG, LOG_INFO, LOG_WARNING, LOG_ERROR: Logging level constants.
    PREDEFINED_OS: Dictionary mapping OS names to download metadata.
    VENTOY_URLS: Dictionary containing download URLs for Ventoy (Linux and Windows).
Usage:
    Import this module in your GUI application (or other code) and instantiate FlashUtility.
"""

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

# ----------------------------
# Logging level constants.
LOG_DEBUG = 10
LOG_INFO = 20
LOG_WARNING = 30
LOG_ERROR = 40

# ----------------------------
# Predefined OS installers dictionary.
# Update the 'hash' values with the actual expected SHA256 hashes.
PREDEFINED_OS = {
    "ParrotOS Home Edition": {
        "url": "https://cdimage.parrot.sh/parrot/iso/ParrotSecurity-4.11_amd64.iso",
        "hash": "dummyhash_parrot"
    },
    "NetBSD 9.3": {
        "url": "https://cdn.netbsd.org/pub/NetBSD/NetBSD-9.3/NetBSD-9.3-amd64.iso",
        "hash": "dummyhash_netbsd"
    },
    "Ubuntu Server 22.04": {
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04-live-server-amd64.iso",
        "hash": "dummyhash_ubuntu_server_22"
    },
    "Debian 11 (Netinst)": {
        "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-11.7.0-amd64-netinst.iso",
        "hash": "dummyhash_debian"
    },
    "Ubuntu 22.04 Desktop": {
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04-desktop-amd64.iso",
        "hash": "dummyhash_ubuntu_desktop_22"
    },
    "Ubuntu Jammy Jellyfish": {
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04-desktop-amd64.iso",
        "hash": "dummyhash_ubuntu_jammy"
    },
    "Fedora Workstation 37": {
        "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/37/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-37-1.6.iso",
        "hash": "dummyhash_fedora"
    },
    "OpenSUSE Leap 15.4": {
        "url": "https://download.opensuse.org/distribution/leap/15.4/iso/openSUSE-Leap-15.4-DVD-x86_64.iso",
        "hash": "dummyhash_opensuse"
    },
    "Arch Linux": {
        "url": "https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso",
        "hash": "dummyhash_arch"
    },
    "AlmaLinux 9": {
        "url": "https://repo.almalinux.org/almalinux/9/isos/x86_64/AlmaLinux-9.0-x86_64-dvd1.iso",
        "hash": "dummyhash_almalinux"
    },
    "Pop!_OS 22.04": {
        "url": "https://pop-iso.sfo2.cdn.digitaloceanspaces.com/22.04/Pop_OS_22.04_amd64_intel_60.iso",
        "hash": "dummyhash_popos"
    },
    "Puppy Linux 9.5": {
        "url": "https://distro.ibiblio.org/puppylinux/puppy-9.5/puppy-9.5_2019-08-14.iso",
        "hash": "dummyhash_puppy"
    },
    "Linux Mint 21": {
        "url": "https://mirrors.edge.kernel.org/linuxmint/stable/21/linuxmint-21-cinnamon-64bit.iso",
        "hash": "dummyhash_mint"
    },
    "Tiny Core Linux 12.1": {
        "url": "http://tinycorelinux.net/12.x/x86/release/TinyCorePure64-12.1.iso",
        "hash": "dummyhash_tinycore"
    },
    "Kali Linux 2022.4": {
        "url": "https://cdimage.kali.org/kali-2022.4/kali-linux-2022.4-installer-amd64.iso",
        "hash": "dummyhash_kali"
    },
    # Additional Ubuntu flavors and versions
    "Ubuntu 20.04 LTS Desktop": {
        "url": "https://releases.ubuntu.com/20.04/ubuntu-20.04.5-desktop-amd64.iso",
        "hash": "dummyhash_ubuntu20_desktop"
    },
    "Ubuntu 20.04 LTS Server": {
        "url": "https://releases.ubuntu.com/20.04/ubuntu-20.04-live-server-amd64.iso",
        "hash": "dummyhash_ubuntu20_server"
    },
    "Ubuntu Minimal 20.04": {
        "url": "https://cdimage.ubuntu.com/ubuntu-minimal/releases/20.04/release/ubuntu-minimal-20.04.5-amd64.iso",
        "hash": "dummyhash_ubuntu_minimal"
    }
}

# ----------------------------
# Ventoy download URLs.
VENTOY_URLS = {
    "Linux": "https://github.com/ventoy/Ventoy/releases/download/v1.0.90/ventoy-1.0.90-linux.tar.gz",
    "Windows": "https://github.com/ventoy/Ventoy/releases/download/v1.0.90/ventoy-1.0.90-windows.zip"
}

# ----------------------------
class FlashUtility:
    """
    FlashUtility encapsulates functions for flashing, downloading, extracting, and validating ISO images,
    as well as operations on USB drives (like reformatting and retrieving details).
    
    Attributes:
        os_type (str): The name of the operating system.
        log_callback (function): A callback function for logging messages.
        temp_dir (str): Temporary directory path for downloads/extractions.
    """
    def __init__(self, log_callback=None):
        self.os_type = platform.system()  # Detect operating system
        self.log_callback = log_callback   # Logging callback function
        self.temp_dir = tempfile.mkdtemp(prefix="ventoy_")
        self.log(f"Temporary directory created at {self.temp_dir}", LOG_DEBUG)

    def log(self, message, level=LOG_INFO):
        """Log a message with the given logging level via the log callback if available."""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(message)

    def run_dd_command(self, iso_path, usb_device):
        """
        Run the dd command to flash an ISO image onto a USB device.
        For Linux, this command requires sudo privileges. For Windows, a placeholder is provided.
        """
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
        """
        Download a file from the given URL to the temporary directory.
        Returns:
            str: The full path of the downloaded file or None if failed.
        """
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
        """
        Extract an archive (tar.gz or zip) to the specified directory.
        Returns:
            bool: True if extraction succeeded, False otherwise.
        """
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
        """
        Download and install Ventoy onto the specified USB device.
        For Linux, uses Ventoy2Disk.sh; for Windows, Ventoy2Disk.exe.
        """
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
        """
        Copy the selected ISO file to the Ventoy USB drive.
        Ventoy will automatically detect and list the ISO files present.
        """
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
        """
        Reformat the USB drive with the specified partition scheme.
        Args:
            usb_device (str): The device path (e.g., /dev/sdx).
            scheme (str): Partition scheme ('gpt' or 'mbr').
        WARNING: This operation is destructive and will erase all data on the drive.
        """
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
        """
        Retrieve detailed USB drive information.
        For Linux, uses the lsblk command with additional columns.
        Returns:
            str: Detailed information or an error message.
        """
        try:
            if self.os_type == "Linux":
                result = subprocess.run(["lsblk", "-o", "NAME,FSTYPE,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL"],
                                        capture_output=True, text=True, check=True)
                details = result.stdout.strip()
                return details
            elif self.os_type == "Windows":
                return "USB details not implemented for Windows."
            else:
                return "Unsupported OS."
        except Exception as ex:
            return f"Error retrieving USB details: {ex}"

    def compute_sha256(self, file_path):
        """
        Compute the SHA256 hash of the specified file.
        Returns:
            str: The computed hexadecimal hash string, or None on error.
        """
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
        """
        Clean up temporary files and directories created during operations.
        """
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.log("Cleaned up temporary files.", LOG_DEBUG)
        except Exception as ex:
            self.log(f"Error during cleanup: {ex}", LOG_ERROR)

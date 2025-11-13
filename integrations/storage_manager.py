"""
Storage Manager
Phase 3.2: Disk, Volume, and BitLocker Management
"""

import logging
import os
import platform
import shutil
import subprocess
import psutil
from sebas.typing import Dict, List, Optional, Tuple, Any


class StorageManager:
    """Manages storage operations for Windows systems."""

    def __init__(self):
        if platform.system() != "Windows":
            logging.warning("StorageManager only fully supports Windows")

    # ----------------------- Disk & Partition Info -----------------------
    def list_disk_partitions(self) -> List[Dict[str, Any]]:
        """List all disk partitions."""
        try:
            partitions = []
            for part in psutil.disk_partitions(all=False):
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "opts": part.opts
                })
            return partitions
        except Exception:
            logging.exception("Failed to list disk partitions")
            return []

    def get_disk_info(self) -> List[Dict[str, Any]]:
        """Get basic info for physical disks."""
        try:
            if platform.system() == "Windows":
                cmd = "wmic diskdrive get Name,Model,Size,Status /format:list"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                disks = []
                disk_info = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        if disk_info:
                            disks.append(disk_info)
                            disk_info = {}
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        disk_info[key.strip().lower()] = value.strip()
                if disk_info:
                    disks.append(disk_info)
                return disks
            else:
                return [{"device": d.device, "size": shutil.disk_usage(d.mountpoint).total} for d in psutil.disk_partitions()]
        except Exception:
            logging.exception("Failed to get disk info")
            return []

    def get_volume_info(self) -> List[Dict[str, Any]]:
        """Get logical volume information."""
        try:
            if platform.system() == "Windows":
                cmd = "wmic logicaldisk get DeviceID,VolumeName,FileSystem,FreeSpace,Size /format:list"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
                volumes = []
                current = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        if current:
                            volumes.append(current)
                            current = {}
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        current[key.strip().lower()] = value.strip()
                if current:
                    volumes.append(current)
                return volumes
            else:
                vols = []
                for part in psutil.disk_partitions():
                    usage = shutil.disk_usage(part.mountpoint)
                    vols.append({
                        "deviceid": part.device,
                        "size": usage.total,
                        "freespace": usage.free
                    })
                return vols
        except Exception:
            logging.exception("Failed to get volume info")
            return []

    # ----------------------- Disk Usage -----------------------
    def get_disk_usage(self, path: Optional[str] = None) -> Any:
        """Get disk usage for given path or all drives."""
        try:
            if path:
                usage = shutil.disk_usage(path)
                return {
                    "path": path,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": (usage.used / usage.total) * 100 if usage.total else 0
                }

            drives = []
            for part in psutil.disk_partitions():
                try:
                    usage = shutil.disk_usage(part.mountpoint)
                    drives.append({
                        "path": part.device,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100 if usage.total else 0
                    })
                except Exception:
                    continue
            return drives
        except Exception:
            logging.exception("Failed to get disk usage")
            return []

    # ----------------------- Storage Spaces -----------------------
    def get_storage_spaces_status(self) -> List[Dict[str, Any]]:
        """Get Windows Storage Spaces status."""
        try:
            if platform.system() != "Windows":
                return []
            ps_cmd = "Get-StoragePool | Select-Object FriendlyName, HealthStatus, OperationalStatus, Size | ConvertTo-Json"
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                import json
                data = json.loads(result.stdout)
                return data if isinstance(data, list) else [data]
            return []
        except Exception:
            logging.exception("Failed to get storage spaces status")
            return []

    # ----------------------- BitLocker -----------------------
    def get_bitlocker_status(self, drive_letter: Optional[str] = None) -> List[Dict[str, str]]:
        """Get BitLocker protection status."""
        try:
            if platform.system() != "Windows":
                return []
            ps_cmd = "Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus | ConvertTo-Json"
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                import json
                data = json.loads(result.stdout)
                items = data if isinstance(data, list) else [data]
                if drive_letter:
                    items = [i for i in items if drive_letter.lower() in i.get("MountPoint", "").lower()]
                return [
                    {
                        "volume": i.get("MountPoint"),
                        "status": i.get("VolumeStatus"),
                        "protection_status": i.get("ProtectionStatus")
                    } for i in items
                ]
            return []
        except Exception:
            logging.exception("Failed to get BitLocker status")
            return []

    def enable_bitlocker(self, drive_letter: str) -> Tuple[bool, str]:
        """Enable BitLocker encryption on a drive."""
        try:
            if platform.system() != "Windows":
                return False, "BitLocker not supported on this system"
            ps_cmd = f"Enable-BitLocker -MountPoint {drive_letter} -UsedSpaceOnly -RecoveryPasswordProtector"
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, f"BitLocker enabled on {drive_letter}"
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("Failed to enable BitLocker")
            return False, "Failed to enable BitLocker"

    def disable_bitlocker(self, drive_letter: str) -> Tuple[bool, str]:
        """Disable BitLocker encryption."""
        try:
            if platform.system() != "Windows":
                return False, "BitLocker not supported on this system"
            ps_cmd = f"Disable-BitLocker -MountPoint {drive_letter}"
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, f"BitLocker disabled on {drive_letter}"
            return False, result.stderr.strip() or result.stdout.strip()
        except Exception:
            logging.exception("Failed to disable BitLocker")
            return False, "Failed to disable BitLocker"
# -*- coding: utf-8 -*-
"""
Storage Administration
Phase 3.2: Disk partition, RAID, Storage Spaces, BitLocker management
"""

import logging
import subprocess
import platform
from typing import Optional, Dict, List, Tuple
from enum import Enum


class PartitionType(Enum):
    """Partition types"""
    PRIMARY = "primary"
    EXTENDED = "extended"
    LOGICAL = "logical"


class FileSystemType(Enum):
    """File system types"""
    NTFS = "ntfs"
    FAT32 = "fat32"
    EXFAT = "exfat"


class StorageManager:
    """
    Manages storage operations including partitions, RAID, Storage Spaces, and BitLocker.
    """
    
    def __init__(self):
        """Initialize Storage Manager."""
        if platform.system() != 'Windows':
            raise RuntimeError("StorageManager only works on Windows")
    
    def list_disk_partitions(self) -> List[Dict[str, str]]:
        """
        List all disk partitions.
        
        Returns:
            List of partition information dicts
        """
        try:
            result = subprocess.run(
                ["wmic", "partition", "get", "DeviceID,Bootable,Index,Size,Type", "/format:list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            partitions = []
            current_partition = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_partition:
                        partitions.append(current_partition)
                        current_partition = {}
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    current_partition[key.lower()] = value
            
            if current_partition:
                partitions.append(current_partition)
            
            return partitions
            
        except Exception:
            logging.exception("Failed to list disk partitions")
            return []
    
    def get_disk_info(self, disk_number: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get disk information.
        
        Args:
            disk_number: Optional disk number to filter
            
        Returns:
            List of disk information dicts
        """
        try:
            cmd = ["wmic", "diskdrive", "get", "DeviceID,Model,Size,InterfaceType,MediaType", "/format:list"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            disks = []
            current_disk = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_disk:
                        disks.append(current_disk)
                        current_disk = {}
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    current_disk[key.lower()] = value
            
            if current_disk:
                disks.append(current_disk)
            
            return disks
            
        except Exception:
            logging.exception("Failed to get disk info")
            return []
    
    def get_volume_info(self) -> List[Dict[str, str]]:
        """
        Get volume information.
        
        Returns:
            List of volume information dicts
        """
        try:
            result = subprocess.run(
                ["wmic", "logicaldisk", "get", "DeviceID,DriveType,FileSystem,FreeSpace,Size,VolumeName", "/format:list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            volumes = []
            current_volume = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_volume:
                        volumes.append(current_volume)
                        current_volume = {}
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    current_volume[key.lower()] = value
            
            if current_volume:
                volumes.append(current_volume)
            
            return volumes
            
        except Exception:
            logging.exception("Failed to get volume info")
            return []
    
    def get_storage_spaces_status(self) -> List[Dict[str, str]]:
        """
        Get Storage Spaces status.
        
        Returns:
            List of Storage Spaces information dicts
        """
        try:
            # Use PowerShell to get Storage Spaces info
            ps_cmd = "Get-StoragePool | Select-Object FriendlyName, HealthStatus, OperationalStatus, Size | ConvertTo-Json"
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            try:
                import json
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            except:
                pass
            
            return []
            
        except Exception:
            logging.exception("Failed to get Storage Spaces status")
            return []
    
    def get_bitlocker_status(self, drive_letter: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get BitLocker encryption status.
        
        Args:
            drive_letter: Optional drive letter (e.g., 'C:')
            
        Returns:
            List of BitLocker status information dicts
        """
        try:
            cmd = ["manage-bde", "-status"]
            if drive_letter:
                cmd.append(drive_letter)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return []
            
            drives = []
            current_drive = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    current_drive[key.lower().replace(' ', '_')] = value
                
                if 'Volume' in line and ':' in line:
                    if current_drive:
                        drives.append(current_drive)
                    current_drive = {'volume': line.split(':', 1)[1].strip()}
            
            if current_drive:
                drives.append(current_drive)
            
            return drives
            
        except Exception:
            logging.exception("Failed to get BitLocker status")
            return []
    
    def enable_bitlocker(self, drive_letter: str, recovery_password: Optional[str] = None,
                        tpm_only: bool = False) -> Tuple[bool, str]:
        """
        Enable BitLocker encryption on a drive.
        
        Args:
            drive_letter: Drive letter (e.g., 'C:')
            recovery_password: Optional recovery password
            tpm_only: Use TPM only (no password)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["manage-bde", "-on", drive_letter]
            
            if tpm_only:
                cmd.extend(["-UsedSpaceOnly"])
            else:
                cmd.extend(["-UsedSpaceOnly", "-Password"])
                if recovery_password:
                    # Note: This is simplified - in production, password should be handled securely
                    logging.warning("Password should be handled securely")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True, f"BitLocker encryption started on {drive_letter}"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to enable BitLocker on {drive_letter}")
            return False, "Failed to enable BitLocker"
    
    def disable_bitlocker(self, drive_letter: str) -> Tuple[bool, str]:
        """
        Disable BitLocker encryption on a drive.
        
        Args:
            drive_letter: Drive letter
            
        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["manage-bde", "-off", drive_letter],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, f"BitLocker decryption started on {drive_letter}"
            else:
                error = result.stderr.strip() or result.stdout.strip()
                return False, error
                
        except Exception:
            logging.exception(f"Failed to disable BitLocker on {drive_letter}")
            return False, "Failed to disable BitLocker"
    
    def get_disk_usage(self, path: Optional[str] = None) -> Dict[str, any]:
        """
        Get disk usage information.
        
        Args:
            path: Optional path to check (defaults to all drives)
            
        Returns:
            Dict with disk usage information
        """
        try:
            import psutil
            
            if path:
                usage = psutil.disk_usage(path)
                return {
                    'path': path,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                }
            else:
                # Get all disk partitions
                partitions = psutil.disk_partitions()
                result = {}
                
                for partition in partitions:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        result[partition.device] = {
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        }
                    except PermissionError:
                        continue
                
                return result
                
        except Exception:
            logging.exception("Failed to get disk usage")
            return {}

